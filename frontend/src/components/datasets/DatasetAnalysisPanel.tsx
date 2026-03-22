"use client";

import { DatasetAnalysis, DatasetVisualization, ExplainabilityData } from "@/types";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  BarChart3,
  BrainCircuit,
  Lightbulb,
  Loader2,
  Sparkles,
} from "lucide-react";

const COLORS = ["#81A6C6", "#AACDDC", "#F3E3D0", "#D2C4B4", "#97B7D0", "#E6D8C7"];

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

function compactLabel(value: unknown, limit = 18) {
  const text = String(value ?? "");
  return text.length > limit ? `${text.slice(0, limit - 3)}...` : text;
}

function formatMetricValue(value: unknown, format?: string) {
  if (typeof value !== "number") return String(value ?? "");
  if (format === "percent") return `${value.toFixed(1)}%`;
  if (format === "correlation") return value.toFixed(2);
  if (format === "number") return value.toFixed(2);
  return value.toLocaleString();
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-sigma-800/60 bg-sigma-950/35 p-5">
      <div className={cx("absolute inset-x-0 top-0 h-1", accent)} />
      <div className="text-[11px] uppercase tracking-[0.2em] text-[color:var(--sigma-muted)]">{label}</div>
      <div className="mt-3 text-3xl font-semibold text-white">{value}</div>
    </div>
  );
}

function InsightCard({ insight, index }: { insight: string; index: number }) {
  const accents = [
    "from-sigma-500/22 to-sigma-400/8",
    "from-sigma-400/22 to-sigma-300/8",
    "from-sigma-500/18 to-sigma-300/10",
    "from-sigma-300/18 to-sigma-500/10",
  ];

  return (
    <div className={`rounded-2xl border border-sigma-800/60 bg-gradient-to-br ${accents[index % accents.length]} p-4`}>
      <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[color:var(--sigma-muted)]">
        <Sparkles className="h-3.5 w-3.5" />
        Insight
      </div>
      <div className="text-sm leading-6 text-sigma-100">{insight}</div>
    </div>
  );
}

function HeatmapCard({ visualization }: { visualization: DatasetVisualization }) {
  const rowLabels = Array.from(new Set(visualization.data.map(item => String(item.row ?? ""))));
  const columnLabels = Array.from(new Set(visualization.data.map(item => String(item.column ?? ""))));
  const values = visualization.data.map(item => Number(item.value ?? 0));
  const maxAbs = Math.max(...values.map(value => Math.abs(value)), 0.001);

  const getCellValue = (row: string, column: string) => {
    const cell = visualization.data.find(item => String(item.row ?? "") === row && String(item.column ?? "") === column);
    return Number(cell?.value ?? 0);
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[620px] border-separate border-spacing-2">
        <thead>
          <tr>
            <th className="p-2 text-left text-[11px] uppercase tracking-[0.18em] text-[color:var(--sigma-muted)]">Feature</th>
            {columnLabels.map(column => (
              <th key={column} className="p-2 text-left text-xs text-sigma-100/80">{compactLabel(column, 14)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rowLabels.map(row => (
            <tr key={row}>
              <td className="p-2 text-xs text-sigma-100/80">{compactLabel(row, 18)}</td>
              {columnLabels.map(column => {
                const value = getCellValue(row, column);
                const alpha = 0.15 + (Math.abs(value) / maxAbs) * 0.6;
                const background = value >= 0
                  ? `rgba(129, 166, 198, ${alpha})`
                  : `rgba(210, 196, 180, ${alpha})`;
                return (
                  <td
                    key={`${row}-${column}`}
                    className="rounded-xl border border-white/5 px-3 py-3 text-center font-mono text-xs text-white"
                    style={{ background }}
                  >
                    {value.toFixed(2)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BoxSummaryCard({ visualization }: { visualization: DatasetVisualization }) {
  const values = visualization.data.flatMap(item => [
    Number(item.min ?? 0),
    Number(item.q1 ?? 0),
    Number(item.median ?? 0),
    Number(item.q3 ?? 0),
    Number(item.max ?? 0),
  ]);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = Math.max(maxValue - minValue, 1);
  const pct = (value: number) => ((value - minValue) / range) * 100;

  return (
    <div className="space-y-4">
      {visualization.data.map((item, index) => {
        const min = Number(item.min ?? 0);
        const q1 = Number(item.q1 ?? 0);
        const median = Number(item.median ?? 0);
        const q3 = Number(item.q3 ?? 0);
        const max = Number(item.max ?? 0);
        return (
          <div key={`${item.feature ?? index}`} className="rounded-2xl border border-sigma-800/60 bg-sigma-950/25 p-4">
            <div className="mb-3 flex items-center justify-between gap-4">
              <div className="text-sm font-semibold text-white">{String(item.feature ?? `Feature ${index + 1}`)}</div>
              <div className="text-xs font-mono text-[color:var(--sigma-muted)]">{min.toFixed(2)} to {max.toFixed(2)}</div>
            </div>
            <div className="relative h-12 rounded-full bg-sigma-900/65">
              <div
                className="absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-sigma-500/70"
                style={{ left: `${pct(min)}%`, width: `${Math.max(pct(max) - pct(min), 1)}%` }}
              />
              <div
                className="absolute top-1/2 h-6 -translate-y-1/2 rounded-xl border border-sigma-200/40 bg-sigma-200/12"
                style={{ left: `${pct(q1)}%`, width: `${Math.max(pct(q3) - pct(q1), 2)}%` }}
              />
              <div
                className="absolute top-1/2 h-8 w-[3px] -translate-y-1/2 rounded-full bg-sigma-400"
                style={{ left: `${pct(median)}%` }}
              />
            </div>
            <div className="mt-3 grid grid-cols-5 gap-2 text-[11px] text-[color:var(--sigma-muted)]">
              <div>min {min.toFixed(2)}</div>
              <div>q1 {q1.toFixed(2)}</div>
              <div>med {median.toFixed(2)}</div>
              <div>q3 {q3.toFixed(2)}</div>
              <div>max {max.toFixed(2)}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function StandardChart({ visualization }: { visualization: DatasetVisualization }) {
  const isScatter = visualization.chart_type === "scatter";
  const isGrouped = visualization.chart_type === "grouped_bar";
  const isBar = visualization.chart_type === "bar";
  const singleSeries = (visualization.series?.length || 0) <= 1;
  const useVerticalBars = isBar && singleSeries;
  const chartHeight = isScatter ? 320 : useVerticalBars ? 340 : 300;
  const primaryKey = visualization.series?.[0]?.key ?? "value";

  if (isScatter) {
    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <ScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(170,205,220,0.08)" />
          <XAxis
            dataKey={visualization.x_key}
            tick={{ fill: "#cbb8b2", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "rgba(170,205,220,0.18)" }}
          />
          <YAxis
            dataKey={visualization.y_key}
            tick={{ fill: "#cbb8b2", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "rgba(170,205,220,0.18)" }}
          />
          <Tooltip
            cursor={{ strokeDasharray: "3 3", stroke: "rgba(170,205,220,0.35)" }}
            formatter={(value: unknown) => formatMetricValue(value, visualization.value_format)}
            contentStyle={{
              background: "rgba(36,49,60,0.97)",
              border: "1px solid rgba(170,205,220,0.18)",
              borderRadius: "14px",
              color: "#fff8f1",
            }}
          />
            <Scatter data={visualization.data} fill="#81A6C6">
              {visualization.data.map((_, index) => (
              <Cell key={index} fill={index % 2 === 0 ? "rgba(129,166,198,0.44)" : "rgba(170,205,220,0.44)"} />
            ))}
            </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    );
  }

  if (useVerticalBars) {
    return (
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart data={visualization.data} layout="vertical" margin={{ top: 10, right: 20, left: 30, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(170,205,220,0.08)" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: "#cbb8b2", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "rgba(170,205,220,0.18)" }}
          />
          <YAxis
            type="category"
            dataKey={visualization.x_key}
            width={120}
            tick={{ fill: "#fff8f1", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value: unknown) => compactLabel(value, 16)}
          />
          <Tooltip
            formatter={(value: unknown) => formatMetricValue(value, visualization.value_format)}
            labelFormatter={(value: unknown) => compactLabel(value, 28)}
            contentStyle={{
              background: "rgba(36,49,60,0.97)",
              border: "1px solid rgba(170,205,220,0.18)",
              borderRadius: "14px",
              color: "#fff8f1",
            }}
          />
          <Bar dataKey={primaryKey} radius={[0, 10, 10, 0]}>
            {visualization.data.map((_, index) => (
              <Cell key={index} fill={COLORS[index % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={visualization.data} margin={{ top: 10, right: 20, left: 0, bottom: 24 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(170,205,220,0.08)" />
        <XAxis
          dataKey={visualization.x_key}
          tick={{ fill: "#cbb8b2", fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: "rgba(170,205,220,0.18)" }}
          tickFormatter={(value: unknown) => compactLabel(value, isGrouped ? 14 : 18)}
        />
        <YAxis
          tick={{ fill: "#cbb8b2", fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: "rgba(170,205,220,0.18)" }}
        />
        <Tooltip
          formatter={(value: unknown) => formatMetricValue(value, visualization.value_format)}
          labelFormatter={(value: unknown) => compactLabel(value, 28)}
          contentStyle={{
            background: "rgba(36,49,60,0.97)",
            border: "1px solid rgba(170,205,220,0.18)",
            borderRadius: "14px",
            color: "#fff8f1",
          }}
        />
        {(visualization.series || []).map((series, index) => (
          <Bar key={series.key} dataKey={series.key} name={series.label} radius={[10, 10, 0, 0]} fill={COLORS[index % COLORS.length]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

function VisualizationCard({ visualization }: { visualization: DatasetVisualization }) {
  const special = visualization.chart_type === "heatmap" || visualization.chart_type === "box_summary";

  return (
    <div className="overflow-hidden rounded-[28px] border border-sigma-800/60 bg-sigma-950/45 p-6 shadow-[0_18px_46px_-30px_rgba(129,166,198,0.2)]">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex rounded-full border border-sigma-800/50 bg-white/[0.03] px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-[color:var(--sigma-muted)]">
            {visualization.chart_type.replace("_", " ")}
          </div>
          <h3 className="font-display text-xl font-semibold text-white">{visualization.title}</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--sigma-muted)]">{visualization.description}</p>
        </div>
      </div>

      {visualization.chart_type === "heatmap" ? (
        <HeatmapCard visualization={visualization} />
      ) : visualization.chart_type === "box_summary" ? (
        <BoxSummaryCard visualization={visualization} />
      ) : (
        <div className={cx("rounded-2xl border border-sigma-800/60 bg-sigma-950/30 p-4", special && "p-0")}>
          <StandardChart visualization={visualization} />
        </div>
      )}
    </div>
  );
}

function ExplainabilityPanel({ explainability }: { explainability: ExplainabilityData }) {
  const total = explainability.feature_importance.reduce((sum, item) => sum + item.importance, 0) || 1;

  return (
      <div className="overflow-hidden rounded-[28px] border border-sigma-500/20 bg-[linear-gradient(180deg,rgba(47,66,82,0.96),rgba(28,37,45,0.96))] p-6 shadow-[0_18px_44px_-28px_rgba(129,166,198,0.2)]">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
            <div className="mb-2 inline-flex rounded-full border border-sigma-400/20 bg-sigma-400/10 px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-sigma-300">
            Explainable AI
          </div>
          <h3 className="font-display text-2xl font-semibold text-white">{explainability.model_name}</h3>
            <p className="mt-2 text-sm leading-6 text-[color:var(--sigma-muted)]">
            Global explanation from the strongest completed model for this dataset.
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-right">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--sigma-muted)]">{explainability.metric_label}</div>
          <div className="mt-1 text-2xl font-semibold text-white">
            {explainability.metric_value !== undefined ? explainability.metric_value.toFixed(3) : "n/a"}
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
        <div className="rounded-2xl border border-white/8 bg-sigma-950/20 p-5">
          <div className="mb-4 text-sm font-medium text-white">Most influential features</div>
          <div className="space-y-4">
            {explainability.feature_importance.map((item, index) => {
              const share = (item.importance / total) * 100;
              return (
                <div key={item.feature}>
                  <div className="mb-1.5 flex items-center justify-between gap-4">
                    <div className="text-sm text-sigma-100">{item.feature}</div>
                    <div className="text-xs font-mono text-[color:var(--sigma-muted)]">{share.toFixed(1)}%</div>
                  </div>
                  <div className="h-3 rounded-full bg-white/8">
                    <div
                      className="h-3 rounded-full"
                      style={{
                        width: `${Math.max(share, 6)}%`,
                        background: `linear-gradient(90deg, ${COLORS[index % COLORS.length]}, rgba(255,255,255,0.55))`,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="rounded-2xl border border-white/8 bg-sigma-950/20 p-5">
          <div className="mb-4 text-sm font-medium text-white">Model reading notes</div>
          <div className="space-y-3">
            {explainability.insights.map((insight, index) => (
              <div key={`${index}-${insight}`} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm leading-6 text-sigma-100">
                {insight}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function DatasetAnalysisPanel({
  analysis,
  loading,
}: {
  analysis: DatasetAnalysis | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="mt-6 rounded-[28px] border border-sigma-800/70 bg-sigma-950/45 p-16">
        <div className="flex items-center justify-center gap-3 text-[color:var(--sigma-muted)]">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Generating visual analysis and explanations...</span>
        </div>
      </div>
    );
  }

  if (!analysis) return null;

  const featured = analysis.visualizations.slice(0, 3);
  const supporting = analysis.visualizations.slice(3);

  return (
    <div className="mt-8 space-y-8">
      <div className="overflow-hidden rounded-[32px] border border-sigma-800/60 bg-[linear-gradient(180deg,rgba(39,53,64,0.98),rgba(22,29,35,0.96))] p-7 shadow-[0_20px_56px_-34px_rgba(129,166,198,0.18)]">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-2 inline-flex rounded-full border border-sigma-800/50 bg-white/[0.03] px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-[color:var(--sigma-muted)]">
              EDA Workspace
            </div>
            <h2 className="font-display flex items-center gap-3 text-3xl font-semibold text-white">
              <BrainCircuit className="h-6 w-6 text-sigma-400" />
              Dataset Intelligence
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[color:var(--sigma-muted)]">
              Cleaned, prioritized visuals chosen for dataset structure, data quality, modeling signal, and target behavior.
            </p>
          </div>
          {analysis.summary.target_column && (
            <div className="rounded-2xl border border-sigma-800/50 bg-white/[0.03] px-4 py-3 text-sm text-sigma-100">
              target: <span className="font-semibold text-white">{analysis.summary.target_column}</span>
            </div>
          )}
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Rows" value={analysis.summary.rows.toLocaleString()} accent="bg-gradient-to-r from-sigma-500 to-sigma-400" />
          <StatCard label="Columns" value={analysis.summary.columns.toString()} accent="bg-gradient-to-r from-sigma-400 to-sigma-200" />
          <StatCard label="Numeric / Categorical" value={`${analysis.summary.numeric_columns} / ${analysis.summary.categorical_columns}`} accent="bg-gradient-to-r from-sigma-600 to-sigma-400" />
          <StatCard label="Missing" value={`${analysis.summary.missing_pct.toFixed(1)}%`} accent="bg-gradient-to-r from-sigma-300 to-sigma-500" />
        </div>
      </div>

      {analysis.insights.length > 0 && (
        <div>
          <div className="mb-4 flex items-center gap-2 text-sm font-medium text-sigma-100/80">
            <Lightbulb className="h-4 w-4 text-sigma-300" />
            Important insights
          </div>
          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
            {analysis.insights.map((insight, index) => (
              <InsightCard key={`${index}-${insight}`} insight={insight} index={index} />
            ))}
          </div>
        </div>
      )}

      {analysis.explainability && <ExplainabilityPanel explainability={analysis.explainability} />}

      {featured.length > 0 && (
        <div>
          <div className="mb-4 flex items-center gap-2 text-sm font-medium text-sigma-100/80">
            <BarChart3 className="h-4 w-4 text-sigma-400" />
            Featured visuals
          </div>
          <div className="grid gap-6 xl:grid-cols-1">
            {featured.map(visualization => (
              <VisualizationCard key={visualization.id} visualization={visualization} />
            ))}
          </div>
        </div>
      )}

      {supporting.length > 0 && (
        <div>
          <div className="mb-4 flex items-center gap-2 text-sm font-medium text-sigma-100/80">
            <Sparkles className="h-4 w-4 text-sigma-400" />
            Supporting visuals
          </div>
          <div className="grid gap-6 2xl:grid-cols-2">
            {supporting.map(visualization => (
              <VisualizationCard key={visualization.id} visualization={visualization} />
            ))}
          </div>
        </div>
      )}

      {analysis.visualizations.length === 0 && (
        <div className="rounded-[28px] border border-sigma-800/60 bg-sigma-950/35 p-10 text-[color:var(--sigma-muted)]">
          This dataset did not yield enough structured signal for additional visualizations.
        </div>
      )}
    </div>
  );
}
