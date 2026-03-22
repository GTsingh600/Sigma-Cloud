"""
SigmaCloud AI - Training API Router
Launches AutoML training jobs (sync for simplicity, async with Celery in prod).
"""
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
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
_job_progress: dict = {}


def run_training(job_id: str, dataset_path: str, config: dict, db_url: str):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        job = db.query(TrainingJob).filter(TrainingJob.job_id == job_id).first()
        if not job:
            return
        job.status = "running"
        db.commit()

        def update_progress(progress: int, message: str = ""):
            _job_progress[job_id] = {"progress": progress, "message": message}
            tracked_job = db.query(TrainingJob).filter(TrainingJob.job_id == job_id).first()
            if tracked_job:
                tracked_job.progress = progress
                db.commit()

        df = load_dataset_dataframe(dataset_path)

        pipeline = AutoMLPipeline(job_id=job_id, progress_callback=update_progress)
        results = pipeline.train_all_models(
            df=df,
            target_column=config["target_column"],
            task_type=config.get("task_type"),
            test_size=config.get("test_size", 0.2),
            cv_folds=config.get("cv_folds", 5),
            models_to_train=config.get("models_to_train"),
            mode=config.get("mode", "simple"),
            tuning_params=config.get("tuning_params"),
        )

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

        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.progress = 100
        db.commit()
        logger.info("Training job %s completed", job_id)
    except Exception as exc:
        logger.exception("Training job %s failed: %s", job_id, exc)
        job = db.query(TrainingJob).filter(TrainingJob.job_id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            db.commit()
    finally:
        db.close()


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

    df = load_dataset_dataframe(dataset.file_path)
    pipeline = AutoMLPipeline(job_id="preview")
    return pipeline.build_training_plan(df, config.target_column, config.task_type)


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

    job_id = str(uuid.uuid4())
    job = TrainingJob(
        user_id=current_user.id,
        job_id=job_id,
        dataset_id=config.dataset_id,
        target_column=config.target_column,
        task_type=config.task_type,
        status="pending",
        progress=0,
        config={
            "target_column": config.target_column,
            "task_type": config.task_type,
            "mode": config.mode,
            "test_size": config.test_size,
            "cv_folds": config.cv_folds,
            "models_to_train": config.models_to_train,
            "tuning_params": config.tuning_params,
        },
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from app.core.config import settings

    background_tasks.add_task(
        run_training,
        job_id=job_id,
        dataset_path=dataset.file_path,
        config={
            "target_column": config.target_column,
            "task_type": config.task_type,
            "mode": config.mode,
            "test_size": config.test_size,
            "cv_folds": config.cv_folds,
            "models_to_train": config.models_to_train,
            "tuning_params": config.tuning_params,
        },
        db_url=settings.DATABASE_URL,
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


@router.get("/training-jobs")
def list_training_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(TrainingJob)
        .filter(TrainingJob.user_id == current_user.id)
        .order_by(TrainingJob.created_at.desc())
        .all()
    )
