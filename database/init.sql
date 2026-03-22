-- SigmaCloud AI - PostgreSQL Schema
-- Tables are also created automatically by SQLAlchemy on startup

CREATE TABLE IF NOT EXISTS datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_size INTEGER,
    num_rows INTEGER,
    num_columns INTEGER,
    columns_info JSONB,
    target_column VARCHAR(255),
    task_type VARCHAR(50),
    is_example BOOLEAN DEFAULT FALSE,
    preview_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS training_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) UNIQUE NOT NULL,
    dataset_id INTEGER REFERENCES datasets(id),
    task_type VARCHAR(50),
    target_column VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    error_message TEXT,
    config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS trained_models (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) REFERENCES training_jobs(job_id),
    model_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(100),
    task_type VARCHAR(50),
    file_path VARCHAR(512),
    is_deployed BOOLEAN DEFAULT FALSE,
    accuracy FLOAT,
    f1_score FLOAT,
    roc_auc FLOAT,
    rmse FLOAT,
    mae FLOAT,
    r2_score FLOAT,
    metrics JSONB,
    feature_importance JSONB,
    confusion_matrix JSONB,
    roc_curve_data JSONB,
    cv_scores JSONB,
    training_time FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_training_jobs_job_id ON training_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_trained_models_job_id ON trained_models(job_id);
CREATE INDEX IF NOT EXISTS idx_trained_models_deployed ON trained_models(is_deployed);
