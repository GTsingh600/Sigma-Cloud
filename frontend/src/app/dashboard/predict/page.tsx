"use client";
import { useState, useEffect } from "react";
import { modelsAPI, predictionsAPI } from "@/lib/api";
import { PredictionResult } from "@/types";
import toast from "react-hot-toast";
import { Zap, Loader2, CheckCircle, BarChart2 } from "lucide-react";

export default function PredictPage() {
  const [deployedModels, setDeployedModels] = useState<any[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const [selectedModel, setSelectedModel] = useState<any>(null);
  const [features, setFeatures] = useState<Record<string, string>>({});
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [predicting, setPredicting] = useState(false);

  useEffect(() => {
    modelsAPI.listDeployed().then((r) => {
      setDeployedModels(r.data);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedModelId) return;
    modelsAPI.get(selectedModelId).then((r) => {
      setSelectedModel(r.data);
      const fi = r.data.feature_importance || {};
      const init: Record<string, string> = {};
      Object.keys(fi).forEach((k) => {
        init[k] = "";
      });
      setFeatures(init);
      setResult(null);
    }).catch(() => {});
  }, [selectedModelId]);

  const runPrediction = async () => {
    if (!selectedModelId) return toast.error("Select a model");
    const parsedFeatures: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(features)) {
      const num = Number(v);
      parsedFeatures[k] = Number.isNaN(num) || v === "" ? v || null : num;
    }
    setPredicting(true);
    try {
      const res = await predictionsAPI.predict(selectedModelId, parsedFeatures);
      setResult(res.data);
      toast.success("Prediction complete!");
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Prediction failed");
    } finally {
      setPredicting(false);
    }
  };

  const featureKeys = Object.keys(features);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-white mb-1">Run Prediction</h1>
        <p className="text-sigma-500">Use a deployed model to predict on new data.</p>
      </div>

      <div className="sigma-card mb-6">
        <h2 className="font-display font-semibold text-white mb-4 flex items-center gap-2">
          <Zap className="w-4 h-4 text-sigma-400" /> Select Model
        </h2>
        {deployedModels.length === 0 ? (
          <div className="text-sm text-sigma-500 bg-sigma-900/40 p-4 rounded-lg">
            No deployed models yet. Go to the <a href="/dashboard/models" className="text-sigma-400 underline">Leaderboard</a> and deploy a model first.
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
            {deployedModels.map((m) => (
              <button
                key={m.id}
                onClick={() => setSelectedModelId(m.id)}
                className={`p-3 rounded-lg border text-left transition-all ${
                  selectedModelId === m.id
                    ? "border-sigma-500/60 bg-sigma-800/40 text-white"
                    : "border-sigma-700/40 bg-sigma-900/30 text-sigma-400 hover:border-sigma-600"
                }`}
              >
                <div className="font-medium text-sm">{m.model_name}</div>
                <div className="text-xs text-sigma-500 mt-1">{m.task_type}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      {selectedModel && featureKeys.length > 0 && (
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="sigma-card">
            <h2 className="font-display font-semibold text-white mb-4">Input Features</h2>
            <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
              {featureKeys.map((feat) => (
                <div key={feat}>
                  <label className="text-xs text-sigma-400 mb-1 block font-mono">{feat}</label>
                  <input
                    value={features[feat]}
                    onChange={(e) => setFeatures((prev) => ({ ...prev, [feat]: e.target.value }))}
                    placeholder="Enter value..."
                    className="w-full bg-sigma-900/50 border border-sigma-700/50 rounded-lg px-3 py-2 text-sm text-white placeholder-sigma-600 focus:outline-none focus:border-sigma-500 font-mono"
                  />
                </div>
              ))}
            </div>
            <button onClick={runPrediction} disabled={predicting} className="btn-primary w-full justify-center mt-5 disabled:opacity-50">
              {predicting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              {predicting ? "Predicting..." : "Run Prediction"}
            </button>
          </div>

          <div className="sigma-card">
            <h2 className="font-display font-semibold text-white mb-4 flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-sigma-400" /> Result
            </h2>
            {!result ? (
              <div className="text-center py-16 text-sigma-600">
                <Zap className="w-10 h-10 mx-auto mb-3 opacity-20" />
                <p className="text-sm">Fill features and click Predict</p>
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-3 mb-6">
                  <CheckCircle className="w-8 h-8 text-sigma-300" />
                  <div>
                    <div className="text-xs text-sigma-500">Prediction</div>
                    <div className="font-display text-2xl font-bold gradient-text">{String(result.prediction)}</div>
                  </div>
                </div>

                {result.confidence !== undefined && result.confidence !== null && (
                  <div className="mb-4">
                    <div className="flex justify-between text-xs text-sigma-500 mb-1.5">
                      <span>Confidence</span>
                      <span className="text-white font-mono">{(result.confidence * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-2 bg-sigma-900 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-sigma-400 to-sigma-300 rounded-full"
                        style={{ width: `${(result.confidence * 100).toFixed(0)}%` }}
                      />
                    </div>
                  </div>
                )}

                {result.probability && (
                  <div>
                    <div className="text-xs text-sigma-500 mb-2">Class Probabilities</div>
                    <div className="space-y-2">
                      {Object.entries(result.probability)
                        .sort((a, b) => b[1] - a[1])
                        .map(([cls, prob]) => (
                          <div key={cls}>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-sigma-300 font-mono">{cls}</span>
                              <span className="text-white font-mono">{(prob * 100).toFixed(1)}%</span>
                            </div>
                            <div className="h-1.5 bg-sigma-900 rounded-full overflow-hidden">
                              <div className="h-full bg-sigma-500 rounded-full transition-all" style={{ width: `${(prob * 100).toFixed(0)}%` }} />
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                <div className="mt-4 p-3 rounded bg-sigma-900/40 text-xs font-mono text-sigma-500">
                  Model: {result.model_name}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
