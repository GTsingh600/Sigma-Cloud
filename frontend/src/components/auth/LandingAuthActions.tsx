"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { useAuth } from "./AuthProvider";
import GoogleSignInButton from "./GoogleSignInButton";

interface LandingAuthActionsProps {
  compact?: boolean;
}

export default function LandingAuthActions({ compact = false }: LandingAuthActionsProps) {
  const { isAuthenticated, loading, user, logout } = useAuth();

  if (loading) {
    return (
      <div className="rounded-xl border border-sigma-800/60 bg-sigma-900/40 px-4 py-3 text-sm text-sigma-400">
        Restoring session...
      </div>
    );
  }

  if (isAuthenticated && user) {
    return (
      <div className={`flex ${compact ? "items-center gap-3" : "flex-col items-start gap-4"}`}>
        <div className="flex items-center gap-3 rounded-2xl border border-sigma-800/60 bg-sigma-900/40 px-4 py-3">
          {user.picture ? (
            <img src={user.picture} alt={user.name} className="h-10 w-10 rounded-full border border-sigma-700/60 object-cover" />
          ) : (
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-sigma-500/15 text-sm font-semibold text-sigma-200">
              {user.name.slice(0, 1).toUpperCase()}
            </div>
          )}
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-white">{user.name}</div>
            <div className="truncate text-xs text-sigma-500">{user.email}</div>
          </div>
        </div>
        <div className={`flex ${compact ? "items-center gap-2" : "items-center gap-3"}`}>
          <Link href="/dashboard" className="btn-primary">
            Open Dashboard <ArrowRight className="h-4 w-4" />
          </Link>
          <button type="button" onClick={logout} className="btn-outline">
            Sign Out
          </button>
        </div>
      </div>
    );
  }

  return <GoogleSignInButton compact={compact} />;
}
