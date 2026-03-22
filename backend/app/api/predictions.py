"""
SigmaCloud AI - Predictions API Router
Run inference on deployed models.
"""
import logging
from typing import Any, Dict

import joblib
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.db_models import TrainedModel, User
from app.schemas.schemas import PredictionRequest, PredictionResponse


router = APIRouter()
logger = logging.getLogger(__name__)
_model_cache: Dict[int, Any] = {}


def load_model(model_id: int, file_path: str) -> dict:
    if model_id not in _model_cache:
        _model_cache[model_id] = joblib.load(file_path)
        logger.info("Model %s loaded into cache", model_id)
    return _model_cache[model_id]


@router.post("/predict", response_model=PredictionResponse)
def predict(
    request: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model_record = (
        db.query(TrainedModel)
        .filter(TrainedModel.id == request.model_id, TrainedModel.user_id == current_user.id)
        .first()
    )
    if not model_record:
        raise HTTPException(status_code=404, detail="Model not found")
    if not model_record.file_path:
        raise HTTPException(status_code=400, detail="Model file not available")

    try:
        model_data = load_model(request.model_id, model_record.file_path)
        pipeline = model_data["pipeline"]
        feature_names = model_data["feature_names"]
        label_encoder = model_data.get("label_encoder")
        task_type = model_data.get("task_type")

        input_data = {}
        for feature in feature_names:
            input_data[feature] = [request.features[feature]] if feature in request.features else [None]
        df_input = pd.DataFrame(input_data)

        prediction_raw = pipeline.predict(df_input)
        prediction = prediction_raw[0]
        probability = None
        confidence = None

        if task_type == "classification":
            if label_encoder:
                prediction = label_encoder.inverse_transform([int(prediction)])[0]

            if hasattr(pipeline, "predict_proba"):
                proba = pipeline.predict_proba(df_input)[0]
                classes = label_encoder.classes_ if label_encoder else [str(i) for i in range(len(proba))]
                probability = {str(cls): float(p) for cls, p in zip(classes, proba)}
                confidence = float(max(proba))
        else:
            prediction = float(prediction)

        return PredictionResponse(
            model_id=request.model_id,
            model_name=model_record.model_name,
            prediction=prediction,
            probability=probability,
            confidence=confidence,
        )
    except Exception as exc:
        logger.exception("Prediction error for model %s: %s", request.model_id, exc)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc


@router.get("/deployed-models")
def list_deployed_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    models = (
        db.query(TrainedModel)
        .filter(TrainedModel.user_id == current_user.id, TrainedModel.is_deployed == True)
        .all()
    )
    return [
        {
            "id": model.id,
            "model_name": model.model_name,
            "model_type": model.model_type,
            "task_type": model.task_type,
            "job_id": model.job_id,
        }
        for model in models
    ]
