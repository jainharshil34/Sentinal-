"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { 
  AlertTriangle, 
  Loader2, 
  CheckCircle2, 
  Info,
  Flame,
  Wrench,
  FileText,
  Clock,
  ShieldAlert
} from "lucide-react";

interface SimulationWindow {
  start_time: string;
  duration_hours: number;
}

interface SimulationInfo {
  default: SimulationWindow;
  vizag_replay: SimulationWindow;
}

interface TriggeredRule {
  rule_name: string;
  severity: number;
  reason: string;
  scenario_name: string;
}

export default function AlertsPage() {
  const [simInfo, setSimInfo] = useState<SimulationInfo | null>(null);
  const [alerts, setAlerts] = useState<TriggeredRule[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<number | "all">("all");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // We will scan all 5 presets of the default dataset to show an aggregated safety alert center feed!
  const presets = [
    { key: "scenario_1", name: "S1: Methane Spike", offset: 24.5 },
    { key: "scenario_2", name: "S2: Confined Space CO", offset: 36.5 },
    { key: "scenario_3", name: "S3: H2S Acid Leak", offset: 48.5 },
    { key: "scenario_4", name: "S4: Methane Spark Risk", offset: 60.5 },
    { key: "silent_failure", name: "S5: Telemetry Interruption", offset: 12.0 }
  ];

  useEffect(() => {
    const fetchAllAlerts = async () => {
      setLoading(true);
      setError(null);

      try {
        const infoRes = await axios.get<SimulationInfo>(`${apiUrl}/api/simulation-info`);
        const simStart = infoRes.data.default?.start_time;
        if (!simStart) {
          setError("Simulation start time not found.");
          setLoading(false);
          return;
        }

        const baseDate = new Date(simStart);
        const collectedAlerts: TriggeredRule[] = [];

        // Query each window in parallel
        await Promise.all(
          presets.map(async (p) => {
            const start = new Date(baseDate.getTime() + p.offset * 60 * 60 * 1000).toISOString();
            const end = new Date(baseDate.getTime() + (p.offset + 0.5) * 60 * 60 * 1000).toISOString();
            
            const res = await axios.get(`${apiUrl}/api/risk-assessment`, {
              params: { window_start: start, window_end: end, dataset: "default" }
            });

            res.data.triggered_rules.forEach((rule: any) => {
              collectedAlerts.push({
                ...rule,
                scenario_name: p.name
              });
            });
          })
        );

        // Sort alerts by severity descending
        setAlerts(collectedAlerts.sort((a, b) => b.severity - a.severity));
      } catch (err) {
        console.error("Failed to load alerts feed", err);
        setError("Could not compile alerts log. Is backend running?");
      } finally {
        setLoading(false);
      }
    };

    fetchAllAlerts();
  }, []);

  const filteredAlerts = activeFilter === "all" 
    ? alerts 
    : alerts.filter(a => a.severity === activeFilter);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="border-b border-slate-800 pb-5">
        <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
          <AlertTriangle className="h-8 w-8 text-rose-500 animate-pulse" />
          Active Incident Alarms
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          Plant Safety Operations Center (SOC) logs compiling active safety violations across the facility floor.
        </p>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveFilter("all")}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
            activeFilter === "all"
              ? "bg-slate-800 text-white border border-slate-700"
              : "bg-slate-900/40 text-slate-400 border border-slate-900 hover:border-slate-800"
          }`}
        >
          All Alarms ({alerts.length})
        </button>
        <button
          onClick={() => setActiveFilter(3)}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
            activeFilter === 3
              ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
              : "bg-slate-900/40 text-slate-400 border border-slate-900 hover:border-slate-850"
          }`}
        >
          Severity 3 (High) ({alerts.filter(a => a.severity === 3).length})
        </button>
        <button
          onClick={() => setActiveFilter(2)}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
            activeFilter === 2
              ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
              : "bg-slate-900/40 text-slate-400 border border-slate-900 hover:border-slate-850"
          }`}
        >
          Severity 2 (Medium) ({alerts.filter(a => a.severity === 2).length})
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-sm font-semibold">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 text-slate-400">
          <Loader2 className="h-10 w-10 animate-spin text-rose-400 mb-3" />
          <span>Polling plant alarms...</span>
        </div>
      ) : filteredAlerts.length === 0 ? (
        <div className="p-12 text-center bg-slate-900 rounded-2xl border border-slate-800 text-slate-400 flex flex-col items-center justify-center">
          <CheckCircle2 className="h-12 w-12 text-emerald-500 mb-4" />
          <span className="text-lg font-bold text-slate-200">No active violations detected</span>
          <span className="text-xs text-slate-500 mt-1">Facility telemetry reports nominal state.</span>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredAlerts.map((alert, index) => (
            <div 
              key={index} 
              className={`p-5 rounded-2xl border bg-slate-900/60 shadow-md flex gap-4 transition-all duration-200 hover:bg-slate-900 ${
                alert.severity === 3 
                  ? "border-rose-500/20 hover:border-rose-500/35 shadow-rose-950/5" 
                  : "border-amber-500/20 hover:border-amber-500/35 shadow-amber-950/5"
              }`}
            >
              <div className="shrink-0 mt-1">
                <ShieldAlert className={`h-6 w-6 ${
                  alert.severity === 3 ? "text-rose-500" : "text-amber-500"
                }`} />
              </div>
              <div className="space-y-2 flex-1">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-black font-mono tracking-wider text-slate-100 uppercase">
                      {alert.rule_name}
                    </span>
                    <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                      alert.severity === 3 
                        ? "bg-rose-500/10 text-rose-400 border border-rose-500/20" 
                        : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    }`}>
                      Severity {alert.severity}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-500 bg-slate-950 px-2 py-1 rounded border border-slate-800 flex items-center gap-1 font-semibold">
                    <Clock className="h-3 w-3" />
                    {alert.scenario_name}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed font-medium">
                  {alert.reason}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
