"use client";
import { useEffect, useState } from "react";
import { metricsAPI, trainingAPI } from "@/lib/api";
import { Database, BrainCircuit, Rocket, CheckCircle, Clock, AlertTriangle, TrendingUp } from "lucide-react";
import Link from "next/link";

interface Summary {
  total_datasets: number;
  total_models: number;
  deployed_models: number;
  completed_jobs: number;
  failed_jobs: number;
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [recentJobs, setRecentJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [summaryRes, jobsRes] = await Promise.all([
          metricsAPI.getDashboardSummary(),
          trainingAPI.listJobs(),
        ]);
        setSummary(summaryRes.data);
        setRecentJobs(jobsRes.data.slice(0, 5));
      } catch (e) {
        // backend may not be running
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const statCards = [
    { label: "Datasets", value: summary?.total_datasets ?? "-", icon: Database, color: "text-sigma-500", bg: "bg-sigma-500/12" },
    { label: "Trained Models", value: summary?.total_models ?? "-", icon: BrainCircuit, color: "text-sigma-400", bg: "bg-sigma-400/12" },
    { label: "Deployed", value: summary?.deployed_models ?? "-", icon: Rocket, color: "text-sigma-300", bg: "bg-sigma-300/12" },
    { label: "Completed Jobs", value: summary?.completed_jobs ?? "-", icon: CheckCircle, color: "text-sigma-400", bg: "bg-sigma-400/12" },
  ];

  const statusIcon = (status: string) => {
    if (status === "completed") return <CheckCircle className="w-4 h-4 text-sigma-300" />;
    if (status === "running") return <Clock className="w-4 h-4 text-sigma-400 animate-spin" />;
    if (status === "failed") return <AlertTriangle className="w-4 h-4 text-sigma-500" />;
    return <Clock className="w-4 h-4 text-sigma-500" />;
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-10">
        <h1 className="font-display text-4xl font-bold text-white mb-2">
          Welcome to <span className="gradient-text">SigmaCloud AI</span>
        </h1>
        <p className="text-sigma-500">Your AutoML platform. Train models, compare results, deploy predictions.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {statCards.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="sigma-card">
            <div className={`w-10 h-10 rounded-lg ${bg} flex items-center justify-center mb-4`}>
              <Icon className={`w-5 h-5 ${color}`} />
            </div>
            <div className="font-display text-3xl font-bold text-white mb-1">{loading ? "..." : value}</div>
            <div className="text-sigma-500 text-sm">{label}</div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        {[
          { href: "/dashboard/datasets", label: "Upload Dataset", desc: "Add CSV or load example", icon: Database, color: "border-sigma-600/40 hover:border-sigma-500" },
          { href: "/dashboard/eda", label: "EDA Workspace", desc: "Explore dataset visuals", icon: TrendingUp, color: "border-sigma-400/30 hover:border-sigma-300" },
          { href: "/dashboard/training", label: "Train Models", desc: "Start an AutoML job", icon: BrainCircuit, color: "border-sigma-500/30 hover:border-sigma-400" },
          { href: "/dashboard/predict", label: "Run Prediction", desc: "Use a deployed model", icon: Rocket, color: "border-sigma-300/30 hover:border-sigma-400" },
        ].map(({ href, label, desc, icon: Icon, color }) => (
          <Link
            key={href}
            href={href}
            className={`sigma-card flex items-center gap-4 cursor-pointer transition-all ${color}`}
          >
            <Icon className="w-8 h-8 text-sigma-400 flex-shrink-0" />
            <div>
              <div className="font-semibold text-white text-sm">{label}</div>
              <div className="text-sigma-500 text-xs">{desc}</div>
            </div>
          </Link>
        ))}
      </div>

      <div className="sigma-card">
        <h2 className="font-display font-semibold text-white mb-4 flex items-center gap-2">
          <Clock className="w-4 h-4 text-sigma-400" /> Recent Training Jobs
        </h2>
        {recentJobs.length === 0 ? (
          <div className="text-center py-10 text-sigma-600">
            <BrainCircuit className="w-10 h-10 mx-auto mb-3 opacity-30" />
            <p className="text-sm">No training jobs yet. Start by uploading a dataset.</p>
            <Link href="/dashboard/datasets" className="btn-primary text-sm mt-4 inline-flex">
              Upload Dataset
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {recentJobs.map((job) => (
              <div key={job.job_id} className="flex items-center gap-4 p-3 rounded-lg bg-sigma-900/30 hover:bg-sigma-800/30 transition-colors">
                {statusIcon(job.status)}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-white truncate font-mono">{job.job_id.slice(0, 8)}...</div>
                  <div className="text-xs text-sigma-500">Target: {job.target_column}</div>
                </div>
                <span
                  className={`metric-badge ${
                    job.status === "completed"
                      ? "bg-sigma-300/12 text-sigma-300"
                      : job.status === "running"
                        ? "bg-sigma-400/12 text-sigma-400"
                        : job.status === "failed"
                          ? "bg-sigma-500/12 text-sigma-500"
                          : "bg-sigma-800/40 text-sigma-400"
                  }`}
                >
                  {job.status}
                </span>
                {job.status === "completed" && (
                  <Link href={`/dashboard/models?job=${job.job_id}`} className="text-xs text-sigma-400 hover:text-sigma-300 underline">
                    View results
                  </Link>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
