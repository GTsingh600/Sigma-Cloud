"""
SigmaCloud AI - FastAPI Backend
Production-grade AutoML Platform
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
from logging.handlers import RotatingFileHandler
import os
from time import perf_counter
from uuid import uuid4

from app.api import auth, datasets, training, models, predictions, metrics
from app.core.auth import ensure_auth_schema
from app.core.config import settings
from app.core.database import engine, Base


# File-based logging setup
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "backend.log")

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=5)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers.clear()
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="SigmaCloud AI",
    description="Production-grade AutoML Platform - Train, Compare, and Deploy ML Models",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount static files for model downloads
os.makedirs(settings.MODEL_STORAGE_PATH, exist_ok=True)
os.makedirs(settings.DATASET_STORAGE_PATH, exist_ok=True)
app.mount("/static/models", StaticFiles(directory=settings.MODEL_STORAGE_PATH), name="models")

# Include routers
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(datasets.router, prefix="/api", tags=["Datasets"])
app.include_router(training.router, prefix="/api", tags=["Training"])
app.include_router(models.router, prefix="/api", tags=["Models"])
app.include_router(predictions.router, prefix="/api", tags=["Predictions"])
app.include_router(metrics.router, prefix="/api", tags=["Metrics"])


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with status code and response time."""
    request_id = str(uuid4())[:8]
    request.state.request_id = request_id
    start = perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (perf_counter() - start) * 1000
        logger.exception(
            "Unhandled request error | id=%s method=%s path=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    duration_ms = (perf_counter() - start) * 1000
    logger.info(
        "Request completed | id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Log HTTP exceptions with request context."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "HTTP exception | id=%s method=%s path=%s status=%s detail=%s",
        request_id,
        request.method,
        request.url.path,
        exc.status_code,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": request_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch and log unexpected exceptions with stack traces."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(
        "Unhandled exception | id=%s method=%s path=%s",
        request_id,
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    Base.metadata.create_all(bind=engine)
    ensure_auth_schema(engine)
    logger.info("🚀 SigmaCloud AI started successfully")
    logger.info(f"📊 Model storage: {settings.MODEL_STORAGE_PATH}")
    logger.info(f"📁 Dataset storage: {settings.DATASET_STORAGE_PATH}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "SigmaCloud AI",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    return {"message": "SigmaCloud AI API - Visit /api/docs for documentation"}
