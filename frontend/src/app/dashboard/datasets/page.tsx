"use client";
import { useState, useCallback, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { datasetsAPI } from "@/lib/api";
import { logToFile } from "@/lib/logger";
import { Dataset, ExampleDataset } from "@/types";
import Link from "next/link";
import toast from "react-hot-toast";
import {
  Upload, Database, Trash2, Table, Info,
  CloudUpload, FileSpreadsheet, Loader2, Sparkles
} from "lucide-react";

function formatBytes(bytes?: number) {
  if (!bytes) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

export default function DatasetsPage() {
  const maxUploadSize = 100 * 1024 * 1024;
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [examples, setExamples] = useState<ExampleDataset[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loadingExample, setLoadingExample] = useState<string | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [targetColumn, setTargetColumn] = useState("");

  const fetchDatasets = async () => {
    try {
      const res = await datasetsAPI.list();
      setDatasets(res.data);
    } catch (e: any) {
      toast.error("Could not connect to backend");
      logToFile(`Backend not connected when fetching datasets: ${e?.message || e}`, "error");
    }
  };

  useEffect(() => {
    fetchDatasets();
    datasetsAPI.listExamples().then((r) => setExamples(r.data)).catch(() => {});
  }, []);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("name", file.name.replace(/\.[^/.]+$/, ""));
    if (targetColumn) formData.append("target_column", targetColumn);
    logToFile(`Upload attempt: ${file.name} (target_column=${targetColumn})`, "info");
    try {
      await datasetsAPI.upload(formData);
      toast.success(`"${file.name}" uploaded successfully`);
      logToFile(`Upload success: ${file.name}`, "info");
      fetchDatasets();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Upload failed");
      logToFile(`Upload failed: ${file.name} | ${e?.message || e}`, "error");
    } finally {
      setUploading(false);
    }
  }, [targetColumn]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"] },
    maxFiles: 1,
    maxSize: maxUploadSize,
  });

  const loadExample = async (key: string) => {
    setLoadingExample(key);
    try {
      await datasetsAPI.loadExample(key);
      toast.success("Example dataset loaded!");
      fetchDatasets();
    } catch {
      toast.error("Failed to load example");
    } finally {
      setLoadingExample(null);
    }
  };

  const deleteDataset = async (id: number) => {
    if (!confirm("Delete this dataset?")) return;
    try {
      await datasetsAPI.delete(id);
      toast.success("Dataset deleted");
      fetchDatasets();
      if (selectedDataset?.id === id) {
        setSelectedDataset(null);
      }
    } catch {
      toast.error("Delete failed");
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-white mb-1">Datasets</h1>
        <p className="text-sigma-500">Upload your data or load a built-in example dataset to get started.</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="sigma-card">
          <h2 className="font-display font-semibold text-white mb-4 flex items-center gap-2">
            <CloudUpload className="w-4 h-4 text-sigma-400" /> Upload Dataset
          </h2>

          <div className="mb-4">
            <label className="text-xs text-sigma-400 mb-1 block">Target Column (optional)</label>
            <input
              value={targetColumn}
              onChange={(e) => setTargetColumn(e.target.value)}
              placeholder="e.g. price, survived, label"
              className="w-full bg-sigma-900/50 border border-sigma-700/50 rounded-lg px-3 py-2 text-sm text-white placeholder-sigma-600 focus:outline-none focus:border-sigma-500"
            />
          </div>

          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
              isDragActive
                ? "border-sigma-500 bg-sigma-800/30"
                : "border-sigma-700/50 hover:border-sigma-600 hover:bg-sigma-900/30"
            }`}
          >
            <input {...getInputProps()} />
            {uploading ? (
              <Loader2 className="w-8 h-8 text-sigma-400 mx-auto mb-3 animate-spin" />
            ) : (
              <Upload className={`w-8 h-8 mx-auto mb-3 ${isDragActive ? "text-sigma-400" : "text-sigma-600"}`} />
            )}
            <p className="text-sm text-sigma-400 mb-1">
              {uploading ? "Uploading..." : isDragActive ? "Drop it here." : "Drag and drop your CSV or Excel file"}
            </p>
            <p className="text-xs text-sigma-600">or click to browse | Max 100MB</p>
          </div>
        </div>

        <div className="sigma-card">
          <h2 className="font-display font-semibold text-white mb-4 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-sigma-400" /> Example Datasets
          </h2>
          <div className="space-y-3">
            {examples.map((ex) => (
              <div key={ex.key} className="flex items-center gap-3 p-3 rounded-lg bg-sigma-900/30 border border-sigma-800/40 hover:border-sigma-700/50 transition-colors">
                <FileSpreadsheet className="w-8 h-8 text-sigma-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-white">{ex.name}</div>
                  <div className="text-xs text-sigma-500 truncate">{ex.description}</div>
                  <div className="flex gap-2 mt-1">
                    <span className="metric-badge bg-sigma-800/60 text-sigma-400">{ex.task_type}</span>
                    <span className="metric-badge bg-sigma-800/60 text-sigma-400">target: {ex.target}</span>
                  </div>
                </div>
                <button onClick={() => loadExample(ex.key)} disabled={loadingExample === ex.key} className="btn-outline text-xs py-1.5 px-3 flex-shrink-0">
                  {loadingExample === ex.key ? <Loader2 className="w-3 h-3 animate-spin" /> : "Load"}
                </button>
              </div>
            ))}
            {examples.length === 0 && <div className="text-center py-6 text-sigma-600 text-sm">Loading examples...</div>}
          </div>
        </div>
      </div>

      <div className="sigma-card mt-6">
        <h2 className="font-display font-semibold text-white mb-4 flex items-center gap-2">
          <Database className="w-4 h-4 text-sigma-400" /> Your Datasets ({datasets.length})
        </h2>
        {datasets.length === 0 ? (
          <div className="text-center py-12 text-sigma-600">
            <Database className="w-10 h-10 mx-auto mb-3 opacity-30" />
            <p className="text-sm">No datasets yet. Upload one or load an example.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-sigma-800/50 text-left text-sigma-500 text-xs uppercase">
                  <th className="pb-3 font-medium">Name</th>
                  <th className="pb-3 font-medium">Rows</th>
                  <th className="pb-3 font-medium">Columns</th>
                  <th className="pb-3 font-medium">Size</th>
                  <th className="pb-3 font-medium">Target</th>
                  <th className="pb-3 font-medium">Task</th>
                  <th className="pb-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((ds) => (
                  <tr key={ds.id} className="border-b border-sigma-900/50 hover:bg-sigma-900/20">
                    <td className="py-3 font-medium text-white">
                      {ds.is_example && <span className="metric-badge bg-sigma-800/60 text-sigma-400 mr-2">example</span>}
                      {ds.name}
                    </td>
                    <td className="py-3 text-sigma-400">{ds.num_rows?.toLocaleString()}</td>
                    <td className="py-3 text-sigma-400">{ds.num_columns}</td>
                    <td className="py-3 text-sigma-400">{formatBytes(ds.file_size)}</td>
                    <td className="py-3 font-mono text-xs text-sigma-300">{ds.target_column || "-"}</td>
                    <td className="py-3">
                      {ds.task_type ? (
                        <span className={`metric-badge ${ds.task_type === "classification" ? "bg-sigma-500/12 text-sigma-500" : "bg-sigma-400/12 text-sigma-400"}`}>
                          {ds.task_type}
                        </span>
                      ) : "-"}
                    </td>
                    <td className="py-3">
                      <div className="flex gap-2">
                        <button onClick={() => setSelectedDataset(selectedDataset?.id === ds.id ? null : ds)} className="p-1.5 rounded hover:bg-sigma-800 text-sigma-500 hover:text-sigma-300 transition-colors">
                          <Table className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => deleteDataset(ds.id)} className="p-1.5 rounded hover:bg-sigma-500/10 text-sigma-500 hover:text-sigma-400 transition-colors">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedDataset && (
        <div className="sigma-card mt-6">
          <h2 className="font-display font-semibold text-white mb-4 flex items-center gap-2">
            <Info className="w-4 h-4 text-sigma-400" /> Preview: {selectedDataset.name}
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-sigma-800/50 text-left text-sigma-500">
                  {selectedDataset.columns_info?.map((c) => (
                    <th key={c.name} className="pb-2 pr-4 font-medium whitespace-nowrap">{c.name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {selectedDataset.preview_data?.slice(0, 8).map((row, i) => (
                  <tr key={i} className="border-b border-sigma-900/30 hover:bg-sigma-900/20">
                    {selectedDataset.columns_info?.map((c) => (
                      <td key={c.name} className="py-1.5 pr-4 text-sigma-300 whitespace-nowrap max-w-[150px] truncate">
                        {String(row[c.name] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-5 flex items-center justify-between gap-4 rounded-xl border border-sigma-800/50 bg-sigma-950/30 p-4">
            <div>
              <div className="text-sm font-medium text-white">Open the full EDA workspace</div>
              <div className="mt-1 text-sm text-sigma-500">
                Use the dedicated data visualization page for richer charts, pairwise analysis, and target-aware EDA.
              </div>
            </div>
            <Link href={`/dashboard/eda?dataset=${selectedDataset.id}`} className="btn-primary whitespace-nowrap">
              Open EDA
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
