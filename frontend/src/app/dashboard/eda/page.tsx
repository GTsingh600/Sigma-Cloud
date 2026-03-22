"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { datasetsAPI } from "@/lib/api";
import { Dataset, DatasetAnalysis } from "@/types";
import { DatasetAnalysisPanel } from "@/components/datasets/DatasetAnalysisPanel";
import { BarChart3, Database, Loader2 } from "lucide-react";
import toast from "react-hot-toast";

export default function EdaPage() {
  const searchParams = useSearchParams();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedId, setSelectedId] = useState(searchParams.get("dataset") || "");
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [analysis, setAnalysis] = useState<DatasetAnalysis | null>(null);
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);

  useEffect(() => {
    datasetsAPI.list()
      .then((r) => {
        setDatasets(r.data);
        if (!selectedId && r.data.length > 0) {
          setSelectedId(String(r.data[0].id));
        }
      })
      .catch(() => toast.error("Could not load datasets"))
      .finally(() => setLoadingDatasets(false));
  }, []);

  useEffect(() => {
    const dataset = datasets.find((item) => String(item.id) === selectedId) || null;
    setSelectedDataset(dataset);
  }, [datasets, selectedId]);

  useEffect(() => {
    if (!selectedId) {
      setAnalysis(null);
      return;
    }
    setLoadingAnalysis(true);
    datasetsAPI.getAnalysis(Number(selectedId))
      .then((r) => setAnalysis(r.data))
      .catch(() => {
        setAnalysis(null);
        toast.error("Could not generate dataset analysis");
      })
      .finally(() => setLoadingAnalysis(false));
  }, [selectedId]);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-white mb-1">EDA & Data Visualization</h1>
        <p className="text-sigma-500">
          Explore dataset-specific visuals chosen for signal, imbalance, structure, and modeling relevance.
        </p>
      </div>

      <div className="sigma-card mb-6">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
          <div>
            <label className="mb-1.5 block text-xs text-sigma-400">Dataset</label>
            <select
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              className="w-full rounded-lg border border-sigma-700/50 bg-sigma-900/50 px-3 py-2 text-sm text-white focus:border-sigma-500 focus:outline-none"
            >
              <option value="">Select dataset...</option>
              {datasets.map((dataset) => (
                <option key={dataset.id} value={dataset.id}>
                  {dataset.name} ({dataset.num_rows?.toLocaleString()} rows)
                </option>
              ))}
            </select>
          </div>
          {selectedDataset && (
            <div className="rounded-xl border border-sigma-800/50 bg-sigma-950/30 px-4 py-3 text-sm text-sigma-400">
              {selectedDataset.task_type ? `task: ${selectedDataset.task_type}` : "task: pending detection"}
              {selectedDataset.target_column ? ` • target: ${selectedDataset.target_column}` : " • no target selected"}
            </div>
          )}
        </div>
      </div>

      {loadingDatasets && (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-sigma-400" />
        </div>
      )}

      {!loadingDatasets && !selectedDataset && (
        <div className="sigma-card py-16 text-center text-sigma-500">
          <Database className="mx-auto mb-3 h-12 w-12 opacity-30" />
          <p>Select a dataset to open the EDA workspace.</p>
        </div>
      )}

      {selectedDataset && (
        <>
          <div className="sigma-card">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-sigma-700/30">
                <BarChart3 className="h-6 w-6 text-sigma-300" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-display text-xl font-semibold text-white">{selectedDataset.name}</div>
                <div className="mt-1 text-sm text-sigma-500">
                  {selectedDataset.num_rows?.toLocaleString() || "?"} rows • {selectedDataset.num_columns || "?"} columns
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {selectedDataset.is_example && (
                    <span className="metric-badge bg-sigma-800/60 text-sigma-400">example dataset</span>
                  )}
                  {selectedDataset.task_type && (
                    <span className={`metric-badge ${selectedDataset.task_type === "classification" ? "bg-sigma-500/12 text-sigma-500" : "bg-sigma-400/12 text-sigma-400"}`}>
                      {selectedDataset.task_type}
                    </span>
                  )}
                  {selectedDataset.target_column && (
                    <span className="metric-badge bg-sigma-800/60 text-sigma-300">target: {selectedDataset.target_column}</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <DatasetAnalysisPanel analysis={analysis} loading={loadingAnalysis} />
        </>
      )}
    </div>
  );
}
