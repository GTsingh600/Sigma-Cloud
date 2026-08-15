"""
SigmaCloud AI - Training API Router
Launches AutoML training jobs (in-process background tasks; Celery in prod).
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.datasets import require_dataset_file
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import session_scope
from app.core.database import get_db
from app.ml.eda import load_dataset_dataframe
from app.ml.pipeline import AutoMLPipeline
from app.models.db_models import Dataset, TrainingJob, TrainedModel, User
from app.schemas.schemas import (
    TrainingConfig,
    TrainingJobResponse,
    TrainingRecommendationRequest,
    TrainingRecommendationResponse,
)


router = APIRouter()
logger = logging.getLogger(__name__)


def run_training(job_id: str, dataset_path: str, config: dict):
    """Execute a training job outside the request cycle.

    Uses the shared session factory rather than constructing an engine here -
    building one per job re-derives dialect connect args (which silently broke
    on PostgreSQL) and leaks a pool for every run.
    """
    try:
        with session_scope() as db:
            job = db.query(TrainingJob).filter(TrainingJob.job_id == job_id).first()
            if not job:
                logger.warning("Training job %s vanished before it started", job_id)
                return
            job.status = "running"
            job.progress = 0

        def update_progress(progress: int, message: str = ""):
            try:
                with session_scope() as progress_db:
                    tracked = (
                        progress_db.query(TrainingJob)
                        .filter(TrainingJob.job_id == job_id)
                        .first()
                    )
                    if tracked:
                        tracked.progress = progress
                        tracked.progress_message = message[:255] if message else None
            except Exception as exc:
                # A dropped progress write must never abort the run itself.
                logger.warning("Progress update failed for %s: %s", job_id, exc)

        df = load_dataset_dataframe(dataset_path)

        pipeline = AutoMLPipeline(job_id=job_id, progress_callback=update_progress)
        results = pipeline.train_all_models(
            df=df,
            target_column=config["target_column"],
            task_type=config.get("task_type"),
            test_size=config.get("test_size", settings.TEST_SIZE),
            cv_folds=config.get("cv_folds", settings.CV_FOLDS),
            models_to_train=config.get("models_to_train"),
            mode=config.get("mode", "simple"),
            tuning_params=config.get("tuning_params"),
        )

        with session_scope() as db:
            job = db.query(TrainingJob).filter(TrainingJob.job_id == job_id).first()
            if not job:
                return

            job.task_type = results["task_type"]
            job.config = {
                **(job.config or {}),
                "mode": results.get("mode", config.get("mode", "simple")),
                "selected_models": results.get("selected_models", config.get("models_to_train")),
                "available_models": results.get("available_models", []),
                "recommended_models": results.get("recommended_models", []),
                "recommendation_reasons": results.get("recommendation_reasons", []),
                "cleaning_steps": results.get("cleaning_steps", []),
            }

            trained_count = 0
            for model_result in results["models"]:
                if "error" in model_result:
                    continue

                db.add(
                    TrainedModel(
                        user_id=job.user_id,
                        job_id=job_id,
                        model_name=model_result["model_name"],
                        model_type=model_result["model_type"],
                        task_type=results["task_type"],
                        file_path=model_result.get("file_path"),
                        accuracy=model_result.get("accuracy"),
                        f1_score=model_result.get("f1_score"),
                        roc_auc=model_result.get("roc_auc"),
                        rmse=model_result.get("rmse"),
                        mae=model_result.get("mae"),
                        r2_score=model_result.get("r2_score"),
                        metrics=model_result.get("metrics"),
                        feature_importance=model_result.get("feature_importance"),
                        confusion_matrix=model_result.get("confusion_matrix"),
                        roc_curve_data=model_result.get("roc_curve_data"),
                        cv_scores=model_result.get("cv_scores"),
                        training_time=model_result.get("training_time"),
                    )
                )
                trained_count += 1

            if trained_count == 0:
                job.status = "failed"
                job.error_message = (
                    "Every selected model failed to train. Check that the target "
                    "column suits the detected task type."
                )
            else:
                job.status = "completed"
                job.progress = 100
                job.progress_message = "Training complete"

            job.completed_at = datetime.now(timezone.utc)

        logger.info("Training job %s completed", job_id)
    except Exception as exc:
        logger.exception("Training job %s failed: %s", job_id, exc)
        try:
            with session_scope() as db:
                job = db.query(TrainingJob).filter(TrainingJob.job_id == job_id).first()
                if job:
                    job.status = "failed"
                    job.error_message = str(exc)[:1000]
                    job.completed_at = datetime.now(timezone.utc)
        except Exception:
            logger.exception("Could not record failure for job %s", job_id)


def reconcile_stale_jobs() -> int:
    """Fail jobs orphaned by a restart.

    Free tiers spin the service down mid-run, which leaves rows stuck at
    'running' forever with no process behind them.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.STALE_JOB_TIMEOUT_MINUTES)

    with session_scope() as db:
        stale = (
            db.query(TrainingJob)
            .filter(
                TrainingJob.status.in_(["pending", "running"]),
                TrainingJob.created_at < cutoff,
            )
            .all()
        )
        for job in stale:
            job.status = "failed"
            job.error_message = (
                "Training stopped because the server restarted. Free hosting tiers "
                "sleep when idle - start the run again and keep the tab open."
            )
            job.completed_at = datetime.now(timezone.utc)

        count = len(stale)

    if count:
        logger.info("Marked %s stale training job(s) as failed", count)
    return count


def get_owned_dataset(config_dataset_id: int, user_id: int, db: Session) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == config_dataset_id, Dataset.user_id == user_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.post("/training-recommendation", response_model=TrainingRecommendationResponse)
async def get_training_recommendation(
    config: TrainingRecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = get_owned_dataset(config.dataset_id, current_user.id, db)
    df_cols = [column["name"] for column in (dataset.columns_info or [])]
    if config.target_column not in df_cols:
        raise HTTPException(status_code=400, detail=f"Target column '{config.target_column}' not found in dataset")

    file_path = require_dataset_file(dataset)
    df = load_dataset_dataframe(file_path)
    pipeline = AutoMLPipeline(job_id="preview")

    try:
        return pipeline.build_training_plan(df, config.target_column, config.task_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/train-model", response_model=TrainingJobResponse)
async def train_model(
    config: TrainingConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = get_owned_dataset(config.dataset_id, current_user.id, db)
    df_cols = [column["name"] for column in (dataset.columns_info or [])]
    if config.target_column not in df_cols:
        raise HTTPException(status_code=400, detail=f"Target column '{config.target_column}' not found in dataset")

    dataset_path = require_dataset_file(dataset)

    active_jobs = (
        db.query(TrainingJob)
        .filter(
            TrainingJob.user_id == current_user.id,
            TrainingJob.status.in_(["pending", "running"]),
        )
        .count()
    )
    if active_jobs:
        raise HTTPException(
            status_code=409,
            detail="You already have a training run in progress. Wait for it to finish.",
        )

    job_id = str(uuid.uuid4())
    training_config = {
        "target_column": config.target_column,
        "task_type": config.task_type,
        "mode": config.mode,
        "test_size": config.test_size,
        "cv_folds": config.cv_folds,
        "models_to_train": config.models_to_train,
        "tuning_params": config.tuning_params,
    }

    job = TrainingJob(
        user_id=current_user.id,
        job_id=job_id,
        dataset_id=config.dataset_id,
        target_column=config.target_column,
        task_type=config.task_type,
        status="pending",
        progress=0,
        progress_message="Queued",
        config=training_config,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        run_training,
        job_id=job_id,
        dataset_path=dataset_path,
        config=training_config,
    )

    logger.info("Training job %s queued for user=%s", job_id, current_user.id)
    return job


@router.get("/training-status/{job_id}", response_model=TrainingJobResponse)
def get_training_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(TrainingJob).filter(TrainingJob.job_id == job_id, TrainingJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    return job


@router.get("/training-jobs", response_model=list[TrainingJobResponse])
def list_training_jobs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(TrainingJob)
        .filter(TrainingJob.user_id == current_user.id)
        .order_by(TrainingJob.created_at.desc())
        .limit(min(max(limit, 1), 200))
        .all()
    )
