"""
SigmaCloud AI - Datasets API Router
Handles dataset upload, listing, and example datasets.
"""
import os
import logging
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.ml.datasets import EXAMPLE_DATASETS
from app.ml.eda import generate_dataset_analysis, load_dataset_dataframe
from app.models.db_models import Dataset, TrainingJob, TrainedModel, User
from app.schemas.schemas import DatasetAnalysisResponse, DatasetResponse
from app.services.dataset_builder import (
    analyze_dataframe,
    build_preview,
    normalize_column_names,
    safe_storage_filename,
)


router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = (".csv", ".xlsx", ".xls")


def get_owned_dataset_or_404(dataset_id: int, user_id: int, db: Session) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == user_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


def require_dataset_file(dataset: Dataset) -> str:
    """Fail with an actionable message when storage was wiped."""
    if dataset.file_available:
        return dataset.file_path

    raise HTTPException(
        status_code=409,
        detail=(
            "This dataset's file is no longer on disk. Free hosting tiers clear "
            "storage when the service restarts - please re-upload it."
        ),
    )


def build_explainability_payload(dataset_id: int, user_id: int, db: Session):
    jobs = (
        db.query(TrainingJob)
        .filter(
            TrainingJob.dataset_id == dataset_id,
            TrainingJob.user_id == user_id,
            TrainingJob.status == "completed",
        )
        .order_by(TrainingJob.completed_at.desc(), TrainingJob.created_at.desc())
        .all()
    )
    if not jobs:
        return None

    latest_job = jobs[0]
    models = (
        db.query(TrainedModel)
        .filter(TrainedModel.job_id == latest_job.job_id, TrainedModel.user_id == user_id)
        .all()
    )
    if not models:
        return None

    if latest_job.task_type == "classification":
        best_model = max(models, key=lambda model: (model.accuracy or 0.0, model.f1_score or 0.0, model.roc_auc or 0.0))
        metric_label = "Accuracy"
        metric_value = best_model.accuracy
    else:
        best_model = max(models, key=lambda model: (model.r2_score if model.r2_score is not None else -999.0))
        metric_label = "R2"
        metric_value = best_model.r2_score

    feature_importance_map = best_model.feature_importance or {}
    feature_importance = [
        {"feature": feature, "importance": round(float(value), 4)}
        for feature, value in sorted(feature_importance_map.items(), key=lambda item: item[1], reverse=True)[:8]
    ]
    if not feature_importance:
        return None

    total_importance = sum(item["importance"] for item in feature_importance) or 1.0
    top_features = ", ".join(item["feature"] for item in feature_importance[:3])
    insights = [
        f"The strongest trained explanation comes from {best_model.model_name}, selected from job {latest_job.job_id[:8]}.",
        f"The model relies most on {top_features}.",
        f"The top {min(5, len(feature_importance))} features explain "
        f"{(sum(item['importance'] for item in feature_importance[:5]) / total_importance) * 100:.1f}% of displayed importance.",
    ]

    return {
        "model_name": best_model.model_name,
        "job_id": latest_job.job_id,
        "task_type": latest_job.task_type or best_model.task_type or "unknown",
        "metric_label": metric_label,
        "metric_value": round(float(metric_value), 4) if metric_value is not None else None,
        "feature_importance": feature_importance,
        "insights": insights,
    }


@router.post("/upload-dataset", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    target_column: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    original_name = os.path.basename(file.filename or "")
    if not original_name.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported.")

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_BYTES
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {max_bytes // (1024 * 1024)}MB on this deployment.",
        )
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    # Filename comes straight from the client and is never trusted as a path.
    stored_name = safe_storage_filename(original_name, current_user.id)
    file_path = os.path.join(settings.DATASET_STORAGE_PATH, stored_name)
    os.makedirs(settings.DATASET_STORAGE_PATH, exist_ok=True)

    with open(file_path, "wb") as saved_file:
        saved_file.write(content)

    try:
        if original_name.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as exc:
        logger.exception("Failed to parse uploaded dataset '%s': %s", original_name, exc)
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}") from exc

    if df.empty or len(df.columns) == 0:
        os.remove(file_path)
        raise HTTPException(status_code=422, detail="The file parsed successfully but contains no rows.")

    df = normalize_column_names(df)

    dataset = Dataset(
        user_id=current_user.id,
        name=name or original_name,
        filename=original_name,
        file_path=file_path,
        file_size=len(content),
        num_rows=len(df),
        num_columns=len(df.columns),
        columns_info=analyze_dataframe(df),
        target_column=target_column,
        is_example=False,
        preview_data=build_preview(df),
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    logger.info("Dataset uploaded for user=%s name=%s rows=%s", current_user.id, dataset.name, len(df))
    return dataset


@router.post("/load-example/{dataset_key}", response_model=DatasetResponse)
async def load_example_dataset(
    dataset_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if dataset_key not in EXAMPLE_DATASETS:
        raise HTTPException(status_code=404, detail=f"Example dataset '{dataset_key}' not found.")

    meta = EXAMPLE_DATASETS[dataset_key]
    existing = (
        db.query(Dataset)
        .filter(
            Dataset.user_id == current_user.id,
            Dataset.is_example.is_(True),
            Dataset.name == meta["name"],
        )
        .first()
    )
    # Reuse the row only if its file survived; otherwise rewrite it in place so
    # example datasets always work after a restart wipes storage.
    if existing and existing.file_available:
        return existing

    df = meta["loader"]()
    os.makedirs(settings.DATASET_STORAGE_PATH, exist_ok=True)
    file_path = os.path.join(
        settings.DATASET_STORAGE_PATH, f"user_{current_user.id}_{meta['filename']}"
    )
    df.to_csv(file_path, index=False)

    if existing:
        existing.file_path = file_path
        existing.file_size = os.path.getsize(file_path)
        existing.num_rows = len(df)
        existing.num_columns = len(df.columns)
        existing.columns_info = analyze_dataframe(df)
        existing.preview_data = build_preview(df)
        db.commit()
        db.refresh(existing)
        logger.info("Example dataset restored for user=%s name=%s", current_user.id, meta["name"])
        return existing

    dataset = Dataset(
        user_id=current_user.id,
        name=meta["name"],
        filename=meta["filename"],
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        num_rows=len(df),
        num_columns=len(df.columns),
        columns_info=analyze_dataframe(df),
        target_column=meta["target"],
        task_type=meta["task_type"],
        is_example=True,
        preview_data=build_preview(df),
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    logger.info("Example dataset loaded for user=%s name=%s", current_user.id, meta["name"])
    return dataset


@router.get("/datasets", response_model=List[DatasetResponse])
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Dataset)
        .filter(Dataset.user_id == current_user.id)
        .order_by(Dataset.created_at.desc())
        .all()
    )


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_owned_dataset_or_404(dataset_id, current_user.id, db)


@router.get("/datasets/{dataset_id}/analysis", response_model=DatasetAnalysisResponse)
def get_dataset_analysis(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = get_owned_dataset_or_404(dataset_id, current_user.id, db)
    file_path = require_dataset_file(dataset)

    try:
        df = load_dataset_dataframe(file_path)
        analysis = generate_dataset_analysis(df, dataset.target_column)
        analysis["explainability"] = build_explainability_payload(dataset.id, current_user.id, db)
        return analysis
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to generate dataset analysis for dataset_id=%s: %s", dataset_id, exc)
        raise HTTPException(status_code=500, detail="Could not generate dataset analysis") from exc


@router.get("/example-datasets")
def list_example_datasets():
    return [
        {
            "key": key,
            "name": meta["name"],
            "description": meta["description"],
            "target": meta["target"],
            "task_type": meta["task_type"],
        }
        for key, meta in EXAMPLE_DATASETS.items()
    ]


@router.delete("/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = get_owned_dataset_or_404(dataset_id, current_user.id, db)

    # Collect model artifacts before the ORM cascade removes their rows -
    # otherwise the files stay on disk forever with nothing referencing them.
    job_ids = [
        job_id
        for (job_id,) in db.query(TrainingJob.job_id)
        .filter(TrainingJob.dataset_id == dataset.id)
        .all()
    ]
    model_paths = []
    if job_ids:
        model_paths = [
            path
            for (path,) in db.query(TrainedModel.file_path)
            .filter(TrainedModel.job_id.in_(job_ids))
            .all()
            if path
        ]

    db.delete(dataset)
    db.commit()

    removed = 0
    for path in [dataset.file_path, *model_paths]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                removed += 1
            except OSError as exc:
                logger.warning("Could not remove file %s: %s", path, exc)

    logger.info(
        "Dataset %s deleted | jobs=%s artifacts_removed=%s", dataset_id, len(job_ids), removed
    )
    return {
        "message": "Dataset deleted along with its training jobs and models.",
        "jobs_removed": len(job_ids),
        "artifacts_removed": removed,
    }
