"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import axios from "axios";
import { 
  LayoutDashboard, 
  AlertTriangle, 
  RotateCcw, 
  Activity, 
  ShieldAlert,
  Server,
  RefreshCw,
  Brain,
  ShieldCheck,
  TrendingUp,
  Shield,
  UploadCloud,
  FileText
} from "lucide-react";

const navItems = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Fleet Overview", href: "/fleet-overview", icon: Server },
  { name: "Alerts", href: "/alerts", icon: AlertTriangle },
  { name: "Incident Log", href: "/incident-log", icon: FileText },
  { name: "Pattern Intelligence", href: "/pattern-intelligence", icon: Brain },
  { name: "Compliance Audit", href: "/compliance-audit", icon: ShieldCheck },
  { name: "Deployment Trust", href: "/deployment-trust", icon: Shield },
  { name: "Data Ingestion", href: "/data-ingestion", icon: UploadCloud },
  { name: "Business Case", href: "/business-case", icon: TrendingUp },
  { name: "Counterfactual Replay", href: "/counterfactual-replay", icon: RotateCcw },
  { name: "Scorecard", href: "/scorecard", icon: Activity },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [resetting, setResetting] = useState(false);

  const handleReset = async () => {
    setResetting(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await axios.post(`${apiUrl}/api/simulation/reset`);
      window.location.reload();
    } catch (err) {
      console.error("Failed to reset demo DB", err);
      alert("Failed to reset demo database. Make sure backend is running.");
    } finally {
      setResetting(false);
    }
  };

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 text-slate-100 flex flex-col h-screen fixed left-0 top-0 z-40">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-slate-800 gap-2">
        <ShieldAlert className="h-6 w-6 text-emerald-400" />
        <span className="text-lg font-bold tracking-wider bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
          SentinelGrid
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-6 px-4 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon || Activity;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 group ${
                isActive
                  ? "bg-emerald-500/10 text-emerald-400 border-l-4 border-emerald-400 pl-3"
                  : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-100"
              }`}
            >
              <Icon
                className={`h-5 w-5 transition-transform duration-200 group-hover:scale-105 ${
                  isActive ? "text-emerald-400" : "text-slate-400 group-hover:text-slate-200"
                }`}
              />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Reset Demo Button */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/60">
        <button
          onClick={handleReset}
          disabled={resetting}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-950 hover:bg-slate-800 text-rose-400 hover:text-rose-300 border border-slate-800 rounded-lg text-xs font-bold transition-all cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`h-4.5 w-4.5 ${resetting ? "animate-spin text-rose-500" : ""}`} />
          {resetting ? "Resetting DB..." : "Reset Demo DB"}
        </button>
      </div>

      {/* Footer System Status */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/40">
        <div className="flex items-center gap-2.5 text-xs text-slate-400">
          <Server className="h-4 w-4 text-emerald-500 animate-pulse" />
          <div className="flex flex-col">
            <span className="font-semibold text-slate-300">System Gateway</span>
            <span className="text-[10px] text-slate-500">v0.1.0-dev</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
