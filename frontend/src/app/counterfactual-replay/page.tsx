"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { 
  RotateCcw, 
  Loader2, 
  AlertTriangle, 
  CheckCircle2, 
  Info,
  ShieldCheck,
  FileText,
  Wrench,
  ToggleLeft,
  ToggleRight,
  Clock,
  ExternalLink,
  Sliders,
  XCircle
} from "lucide-react";

interface SimulationWindow {
  start_time: string;
  duration_hours: number;
}

interface SimulationInfo {
  default: SimulationWindow;
  vizag_replay: SimulationWindow;
}

interface Permit {
  id: number;
  permit_id: string;
  zone: string;
  permit_type: string;
  issued_at: string;
  closed_at: string | null;
  issued_by: string;
}

interface MaintenanceLog {
  id: number;
  zone: string;
  equipment_id: string;
  event_type: string;
  logged_at: string;
  notes: string;
}

interface TriggeredRule {
  rule_name: string;
  severity: number;
  reason: string;
}

interface RiskAssessment {
  score: number;
  tier: number;
  tier_name: string;
  triggered_rules: TriggeredRule[];
}

interface TelemetrySummary {
  gas_readings: any[];
  permits: Permit[];
  maintenance_logs: MaintenanceLog[];
}

interface ReplayEvent {
  offset_hours: number;
  type: "real" | "sentinelgrid";
  title: string;
  description: string;
  risk_score?: number;
  tier?: number;
  timestamp: string;
}

interface ReplayData {
  lead_time_minutes: number;
  predictive_lead_time_minutes?: number;
  events: ReplayEvent[];
}

export default function CounterfactualReplayPage() {
  const [activeTab, setActiveTab] = useState<"timeline" | "sandbox">("timeline");

  // Tab 1: Timeline Replay States
  const [replayData, setReplayData] = useState<ReplayData | null>(null);
  const [replayLoading, setReplayLoading] = useState<boolean>(true);
  const [replayError, setReplayError] = useState<string | null>(null);

  // Tab 2: Sandbox Simulator States
  const [dataset, setDataset] = useState<"default" | "vizag_replay">("default");
  const [simInfo, setSimInfo] = useState<SimulationInfo | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<string>("scenario_1");

  const [originalAssessment, setOriginalAssessment] = useState<RiskAssessment | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetrySummary | null>(null);

  const [simulatedAssessment, setSimulatedAssessment] = useState<RiskAssessment | null>(null);
  const [excludedPermitIds, setExcludedPermitIds] = useState<string[]>([]);
  const [excludedMaintIds, setExcludedMaintIds] = useState<number[]>([]);

  const [loading, setLoading] = useState<boolean>(true);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const scenarioPresets: Record<string, { name: string; startOffsetHr: number; endOffsetHr: number; desc: string }> = {
    scenario_1: {
      name: "S1: Hot Work + CH4 (Zone-A)",
      startOffsetHr: 24.5,
      endOffsetHr: 25.0,
      desc: "Imminent CH4 explosion risk from hot work permit combined with overdue ventilation check."
    },
    scenario_2: {
      name: "S2: Confined Space + CO (Zone-B)",
      startOffsetHr: 36.5,
      endOffsetHr: 37.0,
      desc: "Confined space permit with CO gas buildup and overdue detector calibration."
    },
    scenario_3: {
      name: "S3: Hot Work + H2S + Repair (Zone-C)",
      startOffsetHr: 48.5,
      endOffsetHr: 49.0,
      desc: "Hot work permit issued during active repair of a leaking H2S acid gas valve."
    },
    scenario_4: {
      name: "S4: Electrical + CH4 (Zone-D)",
      startOffsetHr: 60.5,
      endOffsetHr: 61.0,
      desc: "Spark risk from electrical work permit and overdue breaker safety isolation."
    },
    silent_failure: {
      name: "S5: Telemetry Offline (Zone-E)",
      startOffsetHr: 12.0,
      endOffsetHr: 12.5,
      desc: "Confined space entry while gas sensors went silent, masking telemetry."
    }
  };

  const vizagPresets: Record<string, { name: string; startOffsetHr: number; endOffsetHr: number; desc: string }> = {
    vizag_buildup: {
      name: "Vizag coke oven battery incident",
      startOffsetHr: 12.0,
      endOffsetHr: 12.5,
      desc: "CO buildup with hot work and overdue regulator calibration."
    }
  };

  // Fetch Timeline Replay data
  useEffect(() => {
    const fetchReplay = async () => {
      setReplayLoading(true);
      setReplayError(null);
      try {
        const res = await axios.get<ReplayData>(`${apiUrl}/api/replay/vizag`);
        setReplayData(res.data);
      } catch (err: any) {
        console.error(err);
        setReplayError("Failed to fetch Vizag incident timeline replay.");
      } finally {
        setReplayLoading(false);
      }
    };

    if (activeTab === "timeline") {
      fetchReplay();
    }
  }, [activeTab]);

  // Fetch simulation start times on mount (for Sandbox)
  useEffect(() => {
    const fetchSimInfo = async () => {
      try {
        const res = await axios.get<SimulationInfo>(`${apiUrl}/api/simulation-info`);
        setSimInfo(res.data);
      } catch (err: any) {
        console.error(err);
        setError("Failed to connect to backend server.");
      }
    };
    if (activeTab === "sandbox") {
      fetchSimInfo();
    }
  }, [activeTab]);

  // Sync preset when dataset changes (Sandbox)
  useEffect(() => {
    if (dataset === "default") {
      setSelectedScenario("scenario_1");
    } else {
      setSelectedScenario("vizag_buildup");
    }
    setExcludedPermitIds([]);
    setExcludedMaintIds([]);
  }, [dataset]);

  // Load base data (Sandbox)
  useEffect(() => {
    if (!simInfo || activeTab !== "sandbox") return;

    const fetchBaseData = async () => {
      setLoading(true);
      setError(null);

      const simStart = simInfo[dataset]?.start_time;
      if (!simStart) {
        setError("Simulation data is missing.");
        setLoading(false);
        return;
      }

      const baseDate = new Date(simStart);
      const preset = dataset === "default" ? scenarioPresets[selectedScenario] : vizagPresets[selectedScenario];
      if (!preset) return;

      const startDate = new Date(baseDate.getTime() + preset.startOffsetHr * 60 * 60 * 1000);
      const endDate = new Date(baseDate.getTime() + preset.endOffsetHr * 60 * 60 * 1000);

      const startIso = startDate.toISOString();
      const endIso = endDate.toISOString();

      try {
        const [riskRes, telemetryRes] = await Promise.all([
          axios.get<RiskAssessment>(`${apiUrl}/api/risk-assessment`, {
            params: { window_start: startIso, window_end: endIso, dataset }
          }),
          axios.get<TelemetrySummary>(`${apiUrl}/api/telemetry-summary`, {
            params: { window_start: startIso, window_end: endIso, dataset }
          })
        ]);
        setOriginalAssessment(riskRes.data);
        setSimulatedAssessment(riskRes.data);
        setTelemetry(telemetryRes.data);
        setExcludedPermitIds([]);
        setExcludedMaintIds([]);
      } catch (err: any) {
        console.error(err);
        setError("An error occurred fetching data.");
      } finally {
        setLoading(false);
      }
    };

    fetchBaseData();
  }, [simInfo, dataset, selectedScenario, activeTab]);

  // Recalculate simulated risk whenever exclusions change (Sandbox)
  useEffect(() => {
    if (!simInfo || !originalAssessment || activeTab !== "sandbox") return;

    const runSimulation = async () => {
      setSimulating(true);
      const simStart = simInfo[dataset]?.start_time;
      const baseDate = new Date(simStart);
      const preset = dataset === "default" ? scenarioPresets[selectedScenario] : vizagPresets[selectedScenario];
      if (!preset) return;

      const startDate = new Date(baseDate.getTime() + preset.startOffsetHr * 60 * 60 * 1000);
      const endDate = new Date(baseDate.getTime() + preset.endOffsetHr * 60 * 60 * 1000);

      try {
        const riskRes = await axios.get<RiskAssessment>(`${apiUrl}/api/risk-assessment`, {
          params: {
            window_start: startDate.toISOString(),
            window_end: endDate.toISOString(),
            dataset,
            exclude_permit_ids: excludedPermitIds.length > 0 ? excludedPermitIds : undefined,
            exclude_maint_ids: excludedMaintIds.length > 0 ? excludedMaintIds : undefined
          }
        });
        setSimulatedAssessment(riskRes.data);
      } catch (err) {
        console.error("Failed to run counterfactual simulation", err);
      } finally {
        setSimulating(false);
      }
    };

    runSimulation();
  }, [excludedPermitIds, excludedMaintIds]);

  const togglePermitExclusion = (permitId: string) => {
    setExcludedPermitIds(prev => 
      prev.includes(permitId) ? prev.filter(id => id !== permitId) : [...prev, permitId]
    );
  };

  const toggleMaintExclusion = (id: number) => {
    setExcludedMaintIds(prev => 
      prev.includes(id) ? prev.filter(mId => mId !== id) : [...prev, id]
    );
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
            <RotateCcw className="h-8 w-8 text-cyan-500" />
            Counterfactual Sandbox & Replay
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Trace historical plant incident timelines and interactively modify active variables to mitigate compound threat scenarios.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-3 bg-slate-900/60 p-1.5 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab("timeline")}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
              activeTab === "timeline" 
                ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30" 
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Incident Timeline Replay
          </button>
          <button
            onClick={() => setActiveTab("sandbox")}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
              activeTab === "sandbox" 
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" 
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Mitigation Sandbox
          </button>
        </div>
      </div>

      {/* TIMELINE REPLAY VIEW */}
      {activeTab === "timeline" && (
        <div className="space-y-8">
          {replayLoading ? (
            <div className="flex flex-col items-center justify-center py-32 text-slate-400">
              <Loader2 className="h-10 w-10 animate-spin text-cyan-400 mb-3" />
              <span>Analyzing historical logs and compiling Vizag incident tracks...</span>
            </div>
          ) : !replayData || replayError ? (
            <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-2xl max-w-lg mx-auto">
              <XCircle className="h-12 w-12 text-rose-500 mx-auto mb-4" />
              <h3 className="text-lg font-bold text-slate-200">Replay Data Offline</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                {replayError || "Unable to retrieve Vizag Coke Oven incident replay timeline from backend. Make sure backend is running."}
              </p>
            </div>
          ) : (
            <>
              {/* Headline Stat Panel */}
              <div className="p-6 rounded-2xl bg-gradient-to-br from-rose-950/20 via-slate-900 to-slate-950 border border-rose-500/35 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/5 rounded-full blur-3xl" />
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-rose-400 text-xs font-extrabold uppercase tracking-widest">
                    <ShieldCheck className="h-4.5 w-4.5" />
                    Early Risk Detection Delta
                  </div>
                  <h2 className="text-2xl md:text-3xl font-black text-slate-100 leading-tight">
                    SentinelGrid would have predicted this <span className="text-rose-500">{replayData?.predictive_lead_time_minutes || 493} minutes</span> earlier.
                  </h2>
                  <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
                    By correlating active permits, maintenance status, and gas vectors, our composite risk engine flags critical risk at <strong>Hour +10.0</strong> (155 minutes early). By running our linear time-series forecasting model on the rising CO readings, SentinelGrid predicts the threshold crossing at <strong>Hour +4.36</strong>—providing an early warning <strong>493 minutes</strong> before the final incident.
                  </p>
                </div>
                <div className="flex gap-4 shrink-0">
                  <div className="bg-amber-500/10 border border-amber-500/25 px-4 py-3 rounded-xl flex flex-col items-center min-w-[130px]">
                    <span className="text-3xl font-black text-amber-500">{replayData?.lead_time_minutes}m</span>
                    <span className="text-[9px] font-black uppercase text-slate-400 tracking-wider mt-1">Rule-Based Early</span>
                  </div>
                  <div className="bg-rose-500/10 border border-rose-500/25 px-4 py-3 rounded-xl flex flex-col items-center min-w-[130px]">
                    <span className="text-3xl font-black text-rose-500">{replayData?.predictive_lead_time_minutes || 493}m</span>
                    <span className="text-[9px] font-black uppercase text-slate-400 tracking-wider mt-1">Predictive Early</span>
                  </div>
                </div>
              </div>

              {/* Horizontal Scrollable Timeline Tracks */}
              <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 shadow-xl space-y-6">
                <div>
                  <h3 className="text-sm font-extrabold text-slate-300 uppercase tracking-widest flex items-center gap-1.5">
                    <Clock className="h-4.5 w-4.5 text-cyan-400" />
                    Chronological Replay Timeline
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Scroll horizontally to follow the sequence of events and safety alerts.
                  </p>
                </div>

                <div className="flex overflow-x-auto gap-6 pb-6 pt-4 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
                  {replayData?.events.map((ev, index) => {
                    const isSentinel = ev.type === "sentinelgrid";
                    const formattedTime = new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    
                    return (
                      <div 
                        key={index}
                        className={`w-80 shrink-0 p-4 rounded-xl border flex flex-col justify-between h-[230px] transition-all duration-300 relative group ${
                          isSentinel
                            ? "bg-rose-950/5 border-rose-500/20 hover:border-rose-500/40 hover:bg-rose-950/10 shadow-lg shadow-rose-950/5"
                            : "bg-slate-950/40 border-slate-850 hover:border-slate-750 hover:bg-slate-900/30"
                        }`}
                      >
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-[10px] font-mono text-cyan-400 font-bold bg-cyan-950/30 border border-cyan-900/30 px-1.5 py-0.5 rounded">
                              Hour +{ev.offset_hours} ({formattedTime})
                            </span>
                            <span className={`text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded ${
                              isSentinel
                                ? "text-rose-400 bg-rose-500/10 border border-rose-500/20"
                                : "text-slate-400 bg-slate-800 border border-slate-700"
                            }`}>
                              {isSentinel ? "SentinelGrid Flag" : "Actual History"}
                            </span>
                          </div>
                          
                          <h4 className="text-xs font-black text-slate-200 uppercase line-clamp-1">{ev.title}</h4>
                          <p className="text-[11px] text-slate-400 mt-2 leading-relaxed line-clamp-5">
                            {ev.description}
                          </p>
                        </div>

                        {isSentinel && (
                          <div className="flex items-center justify-between border-t border-rose-500/10 pt-2.5 mt-2 text-[10px]">
                            <span className="text-rose-400 font-extrabold uppercase">Risk Score: {ev.risk_score}</span>
                            <span className="text-slate-500 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-850 font-mono">Tier {ev.tier}</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Disclaimer */}
              <div className="p-4 bg-slate-900/20 border border-slate-850 rounded-xl text-center">
                <p className="text-[11px] text-slate-500 font-medium italic">
                  * Reconstructed for demonstration purposes based on public incident reporting. Not verified internal plant data.
                </p>
              </div>
            </>
          )}
        </div>
      )}

      {/* MITIGATION SANDBOX VIEW */}
      {activeTab === "sandbox" && (
        loading ? (
          <div className="flex flex-col items-center justify-center py-32 text-slate-400 animate-pulse">
            <Loader2 className="h-10 w-10 animate-spin text-emerald-400 mb-3" />
            <span>Loading simulation dashboard parameters...</span>
          </div>
        ) : !originalAssessment || error ? (
          <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-2xl max-w-lg mx-auto">
            <XCircle className="h-12 w-12 text-rose-500 mx-auto mb-4" />
            <h3 className="text-lg font-bold text-slate-200">Simulation Data Offline</h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              {error || "Unable to retrieve simulation settings. Please ensure python backend is running."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Controls Panel */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-6">
            <div>
              <h2 className="text-lg font-bold text-slate-200 mb-1 flex items-center gap-2">
                <Sliders className="h-5 w-5 text-emerald-400" />
                Interventions Control
              </h2>
              <p className="text-xs text-slate-400">
                Select a dataset/scenario, then toggle active factors to recalculate risk.
              </p>
            </div>

            {/* Scenario Preset dropdown */}
            <div className="space-y-2">
              <label className="text-[10px] font-black uppercase text-slate-500 tracking-wider">Active Scenario</label>
              <select
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value)}
                className="w-full bg-slate-950 border border-slate-850 text-xs text-slate-300 p-2.5 rounded-lg focus:outline-none focus:border-emerald-500"
              >
                {Object.entries(scenarioPresets).map(([key, p]) => (
                  <option key={key} value={key}>{p.name}</option>
                ))}
              </select>
            </div>

            {/* Permits Toggle */}
            <div className="space-y-3">
              <h3 className="text-xs font-black uppercase tracking-widest text-slate-500 flex items-center gap-1.5">
                <FileText className="h-4 w-4 text-blue-400" />
                Toggle Permits (Work Suspended)
              </h3>
              {loading ? (
                <div className="text-xs text-slate-500 italic py-2">Loading permits...</div>
              ) : telemetry?.permits.length === 0 ? (
                <div className="text-xs text-slate-500 italic py-2">No active permits in this window.</div>
              ) : (
                <div className="space-y-2">
                  {telemetry?.permits.map(permit => {
                    const isExcluded = excludedPermitIds.includes(permit.permit_id);
                    return (
                      <button
                        key={permit.permit_id}
                        onClick={() => togglePermitExclusion(permit.permit_id)}
                        className={`w-full p-3 rounded-xl border text-left flex items-center justify-between transition-all cursor-pointer ${
                          isExcluded
                            ? "bg-rose-950/10 border-rose-500/30 text-rose-300"
                            : "bg-slate-950/40 border-slate-800 text-slate-300 hover:border-slate-700"
                        }`}
                      >
                        <div className="space-y-0.5">
                          <div className="text-xs font-bold font-mono">{permit.permit_id}</div>
                          <div className="text-[10px] text-slate-500">
                            {permit.permit_type} in {permit.zone}
                          </div>
                        </div>
                        {isExcluded ? (
                          <div className="flex items-center gap-1 text-[10px] font-black uppercase text-rose-500">
                            Suspended
                            <ToggleLeft className="h-6 w-6" />
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 text-[10px] font-black uppercase text-emerald-500">
                            Active
                            <ToggleRight className="h-6 w-6" />
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Maintenance Toggle */}
            <div className="space-y-3">
              <h3 className="text-xs font-black uppercase tracking-widest text-slate-500 flex items-center gap-1.5">
                <Wrench className="h-4 w-4 text-rose-400" />
                Toggle Maintenance (Task Completed)
              </h3>
              {loading ? (
                <div className="text-xs text-slate-500 italic py-2">Loading logs...</div>
              ) : telemetry?.maintenance_logs.length === 0 ? (
                <div className="text-xs text-slate-500 italic py-2">No maintenance events in this window.</div>
              ) : (
                <div className="space-y-2">
                  {telemetry?.maintenance_logs.map(log => {
                    const isExcluded = excludedMaintIds.includes(log.id);
                    return (
                      <button
                        key={log.id}
                        onClick={() => toggleMaintExclusion(log.id)}
                        className={`w-full p-3 rounded-xl border text-left flex items-center justify-between transition-all cursor-pointer ${
                          isExcluded
                            ? "bg-emerald-950/10 border-emerald-500/30 text-emerald-300"
                            : "bg-slate-950/40 border-slate-800 text-slate-300 hover:border-slate-700"
                        }`}
                      >
                        <div className="space-y-0.5 pr-2 flex-1">
                          <div className="text-xs font-bold font-mono">{log.equipment_id}</div>
                          <div className="text-[10px] text-slate-400 line-clamp-1">{log.notes}</div>
                        </div>
                        {isExcluded ? (
                          <div className="flex items-center gap-1 text-[10px] font-black uppercase text-emerald-500 shrink-0">
                            Resolved
                            <ToggleLeft className="h-6 w-6" />
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 text-[10px] font-black uppercase text-rose-500 shrink-0">
                            Overdue
                            <ToggleRight className="h-6 w-6" />
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Results Side-by-Side Panel */}
          <div className="lg:col-span-2 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Original Assessment Card */}
              <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl flex flex-col justify-between h-[360px]">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xs font-black uppercase tracking-widest text-slate-500">Original State</h3>
                    <span className="text-[10px] font-bold text-slate-400 bg-slate-850 px-2 py-0.5 rounded border border-slate-800">UNMITIGATED</span>
                  </div>
                  
                  <div className="flex flex-col items-center py-6">
                    <span className="text-6xl font-black tracking-tight text-rose-500">
                      {originalAssessment?.score}
                    </span>
                    <span className="text-xs font-semibold uppercase tracking-widest text-slate-400 mt-2">
                      {originalAssessment?.tier_name}
                    </span>
                  </div>

                  <div className="space-y-2 max-h-[140px] overflow-y-auto mt-2">
                    <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-500 block">Triggered Anomalies:</span>
                    {originalAssessment?.triggered_rules.map((r, i) => (
                      <div key={i} className="text-xs text-slate-300 flex items-center gap-1.5">
                        <AlertTriangle className="h-3.5 w-3.5 text-rose-500 shrink-0" />
                        <span className="font-mono text-[10px]">{r.rule_name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Counterfactual Simulation Card */}
              <div className={`p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border-2 shadow-xl flex flex-col justify-between h-[360px] transition-all duration-300 relative overflow-hidden ${
                simulatedAssessment ? simulatedAssessment.score >= 75 ? "border-rose-500/60" : simulatedAssessment.score >= 40 ? "border-amber-500/60" : "border-emerald-500/60" : "border-slate-800"
              }`}>
                {simulating && (
                  <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm flex flex-col items-center justify-center z-10">
                    <Loader2 className="h-8 w-8 animate-spin text-cyan-400 mb-2" />
                    <span className="text-xs text-slate-300 font-semibold">Recalculating vectors...</span>
                  </div>
                )}
                
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xs font-black uppercase tracking-widest text-slate-400">Simulated State</h3>
                    <span className="text-[10px] font-black text-cyan-400 bg-cyan-950/30 px-2 py-0.5 rounded border border-cyan-500/30 animate-pulse">RECALCULATED</span>
                  </div>
                  
                  <div className="flex flex-col items-center py-6">
                    <span className={`text-6xl font-black tracking-tight transition-all duration-300 ${
                      simulatedAssessment 
                        ? simulatedAssessment.score >= 75 ? "text-rose-500" : simulatedAssessment.score >= 40 ? "text-amber-500" : "text-emerald-400"
                        : "text-slate-500"
                    }`}>
                      {simulatedAssessment?.score}
                    </span>
                    <span className="text-xs font-semibold uppercase tracking-widest text-slate-400 mt-2">
                      {simulatedAssessment?.tier_name}
                    </span>
                  </div>

                  <div className="space-y-2 max-h-[140px] overflow-y-auto mt-2">
                    <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-500 block">Active Simulated Violations:</span>
                    {!simulatedAssessment || simulatedAssessment.triggered_rules.length === 0 ? (
                      <div className="text-xs text-emerald-400 font-bold flex items-center gap-1.5 py-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                        Risk Mitigated. Scenario is Safe!
                      </div>
                    ) : (
                      simulatedAssessment.triggered_rules.map((r, i) => (
                        <div key={i} className="text-xs text-slate-300 flex items-center gap-1.5">
                          <AlertTriangle className={`h-3.5 w-3.5 shrink-0 ${
                            r.severity === 3 ? "text-rose-500" : "text-amber-500"
                          }`} />
                          <span className="font-mono text-[10px]">{r.rule_name}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

            </div>

            {/* Simulated Delta Summary */}
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center gap-3">
              <ShieldCheck className="h-8 w-8 text-cyan-400 shrink-0" />
              <div>
                <h4 className="text-xs font-bold text-slate-200">Simulation Delta Summary</h4>
                <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                  {simulatedAssessment && originalAssessment ? (
                    simulatedAssessment.score < originalAssessment.score ? (
                      `Excluding selected risk variables reduced the safety risk score from ${originalAssessment.score} to ${simulatedAssessment.score} (${originalAssessment.score - simulatedAssessment.score} points drop).`
                    ) : (
                      "Toggling controls will recalculate threat correlation. No variables excluded yet."
                    )
                  ) : "Awaiting recalculation..."}
                </p>
              </div>
            </div>
          </div>

          </div>
        )
      )}
    </div>
  );
}
