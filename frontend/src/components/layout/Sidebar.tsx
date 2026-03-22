"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Database, BrainCircuit, BarChart3,
  Rocket, Zap, ChevronRight, Activity, LogOut
} from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";

const navItems = [
  { label: "Dashboard",    href: "/dashboard",         icon: LayoutDashboard },
  { label: "Datasets",     href: "/dashboard/datasets", icon: Database },
  { label: "EDA",          href: "/dashboard/eda",      icon: BarChart3 },
  { label: "Train Models", href: "/dashboard/training", icon: BrainCircuit },
  { label: "Leaderboard",  href: "/dashboard/models",   icon: Activity },
  { label: "Predict",      href: "/dashboard/predict",  icon: Zap },
  { label: "Deploy",       href: "/dashboard/deploy",   icon: Rocket },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="w-64 flex-shrink-0 flex flex-col border-r border-sigma-800/40 bg-[#1c252d]">
      {/* Logo */}
      <div className="p-6 border-b border-sigma-800/50">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sigma-400 to-sigma-500 flex items-center justify-center shadow-[0_0_24px_rgba(129,166,198,0.2)] group-hover:from-sigma-300 group-hover:to-sigma-500 transition-all">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-display font-bold text-white text-sm tracking-wide">SigmaCloud</div>
            <div className="text-[10px] text-sigma-400 tracking-widest uppercase">AI Platform</div>
          </div>
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(({ label, href, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group
                ${active
                  ? "bg-sigma-500/12 text-white border border-sigma-400/30 shadow-[inset_0_0_0_1px_rgba(170,205,220,0.08)]"
                  : "text-sigma-500 hover:text-sigma-200 hover:bg-sigma-900/40 border border-transparent"
                }`}
            >
              <Icon className={`w-4 h-4 flex-shrink-0 ${active ? "text-sigma-400" : "text-sigma-600 group-hover:text-sigma-400"}`} />
              <span className="flex-1">{label}</span>
              {active && <ChevronRight className="w-3 h-3 text-sigma-500" />}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-sigma-800/50 p-4">
        <div className="mb-3 rounded-2xl border border-sigma-800/50 bg-sigma-900/30 p-3">
          <div className="flex items-center gap-3">
            {user?.picture ? (
              <img src={user.picture} alt={user.name} className="h-10 w-10 rounded-full border border-sigma-700/60 object-cover" />
            ) : (
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-sigma-500/15 text-sm font-semibold text-sigma-200">
                {user?.name?.slice(0, 1).toUpperCase() || "U"}
              </div>
            )}
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-white">{user?.name || "Signed in"}</div>
              <div className="truncate text-xs text-sigma-500">{user?.email || "Google account"}</div>
            </div>
          </div>
          <button type="button" onClick={logout} className="btn-outline mt-3 w-full justify-center py-2 text-sm">
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </div>
        <div className="text-center font-mono text-xs text-sigma-600">
          SigmaCloud AI v1.0.0
        </div>
      </div>
    </aside>
  );
}
