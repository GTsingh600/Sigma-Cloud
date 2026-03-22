"""
SigmaCloud AI - Pydantic Schemas for API validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: Optional[str] = None

    class Config:
        from_attributes = True


class GoogleAuthRequest(BaseModel):
    credential: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── Dataset Schemas ──────────────────────────────────────────────────────────

class ColumnInfo(BaseModel):
    name: str
    dtype: str
    null_count: int
    unique_count: int
    sample_values: List[Any]
    stats: Optional[Dict[str, Any]] = None


class DatasetBase(BaseModel):
    name: str
    target_column: Optional[str] = None
    task_type: Optional[str] = None


class DatasetCreate(DatasetBase):
    pass


class DatasetResponse(DatasetBase):
    id: int
    filename: str
    file_size: Optional[int]
    num_rows: Optional[int]
    num_columns: Optional[int]
    columns_info: Optional[List[Dict[str, Any]]]
    is_example: bool
    preview_data: Optional[List[Dict[str, Any]]]
    created_at: datetime

    class Config:
        from_attributes = True


class VisualizationSeries(BaseModel):
    key: str
    label: str


class DatasetVisualization(BaseModel):
    id: str
    title: str
    description: str
    chart_type: str
    x_key: Optional[str] = None
    y_key: Optional[str] = None
    series: Optional[List[VisualizationSeries]] = None
    data: List[Dict[str, Any]]
    value_format: Optional[str] = None


class DatasetAnalysisSummary(BaseModel):
    rows: int
    columns: int
    sampled_rows: int
    numeric_columns: int
    categorical_columns: int
    missing_cells: int
    missing_pct: float
    target_column: Optional[str] = None


class ExplainabilityFeature(BaseModel):
    feature: str
    importance: float


class ExplainabilityResponse(BaseModel):
    model_name: str
    job_id: str
    task_type: str
    metric_label: str
    metric_value: Optional[float] = None
    feature_importance: List[ExplainabilityFeature]
    insights: List[str]


class DatasetAnalysisResponse(BaseModel):
    summary: DatasetAnalysisSummary
    insights: List[str]
    visualizations: List[DatasetVisualization]
    explainability: Optional[ExplainabilityResponse] = None


# ─── Training Schemas ─────────────────────────────────────────────────────────

class TrainingConfig(BaseModel):
    dataset_id: int
    target_column: str
    task_type: Optional[str] = None  # auto-detect if None
    mode: str = Field(default="simple", pattern="^(simple|complex)$")
    models_to_train: Optional[List[str]] = None  # train all if None
    tuning_params: Optional[Dict[str, Dict[str, Any]]] = None
    test_size: float = Field(default=0.2, ge=0.1, le=0.4)
    cv_folds: int = Field(default=5, ge=2, le=10)


class TrainingRecommendationRequest(BaseModel):
    dataset_id: int
    target_column: str
    task_type: Optional[str] = None


class TrainingRecommendationResponse(BaseModel):
    task_type: str
    available_models: List[str]
    recommended_models: List[str]
    recommendation_reasons: List[str]
    cleaning_preview: List[str]


class TrainingJobResponse(BaseModel):
    id: int
    job_id: str
    dataset_id: int
    task_type: Optional[str]
    target_column: str
    status: str
    progress: int
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Model Schemas ────────────────────────────────────────────────────────────

class ModelResponse(BaseModel):
    id: int
    job_id: str
    model_name: str
    model_type: str
    task_type: str
    is_deployed: bool
    accuracy: Optional[float]
    f1_score: Optional[float]
    roc_auc: Optional[float]
    rmse: Optional[float]
    mae: Optional[float]
    r2_score: Optional[float]
    metrics: Optional[Dict[str, Any]]
    feature_importance: Optional[Dict[str, float]]
    confusion_matrix: Optional[List[List[int]]]
    roc_curve_data: Optional[Dict[str, List[float]]]
    cv_scores: Optional[List[float]]
    training_time: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Prediction Schemas ───────────────────────────────────────────────────────

class PredictionRequest(BaseModel):
    model_id: int
    features: Dict[str, Any]


class PredictionResponse(BaseModel):
    model_id: int
    model_name: str
    prediction: Any
    probability: Optional[Dict[str, float]] = None
    confidence: Optional[float] = None


# ─── Metrics Schemas ──────────────────────────────────────────────────────────

class MetricsResponse(BaseModel):
    job_id: str
    models: List[ModelResponse]
    best_model: Optional[ModelResponse]
    task_type: str
