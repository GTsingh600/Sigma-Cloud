# SigmaCloud AI

I built SigmaCloud AI to explore what it looks like to turn a machine learning workflow into an actual product instead of stopping at notebooks or standalone training scripts.

The idea was simple: a user should be able to upload a tabular dataset, understand the data, train multiple models automatically, compare the results, deploy one of them, and run predictions from a clean web interface.

This project combines the parts I enjoy most: backend systems, frontend product work, and practical ML engineering.

## What it does

SigmaCloud AI lets a user:

- sign in with Google
- upload a CSV or Excel dataset
- load built-in example datasets
- inspect dataset structure and quality
- auto-detect whether the task is classification or regression
- get model recommendations before training
- train multiple models in one run
- compare results on a leaderboard
- inspect metrics like accuracy, F1, ROC-AUC, RMSE, MAE, and R2
- look at feature importance and evaluation outputs
- deploy a trained model
- make predictions from the app

## Why I built it this way

A lot of ML projects look impressive at first glance but don’t really show how models fit into a usable system. I wanted this one to feel closer to a real internal ML platform or lightweight SaaS product.

So instead of focusing only on model training, I built the full workflow around it:

- authentication
- dataset storage
- job tracking
- model persistence
- metrics APIs
- dashboard UX
- deployment state
- prediction serving

That gave me a chance to work across the full stack while still keeping the ML side meaningful.

## Tech stack

### Frontend

- Next.js 14
- TypeScript
- Tailwind CSS
- Recharts

### Backend

- FastAPI
- SQLAlchemy
- Pydantic
- JWT auth

### ML

- scikit-learn
- XGBoost
- LightGBM
- pandas
- NumPy
- joblib

### Infra

- Docker
- Docker Compose
- PostgreSQL-ready setup
- Redis-ready async setup

## Main workflow

1. The user signs in.
2. They upload a dataset or load an example one.
3. The app extracts metadata and shows a preview of the data.
4. The backend recommends models and prepares a training plan.
5. A background training job runs multiple models.
6. Results are stored and shown in the dashboard.
7. The user can deploy a model and use it for predictions.

## Models supported

The current implementation supports multiple model families depending on the task type, including:

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

## What I wanted this project to show

For software engineering roles, I wanted this repo to show that I can build a complete application with:

- a clear backend structure
- API design around real user workflows
- data modeling and persistence
- auth and protected routes
- async job handling
- frontend and backend integration

For AI/ML roles, I wanted it to show that I understand more than just fitting a model:

- preprocessing pipelines
- task detection
- model comparison
- cross-validation
- evaluation reporting
- feature importance
- model serialization and inference

## Project structure

```text
sigmacloud/
├── backend/        # FastAPI app, APIs, database layer, ML pipeline
├── frontend/       # Next.js app and dashboard UI
├── database/       # SQL/bootstrap files
├── logs/           # runtime logs
└── docker-compose.yml
```

## A few implementation details I’m happy with

- The training flow is user-scoped, so datasets, jobs, and models belong to the authenticated user.
- The app doesn’t just train models, it surfaces recommendations, cleaning previews, evaluation outputs, and deployment actions.
- The backend and frontend are separated cleanly enough that the system feels extensible rather than hardcoded around one demo.
- The project is structured like an application I could keep improving, not just a one-time showcase.

## What I’d improve next

If I continue building on this, the next things I’d add are:

- Alembic migrations for cleaner schema evolution
- dedicated workers for longer training jobs
- object storage for datasets and model artifacts
- richer experiment tracking
- more explainability and model monitoring features

## Resume version

Built a full-stack AutoML platform using FastAPI, Next.js, SQLAlchemy, and scikit-learn/XGBoost/LightGBM that lets users upload datasets, analyze data quality, train and compare multiple ML models, deploy selected models, and run live predictions through a web dashboard.
