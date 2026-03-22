"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import {
  AlertTriangle,
  BrainCircuit,
  CheckCircle,
  ChevronRight,
  Loader2,
  Play,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";

import { datasetsAPI, trainingAPI } from "@/lib/api";
import { Dataset, TrainingJob, TrainingRecommendation } from "@/types";

const MODEL_OPTIONS = [
  { name: "Logistic Regression", tasks: ["classification"], tag: "baseline", desc: "Fast interpretable baseline for classification." },
  { name: "Random Forest", tasks: ["classification", "regression"], tag: "ensemble", desc: "Strong general-purpose tree ensemble." },
  { name: "Extra Trees", tasks: ["classification", "regression"], tag: "ensemble", desc: "High-variance ensemble that often boosts accuracy." },
  { name: "XGBoost", tasks: ["classification", "regression"], tag: "boosting", desc: "Powerful boosted trees for complex signal." },
  { name: "LightGBM", tasks: ["classification", "regression"], tag: "boosting", desc: "Efficient gradient boosting for larger datasets." },
  { name: "Gradient Boosting", tasks: ["classification", "regression"], tag: "boosting", desc: "Reliable boosting option for structured data." },
  { name: "AdaBoost", tasks: ["classification", "regression"], tag: "boosting", desc: "Lightweight boosted ensemble for fast experimentation." },
  { name: "SVC", tasks: ["classification"], tag: "kernel", desc: "Useful for smaller classification datasets." },
  { name: "KNN", tasks: ["classification", "regression"], tag: "distance", desc: "Local neighborhood model for pattern-based prediction." },
  { name: "Ridge Regression", tasks: ["regression"], tag: "baseline", desc: "Stable linear baseline for regression." },
  { name: "Elastic Net", tasks: ["regression"], tag: "linear", desc: "Regularized linear model with sparse feature selection." },
  { name: "SVR", tasks: ["regression"], tag: "kernel", desc: "Kernel regression for smaller numeric datasets." },
];

const DEFAULT_TUNING: Record<string, Record<string, string>> = {
  "Logistic Regression": { C: "1.0" },
  "Random Forest": { n_estimators: "160", max_depth: "" },
  "Extra Trees": { n_estimators: "160", max_depth: "" },
  "XGBoost": { n_estimators: "180", max_depth: "6", learning_rate: "0.08" },
  "LightGBM": { n_estimators: "180", max_depth: "", learning_rate: "0.08" },
  "Gradient Boosting": { n_estimators: "160", learning_rate: "0.08" },
  "AdaBoost": { n_estimators: "90", learning_rate: "0.8" },
  "SVC": { C: "1.0" },
  "KNN": { n_neighbors: "7" },
  "Ridge Regression": { alpha: "1.0" },
  "Elastic Net": { alpha: "0.05", l1_ratio: "0.5" },
  "SVR": { C: "1.0", epsilon: "0.1" },
};

const TUNING_FIELDS: Record<string, { key: string; label: string; step?: string; placeholder?: string }[]> = {
  "Logistic Regression": [{ key: "C", label: "Regularization C", step: "0.1" }],
  "Random Forest": [
    { key: "n_estimators", label: "Trees", step: "10" },
    { key: "max_depth", label: "Max Depth", step: "1", placeholder: "auto" },
  ],
  "Extra Trees": [
    { key: "n_estimators", label: "Trees", step: "10" },
    { key: "max_depth", label: "Max Depth", step: "1", placeholder: "auto" },
  ],
  "XGBoost": [
    { key: "n_estimators", label: "Trees", step: "10" },
    { key: "max_depth", label: "Max Depth", step: "1" },
    { key: "learning_rate", label: "Learning Rate", step: "0.01" },
  ],
  "LightGBM": [
    { key: "n_estimators", label: "Trees", step: "10" },
    { key: "max_depth", label: "Max Depth", step: "1", placeholder: "auto" },
    { key: "learning_rate", label: "Learning Rate", step: "0.01" },
  ],
  "Gradient Boosting": [
    { key: "n_estimators", label: "Stages", step: "10" },
    { key: "learning_rate", label: "Learning Rate", step: "0.01" },
  ],
  "AdaBoost": [
    { key: "n_estimators", label: "Stages", step: "10" },
    { key: "learning_rate", label: "Learning Rate", step: "0.05" },
  ],
  "SVC": [{ key: "C", label: "Margin C", step: "0.1" }],
  "KNN": [{ key: "n_neighbors", label: "Neighbors", step: "1" }],
  "Ridge Regression": [{ key: "alpha", label: "Alpha", step: "0.1" }],
  "Elastic Net": [
    { key: "alpha", label: "Alpha", step: "0.01" },
    { key: "l1_ratio", label: "L1 Ratio", step: "0.05" },
  ],
  "SVR": [
    { key: "C", label: "Margin C", step: "0.1" },
    { key: "epsilon", label: "Epsilon", step: "0.01" },
  ],
};

function cloneDefaultTuning() {
  return JSON.parse(JSON.stringify(DEFAULT_TUNING)) as Record<string, Record<string, string>>;
}

function serializeTuningParams(values: Record<string, Record<string, string>>) {
  const serialized: Record<string, Record<string, number>> = {};
  Object.entries(values).forEach(([model, params]) => {
    const clean: Record<string, number> = {};
    Object.entries(params).forEach(([key, value]) => {
      if (value === "") return;
      const numeric = Number(value);
      if (!Number.isNaN(numeric)) clean[key] = numeric;
    });
    if (Object.keys(clean).length > 0) serialized[model] = clean;
  });
  return serialized;
}

export default function TrainingPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [targetColumn, setTargetColumn] = useState("");
  const [taskType, setTaskType] = useState("auto");
  const [mode, setMode] = useState<"simple" | "complex">("simple");
  const [testSize, setTestSize] = useState(0.2);
  const [cvFolds, setCvFolds] = useState(5);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [tuningParams, setTuningParams] = useState<Record<string, Record<string, string>>>(cloneDefaultTuning());
  const [recommendation, setRecommendation] = useState<TrainingRecommendation | null>(null);
  const [recommendationLoading, setRecommendationLoading] = useState(false);
  const [currentJob, setCurrentJob] = useState<TrainingJob | null>(null);
  const [training, setTraining] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    datasetsAPI.list().then(r => setDatasets(r.data)).catch(() => {});
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  useEffect(() => {
    if (!selectedDataset || !targetColumn) {
      setRecommendation(null);
      return;
    }
    setRecommendationLoading(true);
    trainingAPI.recommend({
      dataset_id: selectedDataset.id,
      target_column: targetColumn,
      task_type: taskType === "auto" ? undefined : taskType,
    })
      .then(r => {
        setRecommendation(r.data);
        setSelectedModels(prev => {
          if (mode === "simple") return r.data.recommended_models;
          return prev.length > 0 ? prev : r.data.recommended_models;
        });
      })
      .catch(() => setRecommendation(null))
      .finally(() => setRecommendationLoading(false));
  }, [selectedDataset, targetColumn, taskType, mode]);

  const effectiveTaskType = taskType === "auto" ? recommendation?.task_type : taskType;
  const visibleModels = useMemo(() => {
    const available = recommendation?.available_models;
    if (available?.length) {
      return MODEL_OPTIONS.filter(model => available.includes(model.name));
    }
    if (!effectiveTaskType) return MODEL_OPTIONS;
    return MODEL_OPTIONS.filter(model => model.tasks.includes(effectiveTaskType));
  }, [recommendation, effectiveTaskType]);

  const pollStatus = (jobId: string) => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await trainingAPI.getStatus(jobId);
        setCurrentJob(res.data);
        if (res.data.status === "completed" || res.data.status === "failed") {
          clearInterval(pollRef.current!);
          setTraining(false);
          if (res.data.status === "completed") toast.success("Training completed!");
          else toast.error(`Training failed: ${res.data.error_message}`);
        }
      } catch {
        clearInterval(pollRef.current!);
        setTraining(false);
      }
    }, 1500);
  };

  const handleDatasetSelect = (dataset: Dataset) => {
    setSelectedDataset(dataset);
    if (dataset.target_column) setTargetColumn(dataset.target_column);
    if (dataset.task_type) setTaskType(dataset.task_type);
  };

  const toggleModel = (modelName: string) => {
    setSelectedModels(current =>
      current.includes(modelName) ? current.filter(name => name !== modelName) : [...current, modelName]
    );
  };

  const updateTuning = (modelName: string, key: string, value: string) => {
    setTuningParams(current => ({
      ...current,
      [modelName]: {
        ...(current[modelName] || {}),
        [key]: value,
      },
    }));
  };

  const startTraining = async () => {
    if (!selectedDataset) return toast.error("Select a dataset");
    if (!targetColumn) return toast.error("Enter target column");
    const modelsForRun = mode === "simple" ? recommendation?.recommended_models || selectedModels : selectedModels;
    if (!modelsForRun.length) return toast.error("Select at least one model");

    setTraining(true);
    setCurrentJob(null);
    try {
      const res = await trainingAPI.train({
        dataset_id: selectedDataset.id,
        target_column: targetColumn,
        task_type: taskType === "auto" ? undefined : taskType,
        mode,
        models_to_train: modelsForRun,
        tuning_params: mode === "complex" ? serializeTuningParams(tuningParams) : undefined,
        test_size: testSize,
        cv_folds: cvFolds,
      });
      setCurrentJob(res.data);
      toast.success("Training started!");
      pollStatus(res.data.job_id);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to start training");
      setTraining(false);
    }
  };

  const progressBar = currentJob?.progress || 0;

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-white mb-1">Train Models</h1>
        <p className="text-sigma-500">Choose a training mode, review recommended models, and tune only when you need deeper control.</p>
      </div>

      <div className="grid xl:grid-cols-[1.15fr_0.85fr] gap-6">
        <div className="sigma-card">
          <h2 className="font-display font-semibold text-white mb-5 flex items-center gap-2">
            <BrainCircuit className="w-4 h-4 text-sigma-400" /> Training Config
          </h2>

          <div className="grid md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-xs text-sigma-400 mb-1.5 block">Dataset *</label>
              {datasets.length === 0 ? (
                <div className="text-sm text-sigma-500 bg-sigma-900/40 rounded-lg p-3">
                  No datasets. <Link href="/dashboard/datasets" className="text-sigma-400 underline">Upload one</Link>
                </div>
              ) : (
                <select
                  value={selectedDataset?.id ?? ""}
                  onChange={e => {
                    const dataset = datasets.find(item => item.id === Number(e.target.value));
                    if (dataset) handleDatasetSelect(dataset);
                  }}
                  className="w-full bg-sigma-900/50 border border-sigma-700/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sigma-500"
                >
                  <option value="">Select dataset...</option>
                  {datasets.map(dataset => (
                    <option key={dataset.id} value={dataset.id}>
                      {dataset.name} ({dataset.num_rows} rows)
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div>
              <label className="text-xs text-sigma-400 mb-1.5 block">Target Column *</label>
              {selectedDataset ? (
                <select
                  value={targetColumn}
                  onChange={e => setTargetColumn(e.target.value)}
                  className="w-full bg-sigma-900/50 border border-sigma-700/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sigma-500"
                >
                  <option value="">Select target...</option>
                  {selectedDataset.columns_info?.map(column => (
                    <option key={column.name} value={column.name}>
                      {column.name} ({column.dtype})
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  value={targetColumn}
                  onChange={e => setTargetColumn(e.target.value)}
                  placeholder="e.g. price, survived"
                  className="w-full bg-sigma-900/50 border border-sigma-700/50 rounded-lg px-3 py-2 text-sm text-white placeholder-sigma-600 focus:outline-none focus:border-sigma-500"
                />
              )}
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-xs text-sigma-400 mb-1.5 block">Task Type</label>
              <select
                value={taskType}
                onChange={e => setTaskType(e.target.value)}
                className="w-full bg-sigma-900/50 border border-sigma-700/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sigma-500"
              >
                <option value="auto">Auto-detect</option>
                <option value="classification">Classification</option>
                <option value="regression">Regression</option>
              </select>
            </div>

            <div>
              <label className="text-xs text-sigma-400 mb-1.5 block">Training Mode</label>
              <div className="grid grid-cols-2 gap-2">
                {(["simple", "complex"] as const).map(option => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setMode(option)}
                    className={`rounded-lg border px-3 py-2 text-sm ${mode === option ? "border-sigma-500 bg-sigma-600/15 text-white" : "border-sigma-800 bg-sigma-900/30 text-sigma-400"}`}
                  >
                    {option === "simple" ? "Simple" : "Complex"}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4 mb-6">
            <div>
              <label className="text-xs text-sigma-400 mb-1.5 block">Test Size: {(testSize * 100).toFixed(0)}%</label>
              <input type="range" min="0.1" max="0.4" step="0.05" value={testSize} onChange={e => setTestSize(Number(e.target.value))} className="w-full accent-sigma-500" />
            </div>
            <div>
              <label className="text-xs text-sigma-400 mb-1.5 block">CV Folds: {cvFolds}</label>
              <input type="range" min="2" max="10" step="1" value={cvFolds} onChange={e => setCvFolds(Number(e.target.value))} className="w-full accent-sigma-500" />
            </div>
          </div>

          <div className="rounded-2xl border border-sigma-800/60 bg-sigma-950/30 p-4 mb-6">
            <div className="flex items-center gap-2 text-sm font-medium text-white mb-3">
              <Sparkles className="w-4 h-4 text-sigma-400" />
              Model recommendations
            </div>
            {recommendationLoading ? (
              <div className="text-sm text-sigma-400 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzing dataset and recommending models...
              </div>
            ) : recommendation ? (
              <>
                <div className="flex flex-wrap gap-2 mb-3">
                  {recommendation.recommended_models.map(model => (
                    <span key={model} className="metric-badge text-sigma-200">
                      {model}
                    </span>
                  ))}
                </div>
                <div className="space-y-2 text-sm text-sigma-300">
                  {recommendation.recommendation_reasons.map(reason => (
                    <div key={reason}>{reason}</div>
                  ))}
                </div>
              </>
            ) : (
              <div className="text-sm text-sigma-500">Pick a dataset and target column to get recommendations.</div>
            )}
          </div>

          {mode === "simple" ? (
            <div className="rounded-2xl border border-sigma-800/60 bg-sigma-950/30 p-4 mb-6">
              <div className="text-sm font-medium text-white mb-2">Simple mode</div>
              <p className="text-sm text-sigma-400 mb-3">
                Uses the recommended models and standard training defaults so you can launch fast.
              </p>
              <div className="flex flex-wrap gap-2">
                {(recommendation?.recommended_models || selectedModels).map(model => (
                  <span key={model} className="metric-badge text-sigma-200">{model}</span>
                ))}
              </div>
            </div>
          ) : (
            <>
              <div className="rounded-2xl border border-sigma-800/60 bg-sigma-950/30 p-4 mb-6">
                <div className="flex items-center gap-2 text-sm font-medium text-white mb-3">
                  <SlidersHorizontal className="w-4 h-4 text-sigma-400" />
                  Complex mode: select models
                </div>
                <div className="grid lg:grid-cols-2 gap-3">
                  {visibleModels.map(model => {
                    const selected = selectedModels.includes(model.name);
                    const recommended = recommendation?.recommended_models.includes(model.name);
                    return (
                      <button
                        key={model.name}
                        type="button"
                        onClick={() => toggleModel(model.name)}
                        className={`rounded-xl border p-4 text-left transition-all ${selected ? "border-sigma-500 bg-sigma-600/10" : "border-sigma-800 bg-sigma-900/25"}`}
                      >
                        <div className="flex items-center justify-between gap-3 mb-2">
                          <div className="font-medium text-white text-sm">{model.name}</div>
                          <div className="flex gap-2">
                            {recommended && <span className="metric-badge text-sigma-200">recommended</span>}
                            <span className="metric-badge text-sigma-400">{model.tag}</span>
                          </div>
                        </div>
                        <div className="text-xs text-sigma-500">{model.desc}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {selectedModels.length > 0 && (
                <div className="rounded-2xl border border-sigma-800/60 bg-sigma-950/30 p-4 mb-6">
                  <div className="text-sm font-medium text-white mb-3">Fine-tune selected models</div>
                  <div className="space-y-4">
                    {selectedModels.map(modelName => (
                      <div key={modelName} className="rounded-xl border border-sigma-800/60 bg-sigma-950/20 p-4">
                        <div className="text-sm font-medium text-white mb-3">{modelName}</div>
                        <div className="grid md:grid-cols-3 gap-3">
                          {(TUNING_FIELDS[modelName] || []).map(field => (
                            <div key={`${modelName}-${field.key}`}>
                              <label className="text-xs text-sigma-400 mb-1 block">{field.label}</label>
                              <input
                                type="number"
                                step={field.step || "1"}
                                placeholder={field.placeholder}
                                value={tuningParams[modelName]?.[field.key] ?? ""}
                                onChange={e => updateTuning(modelName, field.key, e.target.value)}
                                className="w-full bg-sigma-900/50 border border-sigma-700/50 rounded-lg px-3 py-2 text-sm text-white placeholder-sigma-600 focus:outline-none focus:border-sigma-500"
                              />
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          <button onClick={startTraining} disabled={training || !selectedDataset || !targetColumn} className="btn-primary w-full justify-center disabled:opacity-50 disabled:cursor-not-allowed">
            {training ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {training ? "Training..." : `Start ${mode === "simple" ? "Recommended" : "Custom"} Training`}
          </button>
        </div>

        <div className="space-y-6">
          <div className="sigma-card">
            <h2 className="font-display font-semibold text-white mb-4">Planned Data Cleaning</h2>
            <div className="space-y-3">
              {(recommendation?.cleaning_preview || [
                "Select a dataset and target column to preview cleaning steps.",
              ]).map(step => (
                <div key={step} className="rounded-xl border border-sigma-800/50 bg-sigma-900/30 px-4 py-3 text-sm text-sigma-300">
                  {step}
                </div>
              ))}
            </div>
          </div>

          <div className="sigma-card">
            <h2 className="font-display font-semibold text-white mb-4">Available Model Families</h2>
            <div className="space-y-2">
              {visibleModels.map(model => (
                <div key={model.name} className="flex items-start gap-3 rounded-xl bg-sigma-900/30 p-3">
                  <CheckCircle className="w-4 h-4 mt-0.5 text-sigma-400" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-white font-medium">{model.name}</span>
                      <span className="metric-badge text-sigma-500">{model.tag}</span>
                    </div>
                    <div className="text-xs text-sigma-500 mt-1">{model.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {currentJob && (
        <div className="sigma-card mt-6">
          <h2 className="font-display font-semibold text-white mb-4 flex items-center gap-2">
            {currentJob.status === "completed" ? (
              <CheckCircle className="w-4 h-4 text-sigma-400" />
            ) : currentJob.status === "failed" ? (
              <AlertTriangle className="w-4 h-4 text-sigma-500" />
            ) : (
              <Loader2 className="w-4 h-4 text-sigma-400 animate-spin" />
            )}
            Job: <span className="font-mono text-sigma-400">{currentJob.job_id.slice(0, 8)}...</span>
          </h2>

          <div className="mb-4">
            <div className="flex justify-between text-xs text-sigma-500 mb-1.5">
              <span className="capitalize">{currentJob.status}</span>
              <span>{progressBar}%</span>
            </div>
            <div className="h-2 bg-sigma-900 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-sigma-600 to-sigma-500 rounded-full transition-all duration-500" style={{ width: `${progressBar}%` }} />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-sigma-900/40">
              <div className="text-sigma-500">Task</div>
              <div className="text-white font-medium">{currentJob.task_type || "detecting..."}</div>
            </div>
            <div className="p-3 rounded-xl bg-sigma-900/40">
              <div className="text-sigma-500">Target</div>
              <div className="text-white font-medium">{currentJob.target_column}</div>
            </div>
            <div className="p-3 rounded-xl bg-sigma-900/40">
              <div className="text-sigma-500">Mode</div>
              <div className="text-white font-medium capitalize">{mode}</div>
            </div>
          </div>

          {currentJob.status === "completed" && (
            <Link href={`/dashboard/models?job=${currentJob.job_id}`} className="btn-primary mt-4 inline-flex">
              View Results <ChevronRight className="w-4 h-4" />
            </Link>
          )}

          {currentJob.error_message && (
            <div className="mt-3 p-3 rounded-xl bg-sigma-500/12 border border-sigma-500/25 text-sigma-400 text-xs font-mono">
              {currentJob.error_message}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
