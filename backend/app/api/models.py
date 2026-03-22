"""
SigmaCloud AI - Models API Router
List, retrieve, deploy, and download trained models.
"""
import os
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.db_models import TrainedModel, User
from app.schemas.schemas import ModelResponse


router = APIRouter()
logger = logging.getLogger(__name__)


def get_owned_model(model_id: int, user_id: int, db: Session) -> TrainedModel:
    model = db.query(TrainedModel).filter(TrainedModel.id == model_id, TrainedModel.user_id == user_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.get("/models", response_model=List[ModelResponse])
def list_models(
    job_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(TrainedModel).filter(TrainedModel.user_id == current_user.id)
    if job_id:
        query = query.filter(TrainedModel.job_id == job_id)
    return query.order_by(TrainedModel.created_at.desc()).all()


@router.get("/models/{model_id}", response_model=ModelResponse)
def get_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_owned_model(model_id, current_user.id, db)


@router.post("/models/{model_id}/deploy")
def deploy_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model = get_owned_model(model_id, current_user.id, db)

    db.query(TrainedModel).filter(
        TrainedModel.user_id == current_user.id,
        TrainedModel.job_id == model.job_id,
        TrainedModel.id != model_id,
    ).update({"is_deployed": False})

    model.is_deployed = True
    db.commit()
    logger.info("Model %s deployed for user=%s", model_id, current_user.id)
    return {"message": f"Model '{model.model_name}' deployed successfully", "model_id": model_id}


@router.post("/models/{model_id}/undeploy")
def undeploy_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model = get_owned_model(model_id, current_user.id, db)
    model.is_deployed = False
    db.commit()
    return {"message": "Model undeployed"}


@router.get("/models/{model_id}/download")
def download_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model = get_owned_model(model_id, current_user.id, db)
    if not model.file_path or not os.path.exists(model.file_path):
        raise HTTPException(status_code=404, detail="Model file not found on disk")

    filename = f"{model.model_name.replace(' ', '_')}_{model_id}.joblib"
    return FileResponse(path=model.file_path, media_type="application/octet-stream", filename=filename)


@router.delete("/models/{model_id}")
def delete_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model = get_owned_model(model_id, current_user.id, db)

    if model.file_path and os.path.exists(model.file_path):
        os.remove(model.file_path)

    db.delete(model)
    db.commit()
    return {"message": "Model deleted successfully"}
