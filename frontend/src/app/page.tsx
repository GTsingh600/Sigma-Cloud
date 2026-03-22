"use client";
import Link from "next/link";
import {
  BrainCircuit, Database, BarChart3, Rocket,
  ArrowRight, CheckCircle, Activity, Zap,
  ChevronRight, Shield, GitBranch
} from "lucide-react";
import LandingAuthActions from "@/components/auth/LandingAuthActions";
import { useAuth } from "@/components/auth/AuthProvider";

const features = [
  { icon: Database, title: "Smart Data Ingestion", desc: "Upload CSV/Excel or load from 4 built-in example datasets. Automatic column type detection and statistics." },
  { icon: BrainCircuit, title: "AutoML Engine", desc: "Trains Logistic Regression, Random Forest, XGBoost, LightGBM and more in one click. Zero config needed." },
  { icon: BarChart3, title: "Model Leaderboard", desc: "Interactive comparison charts, confusion matrices, ROC curves, and feature importance visualization." },
  { icon: Rocket, title: "One-click Deploy", desc: "Deploy your best model instantly and get a live prediction API endpoint. Download models via joblib." },
  { icon: Shield, title: "Cross-Validation", desc: "K-fold cross validation on every model. See CV scores, mean and std to prevent overfitting." },
  { icon: GitBranch, title: "Task Auto-Detection", desc: "Automatically detects classification vs. regression from your target column. No labeling needed." },
];

const stats = [
  { value: "5+", label: "ML Algorithms" },
  { value: "Auto", label: "Task Detection" },
  { value: "5-fold", label: "Cross Validation" },
  { value: "4", label: "Example Datasets" },
];

export default function LandingPage() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-[#161d23] text-[#f8f4ef] overflow-x-hidden">
      {/* Nav */}
      <nav className="fixed top-0 inset-x-0 z-50 border-b border-sigma-800/70 bg-[#1b242c]/88 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-sigma-600 flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
            <span className="font-display font-bold text-white tracking-tight">SigmaCloud AI</span>
          </div>
          <div className="flex items-center gap-4">
            <LandingAuthActions compact />
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-32 pb-24 px-6 overflow-hidden">
        {/* Background grid */}
        <div className="absolute inset-0 bg-grid-pattern bg-grid-size opacity-100" />
        <div className="absolute inset-0 bg-hero-gradient" />
        {/* Glow orb */}
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-sigma-500/12 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-sigma-700/50 bg-sigma-950/50 text-sigma-400 text-sm font-mono mb-8">
            <span className="w-2 h-2 rounded-full bg-sigma-500 animate-pulse" />
            AutoML Platform · Production Grade
          </div>

          <h1 className="font-display text-6xl md:text-7xl font-bold leading-[1.05] mb-6">
            Train ML Models<br />
            <span className="gradient-text">Without the Complexity</span>
          </h1>

          <p className="text-[color:var(--sigma-muted)] text-xl max-w-2xl mx-auto mb-10 leading-relaxed">
            SigmaCloud AI is an AutoML platform that lets you upload datasets,
            automatically train and compare models, visualize results, and
            deploy predictions — all from a single dashboard.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href={isAuthenticated ? "/dashboard" : "#google-signin"} className="btn-primary text-base px-8 py-3.5">
              {isAuthenticated ? "Open Dashboard" : "Get Started with Google"} <ArrowRight className="w-5 h-5" />
            </Link>
            <Link href="/dashboard/datasets" className="btn-outline text-base px-8 py-3.5">
              Try Example Dataset
            </Link>
          </div>

          <div id="google-signin" className="mt-8 flex justify-center">
            <LandingAuthActions />
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-4 gap-4 mt-20 max-w-2xl mx-auto">
            {stats.map(({ value, label }) => (
              <div key={label} className="text-center">
                <div className="font-display text-3xl font-bold gradient-text">{value}</div>
                <div className="text-xs text-sigma-500 mt-1">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-display text-4xl font-bold mb-4">
              Everything you need to build ML models
            </h2>
            <p className="text-sigma-500 text-lg">From raw data to deployed model in minutes.</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="sigma-card group cursor-default">
                <div className="w-10 h-10 rounded-lg bg-sigma-800/80 border border-sigma-700/50 flex items-center justify-center mb-4 group-hover:bg-sigma-700/50 transition-colors">
                  <Icon className="w-5 h-5 text-sigma-400" />
                </div>
                <h3 className="font-display font-semibold text-white mb-2">{title}</h3>
                <p className="text-sigma-500 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Workflow */}
      <section className="py-20 px-6 border-t border-sigma-900/50">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="font-display text-4xl font-bold mb-4">How it works</h2>
          <p className="text-sigma-500 mb-12">Four simple steps from data to production</p>
          <div className="grid md:grid-cols-4 gap-4">
            {[
              { n: "01", title: "Upload Data", desc: "Drop a CSV or pick an example dataset" },
              { n: "02", title: "Auto-Train", desc: "Models train automatically with CV" },
              { n: "03", title: "Compare", desc: "Explore metrics on the leaderboard" },
              { n: "04", title: "Deploy", desc: "Deploy best model & run predictions" },
            ].map(({ n, title, desc }) => (
              <div key={n} className="relative glass rounded-xl p-5 text-center">
                <div className="font-mono text-5xl font-bold text-sigma-800/60 mb-3">{n}</div>
                <div className="font-display font-semibold text-white mb-1">{title}</div>
                <div className="text-sigma-500 text-xs">{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6">
        <div className="max-w-2xl mx-auto text-center glass rounded-2xl p-12 glow-blue">
          <Zap className="w-10 h-10 text-sigma-400 mx-auto mb-6" />
          <h2 className="font-display text-4xl font-bold mb-4">
            Ready to build your first model?
          </h2>
          <p className="text-sigma-500 mb-8">No configuration. No code. Just results.</p>
          <Link href="/dashboard" className="btn-primary text-base px-10 py-3.5 mx-auto">
            Open Dashboard <ChevronRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-sigma-900/50 py-8 px-6 text-center text-sigma-600 text-sm font-mono">
        SigmaCloud AI — Built with FastAPI + Next.js + scikit-learn + XGBoost + LightGBM
      </footer>
    </div>
  );
}
