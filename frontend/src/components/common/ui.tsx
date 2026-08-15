"use client";

import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";

/** Shared presentational primitives so pages stop re-declaring the same markup. */

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`sigma-skeleton rounded-xl ${className}`} />;
}

export function CardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="sigma-card space-y-3">
      <Skeleton className="h-4 w-1/3" />
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className="h-3 w-full" />
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="grid gap-2" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
          {Array.from({ length: columns }).map((_, columnIndex) => (
            <Skeleton key={columnIndex} className="h-8" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-sigma-700/50 bg-sigma-900/20 px-6 py-14 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-sigma-500/10">
        <Icon className="h-6 w-6 text-sigma-400" />
      </div>
      <h3 className="font-display text-lg font-semibold text-white">{title}</h3>
      <p className="mt-2 max-w-sm text-sm leading-6 text-sigma-500">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";

const TONE_STYLES: Record<StatusTone, string> = {
  success: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  warning: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  danger: "border-rose-400/30 bg-rose-400/10 text-rose-200",
  info: "border-sigma-400/30 bg-sigma-400/10 text-sigma-200",
  neutral: "border-sigma-700/50 bg-sigma-900/40 text-sigma-400",
};

export function StatusPill({
  tone = "neutral",
  children,
  icon: Icon,
}: {
  tone?: StatusTone;
  children: ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${TONE_STYLES[tone]}`}
    >
      {Icon && <Icon className="h-3 w-3" />}
      {children}
    </span>
  );
}

export function JobStatusPill({ status }: { status: string }) {
  const config: Record<string, { tone: StatusTone; icon: React.ComponentType<{ className?: string }> }> = {
    completed: { tone: "success", icon: CheckCircle2 },
    failed: { tone: "danger", icon: XCircle },
    running: { tone: "info", icon: Loader2 },
    pending: { tone: "warning", icon: Clock },
  };
  const { tone, icon } = config[status] ?? { tone: "neutral" as StatusTone, icon: Clock };

  return (
    <StatusPill tone={tone} icon={icon}>
      {status}
    </StatusPill>
  );
}

export function InlineAlert({
  tone = "warning",
  title,
  children,
  action,
}: {
  tone?: StatusTone;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className={`rounded-2xl border p-4 ${TONE_STYLES[tone]}`}>
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">{title}</p>
          {children && <div className="mt-1 text-xs leading-5 opacity-90">{children}</div>}
          {action && <div className="mt-3">{action}</div>}
        </div>
      </div>
    </div>
  );
}

export function SectionHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-display text-2xl font-bold text-white sm:text-3xl">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-sm text-sigma-500">{description}</p>}
      </div>
      {action}
    </div>
  );
}
