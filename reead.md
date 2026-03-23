# SigmaCloud AI

SigmaCloud AI is a full-stack AutoML platform built to simulate the workflow of modern ML products: upload a dataset, analyze it, train multiple models automatically, compare results visually, deploy the best candidate, and run predictions from a live interface.

The project is designed to demonstrate product thinking, ML engineering, backend API design, and frontend dashboard development in one system.

## What This Project Does

SigmaCloud AI takes tabular datasets and turns them into an end-to-end machine learning workflow:

- Upload CSV or Excel datasets
- Load built-in example datasets for instant testing
- Auto-detect classification vs regression tasks
- Analyze dataset quality, missing values, types, and column-level patterns
- Recommend suitable models before training
- Train multiple models in one run
- Compare models on a leaderboard with metrics and visualizations
- Inspect feature importance and evaluation outputs
- Deploy a trained model
- Run predictions through the app using deployed models

## Why It Stands Out

This is not just a model training script. It is a product-style ML application with:

- A real backend API
- Persistent storage for users, datasets, jobs, and trained models
- Authentication with Google Sign-In and JWT sessions
- A modern dashboard UI for non-technical users
- Background model training with progress tracking
- Deployment and prediction workflows after training

It reflects the kind of system design used in internal ML platforms and lightweight commercial AutoML tools.

## Architecture

### Frontend

- Next.js 14
- TypeScript
- Tailwind CSS
- Recharts for model visualizations

The frontend provides:

- Landing page and product framing
- Auth flow with Google Sign-In
- Dataset management
- Training configuration UI
- Model leaderboard and charts
- Prediction and deployment screens

### Backend

- FastAPI
- SQLAlchemy
- Pydantic
- File-based model and dataset storage

The backend handles:

- Auth and session validation
- Dataset upload and metadata extraction
- Training job creation and status polling
- AutoML pipeline orchestration
- Model persistence and deployment state
- Prediction APIs
- Metrics aggregation for dashboard views

### ML Layer

- scikit-learn
- XGBoost
- LightGBM
- pandas / NumPy / joblib

The AutoML pipeline includes:

- Task-type detection
- Data cleaning
- Missing value handling
- Categorical encoding
- Numeric scaling
- Cross-validation
- Multi-model comparison
- Feature importance extraction

## Core Product Workflow

1. A user signs in with Google.
2. The user uploads a dataset or loads an example dataset.
3. The app inspects the data and suggests a task type and recommended models.
4. The backend trains multiple ML models in the background.
5. Results are stored and surfaced in a visual leaderboard.
6. The user deploys a model.
7. The user sends feature values to get live predictions.

## Technical Highlights

### 1. Full-Stack ML Product Thinking

The project goes beyond experimentation notebooks and shows how machine learning can be packaged into a usable product with a clean UI, persistent state, and user-specific workflows.

### 2. Real AutoML Pipeline Design

The training system performs preprocessing, task detection, cross-validation, metrics reporting, and multi-model evaluation automatically. It is structured more like a platform service than a one-off script.

### 3. User-Scoped Data Ownership

Datasets, jobs, and models are tied to authenticated users. This makes the platform closer to a real SaaS-style application than a demo with shared global state.

### 4. Recruiter-Friendly Engineering Breadth

This project demonstrates competency across:

- backend API development
- frontend application design
- database modeling
- authentication and authorization
- machine learning workflow orchestration
- data analysis and explainability
- Dockerized deployment setup

## Features Implemented

### Data Layer

- CSV and Excel upload support
- Example dataset loader
- Dataset previews
- Column metadata extraction
- Dataset analysis endpoint

### Training Layer

- Simple mode with recommended models
- Complex mode with manual model selection
- Configurable train/test split
- Configurable cross-validation folds
- Optional model-specific tuning parameters
- Progress tracking for training jobs

### Modeling Layer

Supported families in the current implementation include:

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

### Evaluation Layer

- Accuracy
- F1 score
- ROC-AUC
- RMSE
- MAE
- R2 score
- Confusion matrix
- ROC data
- Cross-validation scores
- Feature importance

### Product Layer

- Google authentication
- Protected API routes
- Model deployment toggle
- Download trained models as `.joblib`
- Prediction endpoint for deployed models
- Dashboard summary metrics

## What a Recruiter Should Take Away

SigmaCloud AI shows that I can build across the stack and connect product UX with backend systems and machine learning infrastructure.

This project demonstrates:

- Ability to design and ship a multi-page production-style web app
- Understanding of ML workflows beyond just model fitting
- Experience structuring backend services around clear API boundaries
- Ability to work with authentication, persistence, async job handling, and model serving
- Stronger engineering range than a notebook-only ML project

## Deployment Readiness

The project includes Docker-based service orchestration and environment-based configuration for local and production-style deployment. It is structured to run with:

- frontend service
- backend API
- PostgreSQL
- Redis

For local development, it can also run with a lighter setup.

## Repository Value

If someone reviews this repository, they should see evidence of:

- end-to-end ownership
- system design thinking
- practical ML engineering
- API and UI integration
- product-focused implementation

## Short Resume Description

Built a full-stack AutoML platform using FastAPI, Next.js, PostgreSQL, and scikit-learn/XGBoost/LightGBM that allows users to upload datasets, auto-train and compare multiple ML models, visualize results, deploy selected models, and generate live predictions through a web dashboard.
