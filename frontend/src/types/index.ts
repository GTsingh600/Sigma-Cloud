export interface ColumnInfo {
  name: string;
  dtype: string;
  null_count: number;
  unique_count: number;
  sample_values: unknown[];
  stats?: {
    min: number; max: number; mean: number; std: number; median: number;
  };
}

export interface Dataset {
  id: number;
  name: string;
  filename: string;
  file_size?: number;
  num_rows?: number;
  num_columns?: number;
  columns_info?: ColumnInfo[];
  target_column?: string;
  task_type?: string;
  is_example: boolean;
  preview_data?: Record<string, unknown>[];
  created_at: string;
}

export interface VisualizationSeries {
  key: string;
  label: string;
}

export interface DatasetVisualization {
  id: string;
  title: string;
  description: string;
  chart_type: "bar" | "grouped_bar" | "histogram" | "heatmap" | "scatter" | "box_summary" | string;
  x_key?: string;
  y_key?: string;
  series?: VisualizationSeries[];
  data: Record<string, unknown>[];
  value_format?: "percent" | "count" | "number" | "correlation" | string;
}

export interface DatasetAnalysisSummary {
  rows: number;
  columns: number;
  sampled_rows: number;
  numeric_columns: number;
  categorical_columns: number;
  missing_cells: number;
  missing_pct: number;
  target_column?: string;
}

export interface ExplainabilityFeature {
  feature: string;
  importance: number;
}

export interface ExplainabilityData {
  model_name: string;
  job_id: string;
  task_type: string;
  metric_label: string;
  metric_value?: number;
  feature_importance: ExplainabilityFeature[];
  insights: string[];
}

export interface DatasetAnalysis {
  summary: DatasetAnalysisSummary;
  insights: string[];
  visualizations: DatasetVisualization[];
  explainability?: ExplainabilityData | null;
}

export interface TrainingJob {
  id: number;
  job_id: string;
  dataset_id: number;
  task_type?: string;
  target_column: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface TrainingRecommendation {
  task_type: string;
  available_models: string[];
  recommended_models: string[];
  recommendation_reasons: string[];
  cleaning_preview: string[];
}

export interface TrainedModel {
  id: number;
  job_id: string;
  model_name: string;
  model_type: string;
  task_type: string;
  is_deployed: boolean;
  accuracy?: number;
  f1_score?: number;
  roc_auc?: number;
  rmse?: number;
  mae?: number;
  r2_score?: number;
  metrics?: Record<string, unknown>;
  feature_importance?: Record<string, number>;
  confusion_matrix?: number[][];
  roc_curve_data?: { fpr: number[]; tpr: number[] };
  cv_scores?: number[];
  cv_mean?: number;
  cv_std?: number;
  training_time?: number;
  created_at: string;
}

export interface MetricsData {
  job_id: string;
  task_type: string;
  status: string;
  training_mode?: string;
  selected_models?: string[];
  available_models?: string[];
  recommended_models?: string[];
  recommendation_reasons?: string[];
  cleaning_steps?: string[];
  performance_scatter?: {
    model_name: string;
    training_time?: number;
    primary_metric?: number;
    stability?: number;
  }[];
  models: TrainedModel[];
  best_model?: TrainedModel;
  leaderboard: {
    rank: number;
    model_name: string;
    primary_metric?: number;
    metric_name: string;
    training_time?: number;
  }[];
}

export interface PredictionResult {
  model_id: number;
  model_name: string;
  prediction: unknown;
  probability?: Record<string, number>;
  confidence?: number;
}

export interface ExampleDataset {
  key: string;
  name: string;
  description: string;
  target: string;
  task_type: string;
}

export interface User {
  id: number;
  email: string;
  name: string;
  picture?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
}
