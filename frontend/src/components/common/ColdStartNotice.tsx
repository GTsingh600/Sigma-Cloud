"use client";

import { useEffect, useState } from "react";
import { Loader2, Server } from "lucide-react";

/**
 * Explains the free-tier cold start while the first request is in flight.
 *
 * The backend sleeps after inactivity and takes up to a minute to wake. Without
 * this, a first-time visitor sees an unexplained spinner and assumes the app is
 * broken - so the copy only appears once the wait passes the point where a warm
 * response would already have arrived.
 */

const HINT_AFTER_MS = 4000;
const ESTIMATED_WAKE_SECONDS = 60;

export function ColdStartNotice({ active }: { active: boolean }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!active) {
      setElapsed(0);
      return;
    }

    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      setElapsed(Date.now() - startedAt);
    }, 500);

    return () => window.clearInterval(timer);
  }, [active]);

  if (!active || elapsed < HINT_AFTER_MS) return null;

  const seconds = Math.floor(elapsed / 1000);
  const progress = Math.min((seconds / ESTIMATED_WAKE_SECONDS) * 100, 96);

  return (
    <div className="mt-6 rounded-2xl border border-sigma-400/25 bg-sigma-500/8 p-4 text-left animate-in">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl bg-sigma-500/15">
          <Server className="h-4 w-4 text-sigma-300" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-sigma-100">Waking the server</p>
          <p className="mt-1 text-xs leading-5 text-sigma-400">
            This demo runs on a free tier that sleeps when idle. The first request
            takes up to a minute while the service starts - everything is fast
            after that.
          </p>

          <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-sigma-900/60">
            <div
              className="h-full rounded-full bg-gradient-to-r from-sigma-400 to-sigma-200 transition-[width] duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="mt-2 flex items-center gap-2 font-mono text-[11px] text-sigma-500">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>
              {seconds}s elapsed - usually ready by {ESTIMATED_WAKE_SECONDS}s
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ColdStartNotice;
