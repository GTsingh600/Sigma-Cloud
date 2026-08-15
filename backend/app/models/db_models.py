"""
SigmaCloud AI - SQLAlchemy Database Models
"""
import os

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_sub = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    picture = Column(String(1024))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # delete-orphan keeps cleanup correct on SQLite too, where foreign keys are
    # not enforced by default and ON DELETE CASCADE would silently do nothing.
    datasets = relationship(
        "Dataset", back_populates="user", cascade="all, delete-orphan"
    )
    training_jobs = relationship(
        "TrainingJob", back_populates="user", cascade="all, delete-orphan"
    )
    trained_models = relationship(
        "TrainedModel", back_populates="user", cascade="all, delete-orphan"
    )


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (Index("ix_dataset_user_created", "user_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    name = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer)
    num_rows = Column(Integer)
    num_columns = Column(Integer)
    columns_info = Column(JSON)
    target_column = Column(String(255))
    task_type = Column(String(50))
    is_example = Column(Boolean, default=False)
    preview_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="datasets")
    training_jobs = relationship(
        "TrainingJob", back_populates="dataset", cascade="all, delete-orphan"
    )

    @property
    def file_available(self) -> bool:
        """Whether the backing file still exists.

        Hosts with ephemeral disks wipe storage on restart while the database
        row survives, so the UI needs to distinguish "deleted" from "evaporated".
        """
        return bool(self.file_path) and os.path.exists(self.file_path)


class TrainingJob(Base):
    __tablename__ = "training_jobs"
    __table_args__ = (Index("ix_job_user_created", "user_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    task_type = Column(String(50))
    target_column = Column(String(255))
    status = Column(String(50), default="pending", index=True)
    progress = Column(Integer, default=0)
    progress_message = Column(String(255))
    error_message = Column(Text)
    config = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="training_jobs")
    dataset = relationship("Dataset", back_populates="training_jobs")
    trained_models = relationship(
        "TrainedModel", back_populates="training_job", cascade="all, delete-orphan"
    )


class TrainedModel(Base):
    __tablename__ = "trained_models"
    __table_args__ = (Index("ix_model_user_created", "user_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), ForeignKey("training_jobs.job_id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    model_name = Column(String(255), nullable=False)
    model_type = Column(String(100))
    task_type = Column(String(50))
    file_path = Column(String(512))
    is_deployed = Column(Boolean, default=False, index=True)
    accuracy = Column(Float)
    f1_score = Column(Float)
    roc_auc = Column(Float)
    rmse = Column(Float)
    mae = Column(Float)
    r2_score = Column(Float)
    metrics = Column(JSON)
    feature_importance = Column(JSON)
    confusion_matrix = Column(JSON)
    roc_curve_data = Column(JSON)
    cv_scores = Column(JSON)
    training_time = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="trained_models")
    training_job = relationship("TrainingJob", back_populates="trained_models")

    @property
    def file_available(self) -> bool:
        """Whether the serialized model is still on disk (see Dataset)."""
        return bool(self.file_path) and os.path.exists(self.file_path)
