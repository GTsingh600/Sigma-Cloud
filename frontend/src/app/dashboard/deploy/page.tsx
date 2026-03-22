"use client";
import { useState, useEffect } from "react";
import { modelsAPI } from "@/lib/api";
import toast from "react-hot-toast";
import { Rocket, Download, CheckCircle, XCircle, Trash2, Loader2, Shield } from "lucide-react";

export default function DeployPage() {
  const [allModels, setAllModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchModels = async () => {
    try {
      const res = await modelsAPI.list();
      setAllModels(res.data);
    } catch {
      toast.error("Could not load models");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const deploy = async (id: number) => {
    try {
      await modelsAPI.deploy(id);
      toast.success("Model deployed!");
      fetchModels();
    } catch {
      toast.error("Deploy failed");
    }
  };

  const undeploy = async (id: number) => {
    try {
      await modelsAPI.undeploy(id);
      toast.success("Model undeployed");
      fetchModels();
    } catch {
      toast.error("Failed");
    }
  };

  const deleteModel = async (id: number) => {
    if (!confirm("Delete this model?")) return;
    try {
      await modelsAPI.delete(id);
      toast.success("Deleted");
      fetchModels();
    } catch {
      toast.error("Delete failed");
    }
  };

  const deployedModels = allModels.filter((m) => m.is_deployed);

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-white mb-1">Model Deployment</h1>
        <p className="text-sigma-500">Deploy models to serve predictions via the REST API.</p>
      </div>

      <div className="sigma-card mb-6">
        <h2 className="font-display font-semibold text-white mb-3 flex items-center gap-2">
          <Rocket className="w-4 h-4 text-sigma-300" /> Currently Deployed
        </h2>
        {deployedModels.length === 0 ? (
          <p className="text-sigma-500 text-sm">No models deployed. Deploy one below to serve predictions.</p>
        ) : (
          <div className="flex flex-wrap gap-3">
            {deployedModels.map((m) => (
              <div key={m.id} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-sigma-300/10 border border-sigma-300/20">
                <CheckCircle className="w-4 h-4 text-sigma-300" />
                <span className="text-sm text-white font-medium">{m.model_name}</span>
                <span className="text-xs text-sigma-400 font-mono">{m.task_type}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="sigma-card mb-6 border-sigma-600/30">
        <h2 className="font-display font-semibold text-white mb-3 flex items-center gap-2">
          <Shield className="w-4 h-4 text-sigma-400" /> Prediction API
        </h2>
        <p className="text-sigma-500 text-sm mb-3">Once deployed, call the prediction endpoint:</p>
        <div className="bg-sigma-900/50 rounded-lg p-4 font-mono text-sm">
          <div className="text-sigma-300">POST</div>
          <div className="text-sigma-300">/api/predict</div>
          <div className="text-sigma-500 mt-2">{"{"}</div>
          <div className="text-sigma-300 ml-4">  "model_id": 1,</div>
          <div className="text-sigma-300 ml-4">  "features": {"{"}"feature1": value, ...{"}"}</div>
          <div className="text-sigma-500">{"}"}</div>
        </div>
      </div>

      <div className="sigma-card">
        <h2 className="font-display font-semibold text-white mb-4">All Trained Models</h2>
        {loading ? (
          <div className="flex justify-center py-10">
            <Loader2 className="w-6 h-6 text-sigma-400 animate-spin" />
          </div>
        ) : allModels.length === 0 ? (
          <div className="text-center py-12 text-sigma-600 text-sm">No models yet. Start training from the Training page.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-sigma-800/50 text-left text-sigma-500 text-xs uppercase">
                  <th className="pb-3 font-medium">Model</th>
                  <th className="pb-3 font-medium">Type</th>
                  <th className="pb-3 font-medium">Task</th>
                  <th className="pb-3 font-medium">Primary Metric</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {allModels.map((m) => {
                  const primary = m.task_type === "classification"
                    ? m.accuracy ? `Acc ${(m.accuracy * 100).toFixed(1)}%` : "-"
                    : m.r2_score ? `R2 ${m.r2_score.toFixed(3)}` : "-";
                  return (
                    <tr key={m.id} className="border-b border-sigma-900/40 hover:bg-sigma-900/20">
                      <td className="py-3 font-medium text-white">{m.model_name}</td>
                      <td className="py-3 text-sigma-400 text-xs">{m.model_type}</td>
                      <td className="py-3">
                        <span className={`metric-badge ${m.task_type === "classification" ? "bg-sigma-500/12 text-sigma-500" : "bg-sigma-400/12 text-sigma-400"}`}>
                          {m.task_type}
                        </span>
                      </td>
                      <td className="py-3 font-mono text-xs text-sigma-300">{primary}</td>
                      <td className="py-3">
                        {m.is_deployed ? (
                          <span className="metric-badge bg-sigma-300/12 text-sigma-300 flex items-center gap-1 w-fit">
                            <CheckCircle className="w-3 h-3" /> deployed
                          </span>
                        ) : (
                          <span className="metric-badge bg-sigma-800/40 text-sigma-500">idle</span>
                        )}
                      </td>
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          {m.is_deployed ? (
                            <button onClick={() => undeploy(m.id)} className="btn-outline text-xs py-1 px-2.5 border-sigma-500/40 text-sigma-500 hover:border-sigma-400">
                              <XCircle className="w-3 h-3" /> Undeploy
                            </button>
                          ) : (
                            <button onClick={() => deploy(m.id)} className="btn-primary text-xs py-1 px-2.5">
                              <Rocket className="w-3 h-3" /> Deploy
                            </button>
                          )}
                          <a href={modelsAPI.download(m.id)} download className="p-1.5 rounded hover:bg-sigma-800 text-sigma-500 hover:text-sigma-300 transition-colors">
                            <Download className="w-3.5 h-3.5" />
                          </a>
                          <button onClick={() => deleteModel(m.id)} className="p-1.5 rounded hover:bg-sigma-500/10 text-sigma-500 hover:text-sigma-400 transition-colors">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
