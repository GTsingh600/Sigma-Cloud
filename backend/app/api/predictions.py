"""
SigmaCloud AI - Predictions API Router
Run inference on deployed models.
"""
import logging

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.db_models import TrainedModel, User
from app.schemas.schemas import (
    ModelFeaturesResponse,
    PredictionRequest,
    PredictionResponse,
)
from app.services import model_registry


router = APIRouter()
logger = logging.getLogger(__name__)

MISSING_ARTIFACT_DETAIL = (
    "This model's file is no longer on disk. Free hosting tiers clear storage "
    "when the service restarts - retrain to recreate it."
)


def get_owned_model(model_id: int, user_id: int, db: Session) -> TrainedModel:
    model = (
        db.query(TrainedModel)
        .filter(TrainedModel.id == model_id, TrainedModel.user_id == user_id)
        .first()
    )
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


def load_artifact(model: TrainedModel) -> dict:
    try:
        return model_registry.load(model.id, model.file_path)
    except model_registry.ModelArtifactMissing as exc:
        raise HTTPException(status_code=409, detail=MISSING_ARTIFACT_DETAIL) from exc


@router.get("/models/{model_id}/features", response_model=ModelFeaturesResponse)
def get_model_features(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Feature names the prediction form should render."""
    model_record = get_owned_model(model_id, current_user.id, db)
    artifact = load_artifact(model_record)

    return ModelFeaturesResponse(
        model_id=model_record.id,
        model_name=model_record.model_name,
        task_type=artifact.get("task_type") or model_record.task_type,
        feature_names=list(artifact.get("feature_names") or []),
    )


@router.post("/predict", response_model=PredictionResponse)
def predict(
    request: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model_record = get_owned_model(request.model_id, current_user.id, db)
    model_data = load_artifact(model_record)

    pipeline = model_data["pipeline"]
    feature_names = list(model_data.get("feature_names") or [])
    label_encoder = model_data.get("label_encoder")
    task_type = model_data.get("task_type")

    # Silently imputing absent features produces a confident prediction from a
    # mostly-empty row, which is worse than refusing.
    missing = [name for name in feature_names if request.features.get(name) in (None, "")]
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Some required feature values are missing.",
                "missing_features": missing,
            },
        )

    unexpected = [name for name in request.features if name not in feature_names]
    if unexpected:
        logger.info("Ignoring unknown feature(s) for model %s: %s", request.model_id, unexpected)

    df_input = pd.DataFrame({name: [request.features[name]] for name in feature_names})

    try:
        prediction_raw = pipeline.predict(df_input)
        prediction = prediction_raw[0]
        probability = None
        confidence = None

        if task_type == "classification":
            if label_encoder is not None:
                prediction = label_encoder.inverse_transform([int(prediction)])[0]

            if hasattr(pipeline, "predict_proba"):
                proba = pipeline.predict_proba(df_input)[0]
                classes = (
                    label_encoder.classes_
                    if label_encoder is not None
                    else [str(index) for index in range(len(proba))]
                )
                probability = {str(cls): float(value) for cls, value in zip(classes, proba)}
                confidence = float(max(proba))

            # numpy scalars are not JSON-serializable.
            if isinstance(prediction, (np.integer, np.floating, np.bool_)):
                prediction = prediction.item()
            else:
                prediction = str(prediction)
        else:
            prediction = float(prediction)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Prediction error for model %s: %s", request.model_id, exc)
        raise HTTPException(
            status_code=400,
            detail=(
                "Prediction failed. Check that each value matches the type the "
                f"model was trained on. ({exc})"
            ),
        ) from exc

    return PredictionResponse(
        model_id=request.model_id,
        model_name=model_record.model_name,
        prediction=prediction,
        probability=probability,
        confidence=confidence,
    )


@router.get("/deployed-models")
def list_deployed_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    models = (
        db.query(TrainedModel)
        .filter(TrainedModel.user_id == current_user.id, TrainedModel.is_deployed.is_(True))
        .order_by(TrainedModel.created_at.desc())
        .all()
    )
    return [
        {
            "id": model.id,
            "model_name": model.model_name,
            "model_type": model.model_type,
            "task_type": model.task_type,
            "job_id": model.job_id,
            "file_available": model.file_available,
        }
        for model in models
    ]
