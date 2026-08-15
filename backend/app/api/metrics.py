"""
SigmaCloud AI - Metrics API Router
Returns comparison metrics and visualization data.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.db_models import Dataset, TrainedModel, TrainingJob, User


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/metrics/{job_id}")
def get_metrics(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(TrainingJob).filter(TrainingJob.job_id == job_id, TrainingJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")

    models = db.query(TrainedModel).filter(TrainedModel.job_id == job_id, TrainedModel.user_id == current_user.id).all()
    if not models:
        return {"job_id": job_id, "status": job.status, "models": []}

    task_type = job.task_type or (models[0].task_type if models else "unknown")
    model_data = []
    for model in models:
        data = {
            "id": model.id,
            "model_name": model.model_name,
            "model_type": model.model_type,
            "task_type": model.task_type,
            "training_time": model.training_time,
            "is_deployed": model.is_deployed,
            "cv_scores": model.cv_scores,
            "metrics": model.metrics,
            "cv_mean": model.metrics.get("cv_mean") if model.metrics else None,
            "cv_std": model.metrics.get("cv_std") if model.metrics else None,
            "feature_importance": model.feature_importance,
        }
        if task_type == "classification":
            data.update(
                {
                    "accuracy": model.accuracy,
                    "f1_score": model.f1_score,
                    "roc_auc": model.roc_auc,
                    "confusion_matrix": model.confusion_matrix,
                    "roc_curve_data": model.roc_curve_data,
                }
            )
        else:
            data.update(
                {
                    "rmse": model.rmse,
                    "mae": model.mae,
                    "r2_score": model.r2_score,
                }
            )
        model_data.append(data)

    if task_type == "classification":
        model_data.sort(key=lambda item: item.get("accuracy") or 0, reverse=True)
    else:
        model_data.sort(key=lambda item: item.get("r2_score") or -999, reverse=True)
    best_model = model_data[0] if model_data else None

    return {
        "job_id": job_id,
        "task_type": task_type,
        "status": job.status,
        "training_mode": (job.config or {}).get("mode", "simple"),
        "selected_models": (job.config or {}).get("selected_models", []),
        "available_models": (job.config or {}).get("available_models", []),
        "recommended_models": (job.config or {}).get("recommended_models", []),
        "recommendation_reasons": (job.config or {}).get("recommendation_reasons", []),
        "cleaning_steps": (job.config or {}).get("cleaning_steps", []),
        "models": model_data,
        "best_model": best_model,
        "performance_scatter": [
            {
                "model_name": item["model_name"],
                "training_time": item.get("training_time"),
                "primary_metric": item.get("accuracy") if task_type == "classification" else item.get("r2_score"),
                "stability": item.get("cv_std"),
            }
            for item in model_data
        ],
        "leaderboard": [
            {
                "rank": index + 1,
                "model_name": item["model_name"],
                # Selected by task type, not `a or b`: an accuracy of exactly
                # 0.0 is falsy and used to fall through to the r2_score key.
                "primary_metric": (
                    item.get("accuracy") if task_type == "classification" else item.get("r2_score")
                ),
                "metric_name": "accuracy" if task_type == "classification" else "r2_score",
                "training_time": item.get("training_time"),
            }
            for index, item in enumerate(model_data)
        ],
    }


@router.get("/dashboard/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Counts for the dashboard tiles.

    Aggregated with grouped COUNT queries rather than one round trip per tile -
    the previous version issued five separate COUNT(*) statements, which is
    noticeably slow against a remote managed Postgres.
    """
    user_id = current_user.id

    job_counts = dict(
        db.query(TrainingJob.status, func.count(TrainingJob.id))
        .filter(TrainingJob.user_id == user_id)
        .group_by(TrainingJob.status)
        .all()
    )

    model_totals = (
        db.query(
            func.count(TrainedModel.id),
            func.sum(case((TrainedModel.is_deployed.is_(True), 1), else_=0)),
        )
        .filter(TrainedModel.user_id == user_id)
        .one()
    )

    total_datasets = (
        db.query(func.count(Dataset.id)).filter(Dataset.user_id == user_id).scalar() or 0
    )

    return {
        "total_datasets": int(total_datasets),
        "total_models": int(model_totals[0] or 0),
        "deployed_models": int(model_totals[1] or 0),
        "completed_jobs": int(job_counts.get("completed", 0)),
        "failed_jobs": int(job_counts.get("failed", 0)),
        "running_jobs": int(job_counts.get("running", 0) + job_counts.get("pending", 0)),
    }
