# SigmaCloud AI

SigmaCloud AI is a full-stack AutoML platform that turns raw tabular data into a production-style machine learning workflow. A user can upload a dataset, inspect data quality, train multiple models automatically, compare results on a leaderboard, deploy a selected model, and generate live predictions from a web dashboard.

This project was built to demonstrate the intersection of software engineering and machine learning engineering: backend APIs, frontend product design, database-backed workflows, async job orchestration, model evaluation, and inference delivery in one system.

## Why This Project Matters

Most ML portfolio projects stop at notebooks or a single training script. SigmaCloud AI is intentionally built as a product:

- Multi-page web application with authentication
- Backend API designed around user workflows
- Persistent storage for users, datasets, jobs, and models
- Automated ML pipeline with multiple algorithms
- Visualization layer for model comparison and explainability
- Deployment and prediction flow after training

For an SDE reviewer, this shows API design, data modeling, state management, and full-stack integration.

For an AI/ML reviewer, this shows preprocessing design, task detection, cross-validation, multi-model benchmarking, explainability, and model serving.

## Product Workflow

1. Sign in with Google.
2. Upload a CSV/Excel dataset or load an example dataset.
3. Inspect dataset structure and quality.
4. Auto-detect the task type or choose it manually.
5. Get recommended models before training.
6. Launch a background AutoML job.
7. Compare trained models on a leaderboard.
8. Inspect metrics, feature importance, and evaluation artifacts.
9. Deploy a model and run predictions from the app.

## Core Features

### Data Ingestion and Analysis

- CSV and Excel upload support
- Built-in example datasets for instant testing
- Dataset preview and metadata extraction
- Column-level statistics and missing value analysis
- Exploratory dataset analysis for target-aware inspection

### AutoML Training

- Automatic classification vs regression detection
- Simple mode with recommended models
- Complex mode with manual model selection
- Configurable train/test split and cross-validation
- Model-specific tuning inputs for deeper control
- Background training with progress tracking

### Modeling and Evaluation

Supported model families in the current implementation include:

- Logistic Regression
- Ridge Regression
- Elastic Net
- Random Forest
- Extra Trees
- Gradient Boosting
- AdaBoost
- XGBoost
- LightGBM
- SVC / SVR
- KNN

Evaluation outputs include:

- Accuracy
- F1 score
- ROC-AUC
- RMSE
- MAE
- R2 score
- Confusion matrix
- ROC curve data
- Cross-validation scores
- Feature importance

### Deployment and Inference

- User-scoped trained model storage
- Model deployment and undeployment
- Download trained models as `.joblib`
- Prediction API for live inference
- Dashboard summaries for datasets, models, and jobs

## Architecture

### Frontend

- Next.js 14
- TypeScript
- Tailwind CSS
- Recharts

The frontend is structured as a dashboard product rather than a static demo. It includes authenticated flows for dataset management, training configuration, model comparison, deployment, and prediction.

### Backend

- FastAPI
- SQLAlchemy
- Pydantic
- JWT-based auth session handling

The backend exposes APIs for authentication, dataset upload, training jobs, metrics aggregation, deployment state, and prediction. It also owns persistence, request logging, CORS handling, and model artifact access.

### ML Stack

- scikit-learn
- XGBoost
- LightGBM
- pandas
- NumPy
- joblib

The ML layer handles preprocessing, model orchestration, evaluation, serialization, and feature-importance reporting for structured/tabular datasets.

### Infrastructure

- PostgreSQL-ready Docker setup
- Redis included for production-style async architecture
- Docker Compose for full-stack local deployment
- Environment-driven configuration for local and production use

## Engineering Highlights

### 1. End-to-End System Design

This project is built as a complete workflow, not as isolated components. The frontend, backend, storage layer, training engine, and inference path all connect around a coherent user journey.

### 2. Product-Oriented Backend Modeling

The data model is user-centric: users own datasets, datasets produce training jobs, and jobs produce trained models. That structure mirrors how real internal tools and SaaS platforms are organized.

### 3. Practical AutoML Pipeline Design

The training pipeline performs:

- task-type inference
- preprocessing for numeric and categorical features
- missing-value handling
- encoding and scaling
- multi-model training
- cross-validation
- metrics collection
- artifact serialization

That makes the project much closer to an ML platform service than a notebook experiment.

### 4. Separation of Concerns

The codebase is organized into clear layers:

- API routers for user-facing endpoints
- core configuration and database setup
- ORM models for persistence
- ML modules for training and analysis
- frontend app routes and reusable components

This makes the project easier to extend and easier to reason about in a production setting.

### 5. Recruiter-Relevant Breadth

SigmaCloud AI demonstrates practical ability across:

- full-stack web development
- backend API implementation
- database-backed application design
- authentication and authorization
- machine learning workflow orchestration
- model evaluation and explainability
- deployment-aware engineering

## Repository Structure

```text
sigmacloud/
├── backend/                 # FastAPI backend and ML pipeline
├── frontend/                # Next.js dashboard frontend
├── database/                # SQL/bootstrap assets
├── logs/                    # Runtime logs
├── docker-compose.yml       # Full-stack local orchestration
└── README.md
```

## What a Reviewer Should Take Away

### For Software Engineering Roles

This project shows that I can design and implement a full-stack application with:

- clear API boundaries
- persistent data models
- authenticated user workflows
- asynchronous processing
- modular backend structure
- polished frontend product flows

### For AI / ML Roles

This project shows that I can move beyond model training alone and build ML systems that include:

- preprocessing pipelines
- task detection
- model recommendation logic
- cross-validation and evaluation reporting
- explainability outputs
- model packaging and inference serving

## Resume-Ready Summary

Built a full-stack AutoML platform using FastAPI, Next.js, SQLAlchemy, PostgreSQL-ready infrastructure, and scikit-learn/XGBoost/LightGBM to let users upload datasets, analyze data quality, auto-train and compare multiple ML models, deploy selected models, and run live predictions through a production-style web dashboard.

## Tech Stack

- Frontend: Next.js, TypeScript, Tailwind CSS, Recharts
- Backend: FastAPI, SQLAlchemy, Pydantic
- ML: scikit-learn, XGBoost, LightGBM, pandas, NumPy
- Auth: Google Sign-In, JWT
- Infra: Docker, Docker Compose, PostgreSQL, Redis

## Future Improvements

- Add Alembic migrations for production-grade schema management
- Move long-running training to dedicated workers by default
- Add object storage support for dataset/model artifacts
- Add experiment history and richer model lineage
- Expand evaluation and explainability support
