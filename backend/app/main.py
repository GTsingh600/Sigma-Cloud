"""
SigmaCloud AI - FastAPI Backend
Production-grade AutoML Platform
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import auth, datasets, metrics, models, predictions, training
from app.api.training import reconcile_stale_jobs
from app.core.auth import ensure_auth_schema
from app.core.config import settings
from app.core.database import Base, engine

# Boot timestamp powers the cold-start hint the frontend shows to first-time
# visitors on a sleepy free tier.
PROCESS_STARTED_AT = time.time()


def configure_logging() -> None:
    handlers: list[logging.Handler] = []

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    handlers.append(console_handler)

    # Off by default: hosts like Render use ephemeral disks and already collect
    # stdout, so file logs cost I/O and disappear on restart anyway.
    if settings.LOG_TO_FILE:
        log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "backend.log"), maxBytes=5 * 1024 * 1024, backupCount=3
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        handlers.append(file_handler)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    for handler in handlers:
        root_logger.addHandler(handler)


configure_logging()
logger = logging.getLogger(__name__)


def warn_on_permissive_cors() -> None:
    if not settings.ALLOWED_ORIGINS and not settings.ALLOWED_ORIGIN_REGEX:
        logger.warning(
            "No CORS origins configured. Set ALLOWED_ORIGINS to your frontend URL, "
            'e.g. ALLOWED_ORIGINS=["https://your-app.vercel.app"]'
        )
    if ".vercel.app" in settings.ALLOWED_ORIGIN_REGEX or ".onrender.com" in settings.ALLOWED_ORIGIN_REGEX:
        logger.warning(
            "ALLOWED_ORIGIN_REGEX matches an entire hosting provider. Any site on "
            "that domain can call this API - narrow it to your own deployments."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown work (replaces the deprecated @app.on_event)."""
    Base.metadata.create_all(bind=engine)
    ensure_auth_schema(engine)
    warn_on_permissive_cors()

    try:
        reconcile_stale_jobs()
    except Exception:
        logger.exception("Stale job reconciliation failed")

    logger.info("SigmaCloud AI started | env=%s", settings.ENVIRONMENT)
    logger.info("Model storage: %s", settings.MODEL_STORAGE_PATH)
    logger.info("Dataset storage: %s", settings.DATASET_STORAGE_PATH)

    yield

    logger.info("SigmaCloud AI shutting down")


app = FastAPI(
    title="SigmaCloud AI",
    description="Production-grade AutoML Platform - Train, Compare, and Deploy ML Models",
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# One CORS layer. A second hand-rolled middleware duplicated this and could
# emit conflicting headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=settings.ALLOWED_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

os.makedirs(settings.MODEL_STORAGE_PATH, exist_ok=True)
os.makedirs(settings.DATASET_STORAGE_PATH, exist_ok=True)

# NOTE: model artifacts are deliberately NOT mounted as static files. Serving
# the storage directory would expose every user's .joblib to anyone who can
# guess a filename; downloads go through the authenticated /api/models/{id}
# /download route instead.

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
        headers=getattr(exc, "headers", None),
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


@app.get("/api/health")
async def health_check():
    """Health probe. Also the endpoint a keep-alive pinger should hit."""
    database_ok = True
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        database_ok = False
        logger.warning("Health check database probe failed: %s", exc)

    uptime_seconds = round(time.time() - PROCESS_STARTED_AT, 1)
    return {
        "status": "healthy" if database_ok else "degraded",
        "service": "SigmaCloud AI",
        "version": settings.VERSION,
        "database": "up" if database_ok else "down",
        "uptime_seconds": uptime_seconds,
        # Under a minute of uptime means this request very likely just woke the
        # service; the frontend uses it to explain the delay to first visitors.
        "recently_started": uptime_seconds < 60,
    }


@app.get("/")
async def root():
    return {"message": "SigmaCloud AI API - Visit /api/docs for documentation"}
