"""
SigmaCloud AI - Datasets API Router
Handles dataset upload, listing, and example datasets.
"""
import os
import uuid
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


router = APIRouter()
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 100 * 1024 * 1024


def get_owned_dataset_or_404(dataset_id: int, user_id: int, db: Session) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == user_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


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


def analyze_dataframe(df: pd.DataFrame) -> List[dict]:
    columns_info = []
    for col in df.columns:
        col_data = df[col]
        info = {
            "name": col,
            "dtype": str(col_data.dtype),
            "null_count": int(col_data.isnull().sum()),
            "unique_count": int(col_data.nunique()),
            "sample_values": col_data.dropna().head(5).tolist(),
        }

        if col_data.dtype in ["int64", "float64"]:
            info["stats"] = {
                "min": float(col_data.min()) if not col_data.empty else None,
                "max": float(col_data.max()) if not col_data.empty else None,
                "mean": float(col_data.mean()) if not col_data.empty else None,
                "std": float(col_data.std()) if not col_data.empty else None,
                "median": float(col_data.median()) if not col_data.empty else None,
            }

        columns_info.append(info)
    return columns_info


@router.post("/upload-dataset", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    target_column: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 100MB.")

    file_id = str(uuid.uuid4())[:8]
    safe_name = f"user_{current_user.id}_{file_id}_{file.filename}"
    file_path = os.path.join(settings.DATASET_STORAGE_PATH, safe_name)

    with open(file_path, "wb") as saved_file:
        saved_file.write(content)

    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as exc:
        logger.exception("Failed to parse uploaded dataset '%s': %s", file.filename, exc)
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}") from exc

    dataset = Dataset(
        user_id=current_user.id,
        name=name or file.filename,
        filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        num_rows=len(df),
        num_columns=len(df.columns),
        columns_info=analyze_dataframe(df),
        target_column=target_column,
        is_example=False,
        preview_data=df.head(10).fillna("").to_dict(orient="records"),
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
            Dataset.is_example == True,
            Dataset.name == meta["name"],
        )
        .first()
    )
    if existing:
        return existing

    df = meta["loader"]()
    file_path = os.path.join(settings.DATASET_STORAGE_PATH, f"user_{current_user.id}_{meta['filename']}")
    df.to_csv(file_path, index=False)

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
        preview_data=df.head(10).fillna("").to_dict(orient="records"),
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

    try:
        df = load_dataset_dataframe(dataset.file_path)
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

    if os.path.exists(dataset.file_path):
        os.remove(dataset.file_path)

    db.delete(dataset)
    db.commit()
    return {"message": "Dataset deleted successfully"}
