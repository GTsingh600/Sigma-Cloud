"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import toast from "react-hot-toast";
import {
  BarChart,
  Bar,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  BarChart3,
  Download,
  Loader2,
  Rocket,
  Trophy,
  WandSparkles,
} from "lucide-react";

import { metricsAPI, modelsAPI, trainingAPI } from "@/lib/api";
import { MetricsData, TrainedModel } from "@/types";

const COLORS = ["#81A6C6", "#AACDDC", "#F3E3D0", "#D2C4B4", "#97B7D0", "#E6D8C7"];

function cardClass(active = false) {
  return `sigma-card ${active ? "border-sigma-500/50 shadow-[0_16px_44px_-28px_rgba(129,166,198,0.35)]" : ""}`;
}

export default function ModelsPage() {
  const searchParams = useSearchParams();
  const [jobId, setJobId] = useState(searchParams.get("job") || "");
  const [jobs, setJobs] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [selectedModel, setSelectedModel] = useState<TrainedModel | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    trainingAPI.listJobs()
      .then(r => {
        const completed = r.data.filter((job: any) => job.status === "completed");
        setJobs(completed);
        if (!jobId && completed.length > 0) setJobId(completed[0].job_id);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!jobId) return;
    setLoading(true);
    metricsAPI.getJobMetrics(jobId)
      .then(r => {
        setMetrics(r.data);
        setSelectedModel(r.data.best_model || null);
      })
      .catch(() => toast.error("Could not load metrics"))
      .finally(() => setLoading(false));
  }, [jobId]);

  const deployModel = async (modelId: number) => {
    try {
      await modelsAPI.deploy(modelId);
      toast.success("Model deployed");
      if (jobId) {
        const refreshed = await metricsAPI.getJobMetrics(jobId);
        setMetrics(refreshed.data);
        if (selectedModel) {
          const nextSelected = refreshed.data.models.find((model: TrainedModel) => model.id === selectedModel.id);
          setSelectedModel(nextSelected || refreshed.data.best_model || null);
        }
      }
    } catch {
      toast.error("Deploy failed");
    }
  };

  const isClassification = metrics?.task_type === "classification";

  const comparisonData = metrics?.models.map(model => ({
    name: model.model_name,
    Accuracy: model.accuracy ? +(model.accuracy * 100).toFixed(1) : undefined,
    F1: model.f1_score ? +(model.f1_score * 100).toFixed(1) : undefined,
    AUC: model.roc_auc ? +(model.roc_auc * 100).toFixed(1) : undefined,
    "R2": model.r2_score ? +(model.r2_score * 100).toFixed(1) : undefined,
    RMSE: model.rmse ? +model.rmse.toFixed(2) : undefined,
  })) || [];

  const featureImportanceData = selectedModel?.feature_importance
    ? Object.entries(selectedModel.feature_importance)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
        .map(([name, value]) => ({ name, value: +(value * 100).toFixed(1) }))
    : [];

  const cvData = selectedModel?.cv_scores?.map((score, index) => ({
    fold: `Fold ${index + 1}`,
    score: +(score * 100).toFixed(2),
  })) || [];

  const stabilityData = metrics?.models.map(model => ({
    name: model.model_name,
    cvStd: model.cv_std ? +(model.cv_std * 100).toFixed(2) : 0,
  })) || [];

  const radarData = useMemo(() => {
    if (!selectedModel) return [];
    if (isClassification) {
      return [
        { metric: "Accuracy", value: selectedModel.accuracy ? selectedModel.accuracy * 100 : 0 },
        { metric: "F1", value: selectedModel.f1_score ? selectedModel.f1_score * 100 : 0 },
        { metric: "AUC", value: selectedModel.roc_auc ? selectedModel.roc_auc * 100 : 0 },
        { metric: "CV Mean", value: selectedModel.cv_mean ? selectedModel.cv_mean * 100 : 0 },
      ];
    }
    return [
      { metric: "R2", value: selectedModel.r2_score ? Math.max(selectedModel.r2_score, 0) * 100 : 0 },
      { metric: "CV Mean", value: selectedModel.cv_mean ? Math.max(selectedModel.cv_mean, 0) * 100 : 0 },
      { metric: "Low RMSE", value: selectedModel.rmse ? Math.max(0, 100 - selectedModel.rmse * 10) : 0 },
      { metric: "Low MAE", value: selectedModel.mae ? Math.max(0, 100 - selectedModel.mae * 10) : 0 },
    ];
  }, [selectedModel, isClassification]);

  const residualData = useMemo(() => {
    const residuals = selectedModel?.metrics?.residuals as { predicted?: number[]; actual?: number[] } | undefined;
    if (!residuals?.predicted || !residuals?.actual) return [];
    return residuals.predicted.map((predicted, index) => ({
      predicted,
      actual: residuals.actual?.[index],
    })).slice(0, 120);
  }, [selectedModel]);

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-white mb-1">Model Leaderboard</h1>
        <p className="text-sigma-500">Compare tuned models, inspect training choices, and understand which model won and why.</p>
      </div>

      <div className="sigma-card mb-6">
        <div className="flex items-center gap-4">
          <label className="text-sm text-sigma-400 whitespace-nowrap">Training Job</label>
          <select
            value={jobId}
            onChange={e => setJobId(e.target.value)}
            className="flex-1 bg-sigma-900/50 border border-sigma-700/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sigma-500"
          >
            <option value="">Select a completed job...</option>
            {jobs.map(job => (
              <option key={job.job_id} value={job.job_id}>
                {job.job_id.slice(0, 8)}... - {job.target_column} ({job.task_type})
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 text-sigma-400 animate-spin" />
        </div>
      )}

      {metrics && !loading && (
        <>
          <div className="grid xl:grid-cols-[1.2fr_0.8fr] gap-6 mb-6">
            <div className={cardClass(true)}>
              {metrics.best_model && (
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-sigma-600/15 flex items-center justify-center">
                    <Trophy className="w-6 h-6 text-[#F3E3D0]" />
                  </div>
                  <div className="flex-1">
                    <div className="text-xs uppercase tracking-[0.18em] text-sigma-500 mb-1">Best model</div>
                    <div className="font-display text-2xl font-bold text-white">{metrics.best_model.model_name}</div>
                    <div className="text-sm text-sigma-400 mt-1">
                      {metrics.training_mode || "simple"} mode · {metrics.task_type}
                    </div>
                    <div className="flex flex-wrap gap-2 mt-4">
                      {metrics.best_model.accuracy !== undefined && (
                        <span className="metric-badge text-white">Accuracy {(metrics.best_model.accuracy * 100).toFixed(1)}%</span>
                      )}
                      {metrics.best_model.f1_score !== undefined && (
                        <span className="metric-badge text-white">F1 {(metrics.best_model.f1_score * 100).toFixed(1)}%</span>
                      )}
                      {metrics.best_model.roc_auc !== undefined && (
                        <span className="metric-badge text-white">AUC {(metrics.best_model.roc_auc * 100).toFixed(1)}%</span>
                      )}
                      {metrics.best_model.r2_score !== undefined && (
                        <span className="metric-badge text-white">R2 {metrics.best_model.r2_score.toFixed(3)}</span>
                      )}
                      {metrics.best_model.rmse !== undefined && (
                        <span className="metric-badge text-white">RMSE {metrics.best_model.rmse.toFixed(3)}</span>
                      )}
                    </div>
                  </div>
                  <button onClick={() => deployModel(metrics.best_model!.id)} className="btn-primary">
                    <Rocket className="w-4 h-4" /> Deploy
                  </button>
                </div>
              )}
            </div>

            <div className="sigma-card">
              <div className="flex items-center gap-2 text-sm font-medium text-white mb-3">
                <WandSparkles className="w-4 h-4 text-sigma-400" />
                Training recipe
              </div>
              <div className="text-xs uppercase tracking-[0.16em] text-sigma-500 mb-2">Recommended models</div>
              <div className="flex flex-wrap gap-2 mb-4">
                {(metrics.recommended_models || []).map(model => (
                  <span key={model} className="metric-badge text-sigma-200">{model}</span>
                ))}
              </div>
              <div className="text-xs uppercase tracking-[0.16em] text-sigma-500 mb-2">Data cleaning steps</div>
              <div className="space-y-2">
                {(metrics.cleaning_steps || []).map(step => (
                  <div key={step} className="rounded-xl border border-sigma-800/50 bg-sigma-900/20 px-3 py-2 text-sm text-sigma-300">
                    {step}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
            {metrics.models.map(model => (
              <div
                key={model.id}
                onClick={() => setSelectedModel(model)}
                className={cardClass(selectedModel?.id === model.id)}
              >
                <div className="flex items-center justify-between gap-3 mb-3">
                  <div className="font-semibold text-white text-sm">{model.model_name}</div>
                  {metrics.best_model?.id === model.id && <Trophy className="w-4 h-4 text-[#F3E3D0]" />}
                </div>
                <div className="space-y-1.5 text-xs">
                  {model.accuracy !== undefined && <div className="flex justify-between"><span className="text-sigma-500">Accuracy</span><span className="text-white font-mono">{(model.accuracy * 100).toFixed(1)}%</span></div>}
                  {model.f1_score !== undefined && <div className="flex justify-between"><span className="text-sigma-500">F1</span><span className="text-white font-mono">{(model.f1_score * 100).toFixed(1)}%</span></div>}
                  {model.roc_auc !== undefined && <div className="flex justify-between"><span className="text-sigma-500">AUC</span><span className="text-white font-mono">{(model.roc_auc * 100).toFixed(1)}%</span></div>}
                  {model.r2_score !== undefined && <div className="flex justify-between"><span className="text-sigma-500">R2</span><span className="text-white font-mono">{model.r2_score.toFixed(3)}</span></div>}
                  {model.rmse !== undefined && <div className="flex justify-between"><span className="text-sigma-500">RMSE</span><span className="text-white font-mono">{model.rmse.toFixed(3)}</span></div>}
                  <div className="flex justify-between"><span className="text-sigma-500">Train time</span><span className="text-white font-mono">{model.training_time?.toFixed(2)}s</span></div>
                </div>
                <div className="flex gap-2 mt-4">
                  <button onClick={e => { e.stopPropagation(); deployModel(model.id); }} className="btn-outline text-xs py-1.5 justify-center flex-1">
                    <Rocket className="w-3 h-3" /> Deploy
                  </button>
                  <a href={modelsAPI.download(model.id)} download className="btn-outline text-xs py-1.5 px-2.5" onClick={e => e.stopPropagation()}>
                    <Download className="w-3 h-3" />
                  </a>
                </div>
              </div>
            ))}
          </div>

          <div className="grid xl:grid-cols-2 gap-6 mb-6">
            <div className="sigma-card">
              <h3 className="font-display font-semibold text-white mb-4">Primary Metric Comparison</h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={comparisonData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(170,205,220,0.12)" />
                  <XAxis dataKey="name" tick={{ fill: "#d2c4b4", fontSize: 10 }} />
                  <YAxis tick={{ fill: "#d2c4b4", fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: "#24313c", border: "1px solid rgba(170,205,220,0.24)", borderRadius: "12px", color: "#f8f4ef" }} />
                  {isClassification ? (
                    <>
                      <Bar dataKey="Accuracy" fill={COLORS[0]} radius={[4, 4, 0, 0]} />
                      <Bar dataKey="F1" fill={COLORS[1]} radius={[4, 4, 0, 0]} />
                      <Bar dataKey="AUC" fill={COLORS[2]} radius={[4, 4, 0, 0]} />
                    </>
                  ) : (
                    <>
                      <Bar dataKey="R2" fill={COLORS[0]} radius={[4, 4, 0, 0]} />
                      <Bar dataKey="RMSE" fill={COLORS[1]} radius={[4, 4, 0, 0]} />
                    </>
                  )}
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="sigma-card">
              <h3 className="font-display font-semibold text-white mb-4">Performance vs Training Time</h3>
              <ResponsiveContainer width="100%" height={260}>
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(170,205,220,0.12)" />
                  <XAxis type="number" dataKey="training_time" name="Training Time" unit="s" tick={{ fill: "#d2c4b4", fontSize: 10 }} />
                  <YAxis type="number" dataKey="primary_metric" name="Primary Metric" tick={{ fill: "#d2c4b4", fontSize: 10 }} />
                  <Tooltip cursor={{ strokeDasharray: "3 3" }} contentStyle={{ background: "#24313c", border: "1px solid rgba(170,205,220,0.24)", borderRadius: "12px", color: "#f8f4ef" }} />
                  <Scatter data={metrics.performance_scatter || []} fill={COLORS[0]} />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid xl:grid-cols-2 gap-6 mb-6">
            <div className="sigma-card">
              <h3 className="font-display font-semibold text-white mb-4">CV Stability</h3>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={stabilityData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(170,205,220,0.12)" horizontal={false} />
                  <XAxis type="number" tick={{ fill: "#d2c4b4", fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" width={120} tick={{ fill: "#d2c4b4", fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: "#24313c", border: "1px solid rgba(170,205,220,0.24)", borderRadius: "12px", color: "#f8f4ef" }} />
                  <Bar dataKey="cvStd" fill={COLORS[1]} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="sigma-card">
              <h3 className="font-display font-semibold text-white mb-4">Selected Model Profile</h3>
              <ResponsiveContainer width="100%" height={240}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="rgba(170,205,220,0.12)" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: "#d2c4b4", fontSize: 11 }} />
                  <Radar name={selectedModel?.model_name || "Model"} dataKey="value" stroke={COLORS[0]} fill={COLORS[0]} fillOpacity={0.25} />
                  <Tooltip contentStyle={{ background: "#24313c", border: "1px solid rgba(170,205,220,0.24)", borderRadius: "12px", color: "#f8f4ef" }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid xl:grid-cols-2 gap-6">
            {cvData.length > 0 && (
              <div className="sigma-card">
                <h3 className="font-display font-semibold text-white mb-4">Cross-Validation Scores</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={cvData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(170,205,220,0.12)" />
                    <XAxis dataKey="fold" tick={{ fill: "#d2c4b4", fontSize: 10 }} />
                    <YAxis tick={{ fill: "#d2c4b4", fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: "#24313c", border: "1px solid rgba(170,205,220,0.24)", borderRadius: "12px", color: "#f8f4ef" }} />
                    <Line type="monotone" dataKey="score" stroke={COLORS[0]} strokeWidth={2.5} dot={{ fill: COLORS[2] }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {featureImportanceData.length > 0 && (
              <div className="sigma-card">
                <h3 className="font-display font-semibold text-white mb-4">Feature Importance</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={featureImportanceData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(170,205,220,0.12)" horizontal={false} />
                    <XAxis type="number" tick={{ fill: "#d2c4b4", fontSize: 10 }} unit="%" />
                    <YAxis type="category" dataKey="name" width={130} tick={{ fill: "#d2c4b4", fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: "#24313c", border: "1px solid rgba(170,205,220,0.24)", borderRadius: "12px", color: "#f8f4ef" }} />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                      {featureImportanceData.map((_, index) => (
                        <Cell key={index} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {residualData.length > 0 && (
            <div className="sigma-card mt-6">
              <h3 className="font-display font-semibold text-white mb-4">Predicted vs Actual</h3>
              <ResponsiveContainer width="100%" height={280}>
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(170,205,220,0.12)" />
                  <XAxis type="number" dataKey="predicted" tick={{ fill: "#d2c4b4", fontSize: 10 }} />
                  <YAxis type="number" dataKey="actual" tick={{ fill: "#d2c4b4", fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: "#24313c", border: "1px solid rgba(170,205,220,0.24)", borderRadius: "12px", color: "#f8f4ef" }} />
                  <Scatter data={residualData} fill={COLORS[1]} />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {!metrics && !loading && (
        <div className="text-center py-20 text-sigma-600">
          <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>Select a completed training job to view metrics.</p>
        </div>
      )}
    </div>
  );
}
