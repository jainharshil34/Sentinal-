"use client";

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import axios from "axios";
import { RiskHeatmap, HeatmapLegend } from "@/components/RiskHeatmap";
import { 
  Activity, 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  RefreshCw, 
  ShieldCheck,
  Flame,
  FileText,
  Wrench,
  AlertTriangle,
  Server,
  Info,
  Thermometer,
  ShieldAlert,
  Sparkles,
  Award,
  Database,
  Radio,
  Brain,
  Download
} from "lucide-react";
import { AlertExplainabilityChart } from "@/components/AlertExplainabilityChart";

const ZONE_CENTERS: Record<string, { x: number; y: number }> = {
  "Zone-A": { x: 140, y: 110 },
  "Zone-B": { x: 140, y: 290 },
  "Zone-C": { x: 397, y: 110 },
  "Zone-D": { x: 397, y: 290 },
  "Zone-E": { x: 655, y: 110 },
  "Zone-F": { x: 655, y: 290 }
};

const ADJACENCY_MAP: Record<string, string[]> = {
  "Zone-A": ["Zone-A", "Zone-B"],
  "Zone-B": ["Zone-B", "Zone-A", "Zone-C"],
  "Zone-C": ["Zone-C", "Zone-B", "Zone-D"],
  "Zone-D": ["Zone-D", "Zone-C", "Zone-E"],
  "Zone-E": ["Zone-E", "Zone-D", "Zone-F"],
  "Zone-F": ["Zone-F", "Zone-E"]
};

interface GasReading {
  id: number;
  zone: string;
  timestamp: string;
  gas_type: string;
  reading_ppm: number;
  sensor_status: string;
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
  flag_id?: string;
  rule_name: string;
  severity: number;
  reason: string;
  contributing_signals: any[];
  predicted_confidence?: number;
  past_similar_flags_count?: number;
}

interface WatchFlag {
  zone: string;
  signal_type: string;
  current_value: number;
  threshold: number;
  trend: string;
  predicted_threshold_breach_minutes?: number | null;
  confidence_interval?: number | null;
  message?: string | null;
}

interface ConfirmationLogEntry {
  confirmed_at: string;
  confirmed_by_role: string;
  flag_id: string;
}

interface AlarmState {
  local_alerts_active: string[];
  acknowledged_local_alerts: string[];
  facility_evacuation_active: boolean;
  last_triggered_by_flag_id: string | null;
  confirmation_log: ConfirmationLogEntry[];
}

interface RiskAssessment {
  score: number;
  tier: number;
  tier_name: string;
  triggered_rules: TriggeredRule[];
  contributing_signals: any[];
  resolved_window_start?: string;
  resolved_window_end?: string;
  resolved_dataset?: string;
  active_scenario?: string;
  watch_flags?: WatchFlag[];
  related_incidents?: any[];
  deployment_mode?: string;
  alarm_state?: AlarmState;
}

interface Worker {
  id: number;
  name: string;
  role: string;
  zone: string;
  x: number;
  y: number;
  last_update: string;
}

interface TelemetrySummary {
  gas_readings: GasReading[];
  permits: Permit[];
  maintenance_logs: MaintenanceLog[];
}

interface EvidencePacket {
  summary: string;
  rules_fired: string[];
  applicable_clause: string;
  clause_relation: string;
}

interface NarrationResponse {
  explanation: string;
  evidence_packet: EvidencePacket | null;
}

let audioCtx: any = null;
let activeOscillators: { stop: () => void }[] = [];

function playLocalAlarm() {
  if (typeof window === "undefined") return;
  try {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) return;
    if (!audioCtx) audioCtx = new AudioContextClass();
    if (audioCtx.state === "suspended") {
      audioCtx.resume();
    }
    
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    
    osc.type = "sine";
    osc.frequency.setValueAtTime(440, audioCtx.currentTime);
    
    const lfo = audioCtx.createOscillator();
    lfo.frequency.value = 2.0;
    const lfoGain = audioCtx.createGain();
    lfoGain.gain.value = 150;
    
    lfo.connect(lfoGain);
    lfoGain.connect(osc.frequency);
    
    gain.gain.setValueAtTime(0.06, audioCtx.currentTime);
    
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    
    osc.start();
    lfo.start();
    
    const alarmInstance = {
      stop: () => {
        try {
          osc.stop();
          lfo.stop();
          osc.disconnect();
          lfo.disconnect();
          gain.disconnect();
        } catch (e) {}
      }
    };
    activeOscillators.push(alarmInstance);
    return alarmInstance;
  } catch (e) {
    console.error("Web Audio API failed to initialize alarm tone", e);
  }
}

function playFacilityAlarm() {
  if (typeof window === "undefined") return;
  try {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) return;
    if (!audioCtx) audioCtx = new AudioContextClass();
    if (audioCtx.state === "suspended") {
      audioCtx.resume();
    }
    
    const osc1 = audioCtx.createOscillator();
    const osc2 = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    
    osc1.type = "sawtooth";
    osc1.frequency.value = 220;
    osc2.type = "sawtooth";
    osc2.frequency.value = 222;
    
    const volumeLfo = audioCtx.createOscillator();
    volumeLfo.frequency.value = 1.5;
    const lfoGain = audioCtx.createGain();
    lfoGain.gain.value = 0.08;
    
    volumeLfo.connect(lfoGain);
    lfoGain.connect(gain.gain);
    
    gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
    
    osc1.connect(gain);
    osc2.connect(gain);
    gain.connect(audioCtx.destination);
    
    osc1.start();
    osc2.start();
    volumeLfo.start();
    
    const alarmInstance = {
      stop: () => {
        try {
          osc1.stop();
          osc2.stop();
          volumeLfo.stop();
          osc1.disconnect();
          osc2.disconnect();
          volumeLfo.disconnect();
          gain.disconnect();
        } catch (e) {}
      }
    };
    activeOscillators.push(alarmInstance);
    return alarmInstance;
  } catch (e) {
    console.error("Web Audio API failed to initialize facility alarm tone", e);
  }
}

function stopAllAlarms() {
  activeOscillators.forEach(osc => osc.stop());
  activeOscillators = [];
}

export default function Dashboard() {
  // Active Injected Scenario
  const [activeScenario, setActiveScenario] = useState<string>("normal");
  
  // Active Plant Selection
  const [activePlant, setActivePlant] = useState<string>("Plant-A");

  // API Data States
  const [riskAssessment, setRiskAssessment] = useState<RiskAssessment | null>(null);
  const [alarmState, setAlarmState] = useState<AlarmState | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetrySummary | null>(null);
  
  // Workers State
  const [workers, setWorkers] = useState<Worker[]>([]);
  
  // Narration States
  const [narration, setNarration] = useState<NarrationResponse | null>(null);
  const [narrating, setNarrating] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(true);
  const [injecting, setInjecting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [emergencyProtocol, setEmergencyProtocol] = useState<any>(null);
  
  // Safety Officer Verdict Feedback State
  const [feedbackStatus, setFeedbackStatus] = useState<Record<string, string>>({});

  // Active Plant Deployment Mode State (shadow or live)
  const [deploymentMode, setDeploymentMode] = useState<string>("shadow");


  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const submitFeedback = async (flagId: string | undefined, ruleName: string, verdict: string) => {
    if (!flagId) return;
    try {
      await axios.post(`${apiUrl}/api/feedback/${flagId}`, {
        rule_name: ruleName,
        verdict: verdict
      });
      setFeedbackStatus(prev => ({ ...prev, [flagId]: verdict }));
      // Reload status to reflect adjusted risk score and tier immediately
      fetchLiveStatus(false);
    } catch (err) {
      console.error("Failed to submit safety officer verdict", err);
    }
  };

  // Sync activePlant with URL parameters
  useEffect(() => {
    const syncPlant = () => {
      if (typeof window !== "undefined") {
        const params = new URLSearchParams(window.location.search);
        const pId = params.get("plant_id");
        if (pId && ["Plant-A", "Plant-B", "Plant-C"].includes(pId)) {
          setActivePlant(pId);
        }
      }
    };
    syncPlant();
    window.addEventListener("popstate", syncPlant);
    return () => window.removeEventListener("popstate", syncPlant);
  }, []);

  const scenarioPresets: Record<string, { name: string; desc: string }> = {
    normal: {
      name: "Normal Operations",
      desc: "Routine plant activity under safe, baseline environmental conditions."
    },
    scenario_1: {
      name: "S1: Hot Work + Methane (Zone-A)",
      desc: "High methane risk, active hot work permit, and overdue ventilation check."
    },
    scenario_2: {
      name: "S2: Confined Space + CO (Zone-B)",
      desc: "Dangerous CO build-up in restricted space with overdue sensor calibration."
    },
    scenario_3: {
      name: "S3: Hot Work + H2S + Repair (Zone-C)",
      desc: "Toxic and explosive H2S leak in Zone-C with active repair overlap."
    },
    scenario_4: {
      name: "S4: Electrical + Methane (Zone-D)",
      desc: "Electrical sparks near methane accumulation and overdue breaker isolation."
    },
    silent_failure: {
      name: "S5: Telemetry Offline (Zone-E)",
      desc: "Sensor goes silent during active confined space permit, masking telemetry."
    },
    vizag_buildup: {
      name: "Vizag: Replay Buildup (Zone-C)",
      desc: "CO buildup with hot work and overdue regulator calibration reconstructed from Vizag."
    },
    multi_gas_toxicity: {
      name: "S6: Multi-Gas Toxicity (Zone-F)",
      desc: "Simultaneous sub-threshold CO & H2S levels in Zone-F with no active permits (toxicological compound risk)."
    }
  };

  // Main data fetch function (queries backend dynamically based on currently injected scenario)
  const fetchLiveStatus = async (showSpinner = false) => {
    if (showSpinner) setLoading(true);
    try {
      // 1. Fetch risk assessment (let backend resolve window dynamically)
      const riskRes = await axios.get<RiskAssessment>(`${apiUrl}/api/risk-assessment`, {
        params: { plant_id: activePlant }
      });
      setRiskAssessment(riskRes.data);
      if (riskRes.data.alarm_state) {
        setAlarmState(riskRes.data.alarm_state);
      } else {
        setAlarmState(null);
      }
      if (riskRes.data.active_scenario) {
        setActiveScenario(riskRes.data.active_scenario);
      }
      if (riskRes.data.deployment_mode) {
        setDeploymentMode(riskRes.data.deployment_mode);
      }

      // 2. Fetch telemetry summary aligned with the same dynamically resolved window
      const telemetryRes = await axios.get<TelemetrySummary>(`${apiUrl}/api/telemetry-summary`, {
        params: { plant_id: activePlant }
      });
      setTelemetry(telemetryRes.data);

      // 3. Fetch worker positions
      const workersRes = await axios.get<Worker[]>(`${apiUrl}/api/worker-positions`);
      setWorkers(workersRes.data);

      setError(null);
    } catch (err: any) {
      console.error("Failed to load plant status", err);
      setError("Failed to reach plant backend. Ensure python backend server is running.");
    } finally {
      if (showSpinner) setLoading(false);
    }
  };

  // Poll safety assessments every 5 seconds or when activePlant changes
  useEffect(() => {
    // Initial fetch
    fetchLiveStatus(true);

    const interval = setInterval(() => {
      fetchLiveStatus(false);
    }, 5000);

    return () => clearInterval(interval);
  }, [activePlant]);

  // Fetch narration when riskAssessment changes
  useEffect(() => {
    if (!riskAssessment) {
      setNarration(null);
      return;
    }

    const fetchNarration = async () => {
      setNarrating(true);
      try {
        const res = await axios.post<NarrationResponse>(`${apiUrl}/api/narrate`, riskAssessment);
        setNarration(res.data);
      } catch (err) {
        console.error("Failed to fetch LLM safety narration", err);
        setNarration(null);
      } finally {
        setNarrating(false);
      }
    };

    fetchNarration();
  }, [riskAssessment]);

  // Poll emergency response protocol state when in Tier 3
  useEffect(() => {
    if (!riskAssessment || riskAssessment.tier !== 3) {
      setEmergencyProtocol(null);
      return;
    }
    
    // Find active zone
    const activeZone = riskAssessment.triggered_rules.find(r => r.severity === 3)
      ? ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F"].find(z => 
          riskAssessment.triggered_rules.some(r => r.severity === 3 && r.reason.includes(z))
        )
      : null;
      
    if (!activeZone) {
      setEmergencyProtocol(null);
      return;
    }
    
    const fetchEmergencyState = async () => {
      try {
        const res = await axios.get(`${apiUrl}/api/emergency-response/${activeZone}`, {
          params: { plant_id: activePlant }
        });
        setEmergencyProtocol(res.data);
      } catch (err) {
        console.error("Failed to fetch emergency response state", err);
      }
    };
    
    // Initial fetch
    fetchEmergencyState();
    
    const interval = setInterval(fetchEmergencyState, 1000);
    return () => clearInterval(interval);
  }, [riskAssessment, activeScenario]);

  // Synchronize warning alarm audio oscillators with current alarm state
  useEffect(() => {
    if (!alarmState) {
      stopAllAlarms();
      return;
    }
    
    stopAllAlarms();
    
    if (alarmState.facility_evacuation_active) {
      playFacilityAlarm();
    } else if (alarmState.local_alerts_active.length > 0) {
      playLocalAlarm();
    }
    
    return () => stopAllAlarms();
  }, [alarmState?.facility_evacuation_active, alarmState?.local_alerts_active.join(",")]);

  const handleAcknowledgeLocal = async (zone: string) => {
    try {
      const res = await axios.post(`${apiUrl}/api/alarm-state/acknowledge-local`, {
        zone: zone,
        plant_id: activePlant
      });
      setAlarmState(res.data.alarm_state);
    } catch (err) {
      console.error("Failed to acknowledge local zone alarm", err);
    }
  };

  const handleConfirmEvacuation = async (flagId: string) => {
    try {
      const res = await axios.post(`${apiUrl}/api/alarm-state/confirm-evacuation`, {
        flag_id: flagId,
        confirmed_by_role: "Safety Officer",
        plant_id: activePlant
      });
      setAlarmState(res.data.alarm_state);
      fetchLiveStatus(false);
    } catch (err) {
      console.error("Failed to confirm facility evacuation", err);
    }
  };

  const handleDownloadPdf = (zoneName: string) => {
    const pdfUrl = `${apiUrl}/api/emergency-response/${zoneName}/report-pdf?plant_id=${activePlant}`;
    window.open(pdfUrl, "_blank");
  };

  // Inject test scenario
  const handleInjectScenario = async (scenarioKey: string) => {
    setInjecting(true);
    try {
      await axios.post(`${apiUrl}/api/simulation/inject?scenario=${scenarioKey}`);
      setActiveScenario(scenarioKey);
      // Immediately refresh dashboard to show updated state instantly
      await fetchLiveStatus(true);
    } catch (err) {
      console.error("Failed to inject scenario", err);
      setError("Failed to inject test scenario.");
    } finally {
      setInjecting(false);
    }
  };

  // Helper to determine safety tier for a specific zone based on active triggered rules and watch flags
  const getZoneStatus = useCallback((zoneName: string): { tier: number; colorClass: string; strokeClass: string; fillClass: string; isCascaded: boolean } => {
    if (alarmState?.facility_evacuation_active) {
      return { 
        tier: 3, 
        colorClass: "text-rose-500 font-bold font-black", 
        strokeClass: "stroke-rose-500 animate-[pulse_1s_infinite] stroke-[3px]", 
        fillClass: "fill-rose-500/30 hover:fill-rose-500/40",
        isCascaded: false 
      };
    }
    if (alarmState?.local_alerts_active?.includes(zoneName)) {
      return { 
        tier: 3, 
        colorClass: "text-rose-500 font-bold font-black animate-pulse", 
        strokeClass: "stroke-rose-600 animate-[pulse_1.2s_infinite] stroke-[3px]", 
        fillClass: "fill-rose-600/35 hover:fill-rose-600/45",
        isCascaded: false 
      };
    }

    if (!riskAssessment) return { tier: 1, colorClass: "text-emerald-400", strokeClass: "stroke-emerald-500/40", fillClass: "fill-emerald-500/10", isCascaded: false };
    
    // Check if any rule violations target this zone
    const zoneRules = riskAssessment.triggered_rules.filter(rule => 
      rule.reason.includes(zoneName) || 
      rule.contributing_signals.some((sig: any) => sig.zone === zoneName)
    );

    if (zoneRules.length === 0) {
      // Check if there are watch flags for this zone
      const zoneWatchFlags = (riskAssessment.watch_flags || []).filter(wf => wf.zone === zoneName);
      if (zoneWatchFlags.length > 0) {
        return {
          tier: 0,
          colorClass: "text-sky-400 font-bold",
          strokeClass: "stroke-sky-500 animate-[pulse_2s_infinite] stroke-2",
          fillClass: "fill-sky-500/10 hover:fill-sky-500/20",
          isCascaded: false
        };
      }
      return { 
        tier: 1, 
        colorClass: "text-emerald-400", 
        strokeClass: "stroke-emerald-500/40", 
        fillClass: "fill-emerald-500/10 hover:fill-emerald-500/20",
        isCascaded: false 
      };
    }

    const hasCascadeRule = zoneRules.some(rule => rule.rule_name === "RULE_ADJACENT_ZONE_ESCALATION");
    const maxSeverity = zoneRules.reduce((max, r) => Math.max(max, r.severity), 0);
    
    if (maxSeverity === 3) {
      return { 
        tier: 3, 
        colorClass: "text-rose-500 font-bold", 
        strokeClass: "stroke-rose-500 animate-pulse stroke-2", 
        fillClass: "fill-rose-500/20 hover:fill-rose-500/30",
        isCascaded: false 
      };
    } else if (hasCascadeRule) {
      return { 
        tier: 2, 
        colorClass: "text-sky-400 font-bold", 
        strokeClass: "stroke-sky-500 stroke-2 animate-[pulse_3s_infinite]", 
        fillClass: "fill-sky-500/5 hover:fill-sky-500/10",
        isCascaded: true
      };
    } else {
      return { 
        tier: 2, 
        colorClass: "text-amber-500 font-bold", 
        strokeClass: "stroke-amber-500 stroke-2", 
        fillClass: "fill-amber-500/20 hover:fill-amber-500/30",
        isCascaded: false 
      };
    }
  }, [alarmState, riskAssessment]);

  const getGlowScore = useCallback((zoneName: string): number => {
    const status = getZoneStatus(zoneName);
    let baseScore = 5;
    if (status.tier === 3) baseScore = 90;
    else if (status.tier === 2) baseScore = status.isCascaded ? 45 : 65;
    else if (status.tier === 0) baseScore = 25;
    
    // Check neighbors for higher tier
    const adjacentZones = ADJACENCY_MAP[zoneName] || [];
    let maxNeighborScore = 0;
    adjacentZones.forEach(neighbor => {
      if (neighbor !== zoneName) {
        const nStatus = getZoneStatus(neighbor);
        let nScore = 5;
        if (nStatus.tier === 3) nScore = 90;
        else if (nStatus.tier === 2) nScore = nStatus.isCascaded ? 45 : 65;
        else if (nStatus.tier === 0) nScore = 25;
        maxNeighborScore = Math.max(maxNeighborScore, nScore);
      }
    });
    
    // Return local score, or 50% of the highest neighbor score (simulating spatial bleed)
    return Math.max(baseScore, maxNeighborScore * 0.5);
  }, [getZoneStatus]);

  // Geospatial heatmap layer state & memoized heat sources
  const [heatmapLayer, setHeatmapLayer] = useState<"risk" | "workers" | "off">("risk");

  const heatSources = useMemo(() => {
    if (heatmapLayer === "risk") {
      return Object.keys(ZONE_CENTERS).map((zone) => {
        const center = ZONE_CENTERS[zone];
        const weight = getGlowScore(zone);
        return {
          id: zone,
          x: center.x,
          y: center.y,
          weight,
          sigma: 150
        };
      });
    } else if (heatmapLayer === "workers") {
      return workers.map((worker) => {
        const status = getZoneStatus(worker.zone);
        let weight = 15; // default low
        if (status.tier === 3) {
          weight = 95;
        } else if (status.tier === 2) {
          weight = 65; // tier 2: 55-70
        } else if (status.tier === 0) {
          weight = 30; // tier 0 watch
        }
        return {
          id: worker.id,
          x: worker.x,
          y: worker.y,
          weight,
          sigma: 70
        };
      });
    }
    return [];
  }, [heatmapLayer, workers, getGlowScore, getZoneStatus]);


  // Group latest gas readings per zone
  const getLatestReadingsPerZone = () => {
    if (!telemetry) return {};
    const map: Record<string, Record<string, number | string>> = {};
    telemetry.gas_readings.forEach(r => {
      if (!map[r.zone]) {
        map[r.zone] = {};
      }
      map[r.zone][r.gas_type] = r.sensor_status === "silent" ? "SILENT" : r.reading_ppm;
    });
    return map;
  };

  const zoneGasData = getLatestReadingsPerZone();

  // Color mappings based on score / safety tier
  const getTierDetails = (tier: number, score: number) => {
    if (tier === 3 || score >= 75) {
      return {
        bg: "from-rose-950/20 via-slate-900 to-slate-950",
        border: "border-rose-500/40",
        text: "text-rose-400",
        accent: "bg-rose-500",
        label: "Tier 3: Escalate / Safety Stop"
      };
    } else if (tier === 2 || (score >= 40 && score < 75)) {
      return {
        bg: "from-amber-950/20 via-slate-900 to-slate-950",
        border: "border-amber-500/40",
        text: "text-amber-400",
        accent: "bg-amber-500",
        label: "Tier 2: Active Safety Warning"
      };
    } else if (tier === 0) {
      return {
        bg: "from-sky-950/20 via-slate-900 to-slate-950",
        border: "border-sky-500/40",
        text: "text-sky-400",
        accent: "bg-sky-500",
        label: "Safety Watch: Proximity Trend Alert"
      };
    } else {
      return {
        bg: "from-emerald-950/20 via-slate-900 to-slate-950",
        border: "border-emerald-500/40",
        text: "text-emerald-400",
        accent: "bg-emerald-500",
        label: "Tier 1: Nominal Safe Operations"
      };
    }
  };

  const currentTier = riskAssessment ? getTierDetails(riskAssessment.tier, riskAssessment.score) : getTierDetails(1, 0);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">

      {/* Active Local Alarm Siren Banner */}
      {alarmState?.local_alerts_active && alarmState.local_alerts_active.length > 0 && (
        <div className="space-y-3">
          {alarmState.local_alerts_active.map((zone) => (
            <div 
              key={zone} 
              className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/35 flex items-center justify-between gap-4 animate-[pulse_1.5s_infinite]"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-rose-500 rounded-lg text-slate-950 animate-bounce">
                  <AlertTriangle className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-rose-550 uppercase tracking-wider">
                    LOCAL ALERT — {zone} — Tier 3 Compound Risk
                  </h3>
                  <p className="text-[11px] text-slate-400 font-medium">
                    Local gas/permit correlation has exceeded emergency safety envelope. Evacuation suggested.
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleAcknowledgeLocal(zone)}
                className="px-4 py-2 bg-rose-950 hover:bg-rose-900 border border-rose-500/30 hover:border-rose-500/50 text-rose-400 hover:text-rose-300 rounded-xl text-xs font-black uppercase tracking-wider transition-all cursor-pointer"
              >
                Mute / Acknowledge
              </button>
            </div>
          ))}
        </div>
      )}
      
      {/* Header and Live Connection Indicator */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
            <Radio className="h-8 w-8 text-emerald-500 animate-pulse" />
            Live Plant Status Dashboard
          </h1>
          <div className="mt-3 flex flex-wrap items-center gap-2 bg-slate-900/60 p-1 border border-slate-800/80 rounded-xl max-w-max">
            {["Plant-A", "Plant-B", "Plant-C"].map((pId) => (
              <button
                key={pId}
                onClick={() => {
                  setActivePlant(pId);
                  if (typeof window !== "undefined") {
                    const url = new URL(window.location.href);
                    url.searchParams.set("plant_id", pId);
                    window.history.pushState({}, "", url.toString());
                  }
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                  activePlant === pId
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                }`}
              >
                {pId === "Plant-A" ? "Plant-A (Methane)" : pId === "Plant-B" ? "Plant-B (Coke Oven)" : "Plant-C (Acid)"}
              </button>
            ))}
          </div>
          <p className="mt-2 text-sm text-slate-400">
            Real-time multi-system threat correlation monitoring 6 active plant sectors for <span className="text-white font-bold">{activePlant}</span>.
          </p>
        </div>

        {/* Polling/Connection Badge */}
        <div className="flex items-center gap-3 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800 shrink-0">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 bg-emerald-500 rounded-full animate-ping" />
            <span className="text-[10px] font-black uppercase text-slate-300 font-mono tracking-wider">
              Live Polling (5s)
            </span>
          </div>
          <span className="text-slate-700">|</span>
          <span className="text-[10px] text-slate-400 font-semibold font-mono uppercase bg-slate-950 px-2 py-0.5 rounded border border-slate-850">
            Active: {activeScenario.toUpperCase()}
          </span>
          <span className="text-slate-700">|</span>
          <span className={`text-[10px] font-black font-mono uppercase px-2 py-0.5 rounded border ${
            deploymentMode === "live"
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
              : "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse"
          }`}>
            {deploymentMode === "live" ? "Live Mode" : "Shadow Mode"}
          </span>
        </div>
      </div>

      {/* Scenario Injection Control Bar */}
      <div className="p-4 bg-slate-900/40 rounded-2xl border border-slate-800/80 space-y-3 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/5 rounded-full blur-3xl" />
        <div className="flex items-center gap-1.5">
          <Database className="h-4.5 w-4.5 text-cyan-400" />
          <span className="text-xs font-extrabold uppercase tracking-widest text-slate-400 block">
            Inject Test Scenario (Simulation Fast-Forward)
          </span>
        </div>
        <div className="flex flex-wrap gap-2.5">
          {Object.entries(scenarioPresets).map(([key, preset]) => (
            <button
              key={key}
              onClick={() => handleInjectScenario(key)}
              disabled={injecting}
              className={`px-3 py-2 text-xs font-semibold rounded-lg border transition-all cursor-pointer flex items-center gap-1.5 ${
                activeScenario === key
                  ? "bg-cyan-500/25 text-white border-cyan-500/50 shadow-lg shadow-slate-950 font-bold"
                  : "bg-slate-950/40 text-slate-400 border-slate-800 hover:border-slate-700 hover:text-slate-200"
              }`}
            >
              {injecting && activeScenario === key && (
                <Loader2 className="h-3 w-3 animate-spin text-cyan-400" />
              )}
              {preset.name}
            </button>
          ))}
        </div>
        <p className="text-[11px] text-slate-400 flex items-center gap-1.5 bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/50">
          <Info className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
          <span>
            {scenarioPresets[activeScenario]?.desc}
          </span>
        </p>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-sm font-semibold flex items-center gap-2">
          <XCircle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-32 text-slate-400">
          <Loader2 className="h-10 w-10 animate-spin text-emerald-400 mb-3" />
          <span>Compiling live safety matrix indices...</span>
        </div>
      ) : !riskAssessment ? (
        <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-2xl max-w-lg mx-auto">
          <XCircle className="h-12 w-12 text-rose-500 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-slate-200">Refinery Safety Systems Offline</h3>
          <p className="text-xs text-slate-400 mt-2 leading-relaxed">
            Unable to communicate with the SentinelGrid risk engine. Please ensure the Python backend server is running and the database is seeded.
          </p>
        </div>
      ) : (
        <>
          {/* Main Grid: SVG Floor Plan and Risk Gauge */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* SVG Interactive Floor Plan Map */}
            <div className="lg:col-span-2 p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-850 shadow-xl space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-200 mb-1 flex items-center gap-2">
                    <Thermometer className="h-5 w-5 text-emerald-400" />
                    Geospatial Risk Heatmap
                  </h2>
                  <p className="text-xs text-slate-400">
                    {heatmapLayer === "risk"
                      ? "Showing real-time continuous safety risk field interpolated across zones."
                      : heatmapLayer === "workers"
                      ? "Showing human exposure density risk mapped from worker locations."
                      : "Continuous geospatial heatmap is turned off."}
                  </p>
                </div>

                {/* Heatmap Layer Selector */}
                <div className="flex items-center bg-slate-950/80 p-1 rounded-lg border border-slate-800 self-start sm:self-center">
                  <button
                    onClick={() => setHeatmapLayer("risk")}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                      heatmapLayer === "risk"
                        ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                        : "text-slate-400 hover:text-slate-200 border border-transparent"
                    }`}
                  >
                    Risk Field
                  </button>
                  <button
                    onClick={() => setHeatmapLayer("workers")}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                      heatmapLayer === "workers"
                        ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30"
                        : "text-slate-400 hover:text-slate-200 border border-transparent"
                    }`}
                  >
                    Worker Exposure
                  </button>
                  <button
                    onClick={() => setHeatmapLayer("off")}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                      heatmapLayer === "off"
                        ? "bg-slate-800/80 text-slate-350 border border-slate-700/50"
                        : "text-slate-400 hover:text-slate-200 border border-transparent"
                    }`}
                  >
                    Off
                  </button>
                </div>
              </div>

              {heatmapLayer !== "off" && (
                <div className="flex items-center gap-4 py-1.5 border-t border-slate-800/40">
                  <HeatmapLegend />
                </div>
              )}

              {/* Plant Map SVG Layout */}
              <div className="relative w-full overflow-hidden rounded-xl border border-slate-850 bg-slate-950">
                {/* Continuous Heatmap Backdrop */}
                {heatmapLayer !== "off" && (
                  <RiskHeatmap sources={heatSources} width={800} height={400} showContours={true} />
                )}

                <svg viewBox="0 0 800 400" className="relative z-10 w-full h-auto bg-transparent">

                  {/* Walkways / Roads grid in refinery floor */}
                  <line x1="260" y1="30" x2="260" y2="370" className="stroke-slate-800/60" strokeWidth="12" strokeDasharray="6 4" />
                  <line x1="535" y1="30" x2="535" y2="370" className="stroke-slate-800/60" strokeWidth="12" strokeDasharray="6 4" />
                  <line x1="30" y1="200" x2="770" y2="200" className="stroke-slate-800/60" strokeWidth="12" strokeDasharray="6 4" />

                  {/* ZONE A */}
                  <g className="cursor-pointer">
                    <rect x="40" y="40" width="200" height="140" rx="8" className={`transition-all duration-500 ${getZoneStatus("Zone-A").strokeClass} ${getZoneStatus("Zone-A").fillClass}`} strokeWidth="2.5" strokeDasharray={getZoneStatus("Zone-A").isCascaded ? "6 4" : undefined} />
                    <text x="60" y="70" className="fill-white font-extrabold text-sm tracking-wider">ZONE-A</text>
                    {getZoneStatus("Zone-A").isCascaded && (
                      <text x="170" y="70" className="fill-sky-400 font-black text-[8px] tracking-wider animate-pulse font-mono">⚡ CASCADE</text>
                    )}
                    <text x="60" y="90" className="fill-slate-500 font-bold text-[9px] uppercase tracking-widest">Ventilation Hub</text>
                    <text x="60" y="125" className="fill-slate-300 font-mono text-[10px]">
                      CH4: {zoneGasData["Zone-A"]?.["CH4"] !== undefined ? `${zoneGasData["Zone-A"]["CH4"]} ppm` : "N/A"}
                    </text>
                    <text x="60" y="145" className="fill-slate-350 font-mono text-[10px]">
                      H2S: {zoneGasData["Zone-A"]?.["H2S"] !== undefined ? `${zoneGasData["Zone-A"]["H2S"]} ppm` : "N/A"}
                    </text>
                  </g>

                  {/* ZONE B */}
                  <g className="cursor-pointer">
                    <rect x="40" y="220" width="200" height="140" rx="8" className={`transition-all duration-500 ${getZoneStatus("Zone-B").strokeClass} ${getZoneStatus("Zone-B").fillClass}`} strokeWidth="2.5" strokeDasharray={getZoneStatus("Zone-B").isCascaded ? "6 4" : undefined} />
                    <text x="60" y="250" className="fill-white font-extrabold text-sm tracking-wider">ZONE-B</text>
                    {getZoneStatus("Zone-B").isCascaded && (
                      <text x="170" y="250" className="fill-sky-400 font-black text-[8px] tracking-wider animate-pulse font-mono">⚡ CASCADE</text>
                    )}
                    <text x="60" y="270" className="fill-slate-500 font-bold text-[9px] uppercase tracking-widest">Confined Storage</text>
                    <text x="60" y="305" className="fill-slate-300 font-mono text-[10px]">
                      CO: {zoneGasData["Zone-B"]?.["CO"] !== undefined ? `${zoneGasData["Zone-B"]["CO"]} ppm` : "N/A"}
                    </text>
                    <text x="60" y="325" className="fill-slate-350 font-mono text-[10px]">
                      CH4: {zoneGasData["Zone-B"]?.["CH4"] !== undefined ? `${zoneGasData["Zone-B"]["CH4"]} ppm` : "N/A"}
                    </text>
                  </g>

                  {/* ZONE C */}
                  <g className="cursor-pointer">
                    <rect x="280" y="40" width="235" height="140" rx="8" className={`transition-all duration-500 ${getZoneStatus("Zone-C").strokeClass} ${getZoneStatus("Zone-C").fillClass}`} strokeWidth="2.5" strokeDasharray={getZoneStatus("Zone-C").isCascaded ? "6 4" : undefined} />
                    <text x="300" y="70" className="fill-white font-extrabold text-sm tracking-wider">ZONE-C</text>
                    {getZoneStatus("Zone-C").isCascaded && (
                      <text x="440" y="70" className="fill-sky-400 font-black text-[8px] tracking-wider animate-pulse font-mono">⚡ CASCADE</text>
                    )}
                    <text x="300" y="90" className="fill-slate-500 font-bold text-[9px] uppercase tracking-widest">Acid Gas Valve</text>
                    <text x="300" y="125" className="fill-slate-300 font-mono text-[10px]">
                      H2S: {zoneGasData["Zone-C"]?.["H2S"] !== undefined ? `${zoneGasData["Zone-C"]["H2S"]} ppm` : "N/A"}
                    </text>
                    <text x="300" y="145" className="fill-slate-350 font-mono text-[10px]">
                      CO: {zoneGasData["Zone-C"]?.["CO"] !== undefined ? `${zoneGasData["Zone-C"]["CO"]} ppm` : "N/A"}
                    </text>
                  </g>

                  {/* ZONE D */}
                  <g className="cursor-pointer">
                    <rect x="280" y="220" width="235" height="140" rx="8" className={`transition-all duration-500 ${getZoneStatus("Zone-D").strokeClass} ${getZoneStatus("Zone-D").fillClass}`} strokeWidth="2.5" strokeDasharray={getZoneStatus("Zone-D").isCascaded ? "6 4" : undefined} />
                    <text x="300" y="250" className="fill-white font-extrabold text-sm tracking-wider">ZONE-D</text>
                    {getZoneStatus("Zone-D").isCascaded && (
                      <text x="440" y="250" className="fill-sky-400 font-black text-[8px] tracking-wider animate-pulse font-mono">⚡ CASCADE</text>
                    )}
                    <text x="300" y="270" className="fill-slate-500 font-bold text-[9px] uppercase tracking-widest">Electrical Switch</text>
                    <text x="300" y="305" className="fill-slate-300 font-mono text-[10px]">
                      CH4: {zoneGasData["Zone-D"]?.["CH4"] !== undefined ? `${zoneGasData["Zone-D"]["CH4"]} ppm` : "N/A"}
                    </text>
                    <text x="300" y="325" className="fill-slate-350 font-mono text-[10px]">
                      H2S: {zoneGasData["Zone-D"]?.["H2S"] !== undefined ? `${zoneGasData["Zone-D"]["H2S"]} ppm` : "N/A"}
                    </text>
                  </g>

                  {/* ZONE E */}
                  <g className="cursor-pointer">
                    <rect x="555" y="40" width="200" height="140" rx="8" className={`transition-all duration-500 ${getZoneStatus("Zone-E").strokeClass} ${getZoneStatus("Zone-E").fillClass}`} strokeWidth="2.5" strokeDasharray={getZoneStatus("Zone-E").isCascaded ? "6 4" : undefined} />
                    <text x="575" y="70" className="fill-white font-extrabold text-sm tracking-wider">ZONE-E</text>
                    {getZoneStatus("Zone-E").isCascaded && (
                      <text x="690" y="70" className="fill-sky-400 font-black text-[8px] tracking-wider animate-pulse font-mono">⚡ CASCADE</text>
                    )}
                    <text x="575" y="90" className="fill-slate-500 font-bold text-[9px] uppercase tracking-widest">Refinery Tank</text>
                    <text x="575" y="125" className="fill-slate-300 font-mono text-[10px]">
                      H2S: {zoneGasData["Zone-E"]?.["H2S"] !== undefined ? `${zoneGasData["Zone-E"]["H2S"]} ppm` : "N/A"}
                    </text>
                    <text x="575" y="145" className="fill-slate-350 font-mono text-[10px]">
                      CO: {zoneGasData["Zone-E"]?.["CO"] !== undefined ? `${zoneGasData["Zone-E"]["CO"]} ppm` : "N/A"}
                    </text>
                  </g>

                  {/* ZONE F */}
                  <g className="cursor-pointer">
                    <rect x="555" y="220" width="200" height="140" rx="8" className={`transition-all duration-500 ${getZoneStatus("Zone-F").strokeClass} ${getZoneStatus("Zone-F").fillClass}`} strokeWidth="2.5" strokeDasharray={getZoneStatus("Zone-F").isCascaded ? "6 4" : undefined} />
                    <text x="575" y="250" className="fill-white font-extrabold text-sm tracking-wider">ZONE-F</text>
                    {getZoneStatus("Zone-F").isCascaded && (
                      <text x="690" y="250" className="fill-sky-400 font-black text-[8px] tracking-wider animate-pulse font-mono">⚡ CASCADE</text>
                    )}
                    <text x="575" y="270" className="fill-slate-500 font-bold text-[9px] uppercase tracking-widest">Routine Loading</text>
                    <text x="575" y="305" className="fill-slate-300 font-mono text-[10px]">
                      CH4: {zoneGasData["Zone-F"]?.["CH4"] !== undefined ? `${zoneGasData["Zone-F"]["CH4"]} ppm` : "N/A"}
                    </text>
                    <text x="575" y="325" className="fill-slate-350 font-mono text-[10px]">
                      CO: {zoneGasData["Zone-F"]?.["CO"] !== undefined ? `${zoneGasData["Zone-F"]["CO"]} ppm` : "N/A"}
                    </text>
                  </g>

                  {/* WORKER POSITION MARKERS */}
                  {workers.map((worker) => {
                    const zoneStatus = getZoneStatus(worker.zone);
                    const isDanger = zoneStatus.tier >= 2;
                    return (
                      <g key={worker.id} className="transition-all duration-500">
                        {/* Outer pulsing ring in case of danger */}
                        {isDanger && (
                          <circle
                            cx={worker.x}
                            cy={worker.y}
                            r="12"
                            className="fill-none stroke-rose-500 stroke-2 animate-ping"
                          />
                        )}
                        {/* Outer glowing aura/pulse */}
                        <circle
                          cx={worker.x}
                          cy={worker.y}
                          r={isDanger ? "8" : "6"}
                          className={`transition-all duration-300 ${
                            isDanger 
                              ? "fill-rose-500/30 stroke-rose-400 stroke-1.5 animate-pulse" 
                              : "fill-cyan-500/20 stroke-cyan-400/50 stroke-1"
                          }`}
                        />
                        {/* Inner solid dot */}
                        <circle
                          cx={worker.x}
                          cy={worker.y}
                          r="4"
                          className={`transition-all duration-300 ${
                            isDanger 
                              ? "fill-rose-500 stroke-white stroke-1" 
                              : "fill-cyan-400 stroke-slate-950 stroke-1"
                          }`}
                        />
                        {/* Labeled Name + Role */}
                        <text
                          x={worker.x + 8}
                          y={worker.y + 3}
                          className={`font-mono text-[8px] font-bold select-none pointer-events-none transition-all duration-300 ${
                            isDanger ? "fill-rose-400 font-extrabold" : "fill-slate-350"
                          }`}
                        >
                          {worker.name} ({worker.role[0].toUpperCase()})
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>
            </div>

            {/* Safety Score Meter Gauge */}
            <div className={`p-6 rounded-2xl bg-gradient-to-br ${currentTier.bg} border ${currentTier.border} shadow-xl flex flex-col justify-between items-center transition-all duration-500 relative overflow-hidden group`}>
              <div className="absolute top-0 right-0 w-32 h-32 bg-slate-500/5 rounded-full blur-3xl" />
              <div className="w-full">
                <h2 className="text-lg font-bold text-slate-200 mb-1 flex items-center gap-2">
                  <Activity className="h-5 w-5 text-emerald-400" />
                  Safety Risk Index
                </h2>
                <p className="text-xs text-slate-400">
                  Dynamic plant risk calculations aggregated from sensor vectors.
                </p>
              </div>

              <div className="my-6 relative flex items-center justify-center">
                <svg className="w-48 h-48 transform -rotate-90">
                  <circle
                    cx="96"
                    cy="96"
                    r="78"
                    className="stroke-slate-800"
                    strokeWidth="10"
                    fill="transparent"
                  />
                  <circle
                    cx="96"
                    cy="96"
                    r="78"
                    className={`transition-all duration-1000 ease-out`}
                    strokeWidth="10"
                    strokeDasharray={2 * Math.PI * 78}
                    strokeDashoffset={2 * Math.PI * 78 * (1 - (riskAssessment?.score || 0) / 100)}
                    strokeLinecap="round"
                    fill="transparent"
                    style={{
                      stroke: riskAssessment 
                        ? riskAssessment.tier === 0 ? "#38bdf8" : riskAssessment.score >= 75 ? "#f43f5e" : riskAssessment.score >= 40 ? "#f59e0b" : "#10b981"
                        : "#10b981"
                    }}
                  />
                </svg>
                <div className="absolute flex flex-col items-center justify-center">
                  <span className={`text-5xl font-black tracking-tight ${currentTier.text}`}>
                    {riskAssessment?.score || 0}
                  </span>
                  <span className="text-[10px] font-extrabold uppercase tracking-widest text-slate-500 mt-1">
                    Risk Score
                  </span>
                </div>
              </div>

              <div className="w-full text-center p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                <div className={`text-sm font-extrabold ${currentTier.text}`}>
                  {currentTier.label}
                </div>
              </div>
            </div>

          </div>

          {/* Grid layout containing alerts and simulated emergency protocol panel */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className={`${riskAssessment && riskAssessment.tier === 3 ? "lg:col-span-2" : "lg:col-span-3"} p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-5`}>
            <div>
              <h2 className="text-lg font-bold text-slate-200 mb-1 flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-rose-500" />
                Active Safety Violations Feed
              </h2>
              <p className="text-xs text-slate-400">
                Interleaved deterministic alerts with AI briefing descriptions, sorted most recent first.
              </p>
            </div>

            {/* AI Safety Explanation Bubble */}
            {riskAssessment && riskAssessment.triggered_rules.length > 0 && (
              <div className="p-4.5 rounded-xl bg-slate-950 border border-emerald-500/25 relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl" />
                <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-extrabold uppercase tracking-wider mb-2">
                  <Sparkles className="h-4 w-4" />
                  Executive AI Briefing
                </div>
                {narrating ? (
                  <div className="flex items-center gap-2 text-xs text-slate-500 py-1">
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-emerald-400" />
                    Generating plain-language description...
                  </div>
                ) : (
                  <p className="text-xs text-slate-300 leading-relaxed font-medium">
                    {narration?.explanation}
                  </p>
                )}
              </div>
            )}

            {/* Rules list */}
            {!riskAssessment || riskAssessment.triggered_rules.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-slate-500 border border-dashed border-slate-800 rounded-xl bg-slate-950/30">
                <CheckCircle2 className="h-10 w-10 text-emerald-500/40 mb-3" />
                <span className="text-sm font-semibold">No Threat Anomalies Detected</span>
                <span className="text-xs text-slate-500 mt-1">All live variables are within normal parameters.</span>
              </div>
            ) : (
              <div className="space-y-3.5">
                {riskAssessment.triggered_rules.map((rule, idx) => (
                  <div 
                    key={idx} 
                    className={`p-4 rounded-xl border bg-slate-950/60 flex gap-4 transition-colors ${
                      rule.severity === 3 
                        ? "border-rose-500/20 hover:border-rose-500/30" 
                        : "border-amber-500/20 hover:border-amber-500/30"
                    }`}
                  >
                    <div className="shrink-0 mt-0.5">
                      <AlertTriangle className={`h-5.5 w-5.5 ${
                        rule.severity === 3 ? "text-rose-500" : "text-amber-500"
                      }`} />
                    </div>
                    <div className="space-y-1.5 flex-1">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <span className="text-xs font-black text-slate-100 uppercase font-mono tracking-wider">
                          {rule.rule_name}
                        </span>
                        <div className="flex gap-2 items-center flex-wrap">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                            rule.severity === 3 
                              ? "bg-rose-500/10 text-rose-400 border border-rose-500/20" 
                              : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          }`}>
                            Tier {rule.severity === 3 ? "3 — Escalate" : rule.severity === 2 ? "2 — Warning" : "1 — Log"}
                          </span>
                          {rule.predicted_confidence !== undefined && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              Historical confidence: {Math.round(rule.predicted_confidence * 100)}% (based on {rule.past_similar_flags_count || 0} similar past flags)
                            </span>
                          )}
                          {(rule as any).would_have_triggered_local_alert && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-amber-500/15 text-amber-500 border border-amber-500/25">
                              ⚠️ Shadow Mode: Would Have Triggered Local Alert
                            </span>
                          )}
                        </div>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        {rule.reason}
                      </p>
                      <AlertExplainabilityChart apiUrl={apiUrl} />
                      {/* Related Historical Incidents Accordion */}
                      {(() => {
                        const ruleIncidents = riskAssessment.related_incidents?.filter(inc => 
                          inc.rule_type === rule.rule_name ||
                          inc.reasons.some((r: string) => r.includes(rule.rule_name))
                        ) || [];
                        
                        if (ruleIncidents.length === 0) return null;
                        
                        return (
                          <details className="group mt-3 border-t border-slate-800/40 pt-3">
                            <summary className="list-none flex items-center justify-between text-[10px] font-black text-emerald-400 hover:text-emerald-300 cursor-pointer transition-colors uppercase tracking-wider select-none">
                              <span className="flex items-center gap-1.5">
                                <Brain className="h-3.5 w-3.5" />
                                Related Past Incidents ({ruleIncidents.length})
                              </span>
                              <span className="text-[9px] text-slate-500 font-bold group-open:rotate-180 transition-transform">
                                ▼
                              </span>
                            </summary>
                            <div className="mt-3.5 space-y-3 pl-1">
                              {ruleIncidents.map((inc: any, idxInc: number) => (
                                <div key={idxInc} className="p-3 rounded-xl bg-slate-950/80 border border-slate-900 space-y-2 text-xs">
                                  <div className="flex justify-between items-center text-[9px] font-bold text-slate-500 uppercase font-mono">
                                    <span>Incident #{inc.id} ({inc.zone})</span>
                                    <span>{inc.regulatory_clause}</span>
                                  </div>
                                  <p className="text-[11px] text-slate-400 leading-relaxed font-medium font-sans">
                                    {inc.text}
                                  </p>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {inc.reasons.map((reason: string, idxR: number) => (
                                      <span key={idxR} className="px-1.5 py-0.2 rounded text-[8px] font-extrabold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/10">
                                        {reason}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </details>
                        );
                      })()}
                      
                      {/* Safety Officer Verdict Feedback */}
                      {rule.flag_id && (
                        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-800/40">
                          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mr-auto">
                            Officer Verdict:
                          </span>
                          {feedbackStatus[rule.flag_id] ? (
                            <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded border ${
                              feedbackStatus[rule.flag_id] === "Confirmed Risk"
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                            }`}>
                              {feedbackStatus[rule.flag_id] === "Confirmed Risk" ? "✓ Confirmed Risk" : "✗ False Alarm"}
                            </span>
                          ) : (
                            <div className="flex gap-2">
                              <button
                                onClick={() => submitFeedback(rule.flag_id, rule.rule_name, "Confirmed Risk")}
                                className="px-2 py-1 text-[10px] font-bold rounded bg-emerald-600/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-600/20 transition-all"
                              >
                                Confirm Risk
                              </button>
                              <button
                                onClick={() => submitFeedback(rule.flag_id, rule.rule_name, "False Alarm")}
                                className="px-2 py-1 text-[10px] font-bold rounded bg-rose-600/10 text-rose-400 border border-rose-500/20 hover:bg-rose-600/20 transition-all"
                              >
                                False Alarm
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Watch Flags list */}
            {riskAssessment && riskAssessment.watch_flags && riskAssessment.watch_flags.length > 0 && (
              <div className="space-y-3.5 pt-4 border-t border-slate-800/80">
                <div className="text-xs font-extrabold uppercase tracking-widest text-slate-450 flex items-center gap-1.5">
                  <Activity className="h-4 w-4 text-sky-400 animate-pulse" />
                  Active Proximity Watch Alerts
                </div>
                <div className="space-y-2">
                  {riskAssessment.watch_flags.map((wf, idx) => (
                    <div 
                      key={idx} 
                      className="p-4 rounded-xl border border-sky-500/20 bg-slate-950/40 hover:border-sky-500/30 flex gap-4 transition-colors"
                    >
                      <div className="shrink-0 mt-0.5">
                        <Activity className="h-5.5 w-5.5 text-sky-500 animate-[pulse_2s_infinite]" />
                      </div>
                      <div className="space-y-1.5 flex-1">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <span className="text-xs font-black text-slate-100 uppercase font-mono tracking-wider">
                            {wf.signal_type} Watch - {wf.zone}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-sky-500/10 text-sky-400 border border-sky-500/20">
                            Trend: {wf.trend}
                          </span>
                        </div>
                        <p className="text-xs text-slate-305 leading-relaxed font-medium">
                          {wf.predicted_threshold_breach_minutes !== undefined && wf.predicted_threshold_breach_minutes !== null ? (
                            <span>
                              {wf.signal_type} trending up, <span className="font-mono text-sky-450 font-bold">{wf.current_value} ppm</span> → predicted to cross <span className="font-mono text-slate-450 font-bold">{wf.threshold} ppm</span> threshold in approximately <span className="font-mono text-sky-400 font-bold font-black underline decoration-sky-500 decoration-2">{Math.round(wf.predicted_threshold_breach_minutes)} minutes</span> (±{Math.round(wf.confidence_interval || 0)} mins).
                            </span>
                          ) : (
                            <span>
                              Telemetry value <span className="font-mono text-sky-450 font-bold">{wf.current_value} ppm</span> is approaching the safety threshold of <span className="font-mono text-slate-450 font-bold">{wf.threshold} ppm</span>.
                            </span>
                          )}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Emergency Response Panel */}
          {riskAssessment && riskAssessment.tier === 3 && (
            <div className="lg:col-span-1 p-6 rounded-2xl bg-gradient-to-br from-rose-950/15 via-slate-900 to-slate-950 border border-rose-500/20 shadow-xl flex flex-col justify-between space-y-5 relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-24 h-24 bg-rose-500/5 rounded-full blur-2xl animate-pulse" />
              
              <div className="space-y-4">
                {/* Header */}
                <div>
                  <div className="flex items-center gap-2 text-rose-450 font-extrabold text-xs uppercase tracking-wider mb-1 flex-wrap">
                    <span className="relative flex h-2 w-2 shrink-0">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-450 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
                    </span>
                    <span className="bg-gradient-to-r from-rose-400 to-orange-400 bg-clip-text text-transparent font-extrabold">
                      Emergency Protocol Initiated
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono tracking-wider font-bold">
                    Zone: <span className="text-rose-450 font-bold">{emergencyProtocol?.zone || "Detecting..."}</span>
                  </div>
                </div>

                {/* Vertical step tracker */}
                <div className="relative pl-6 space-y-6 py-2">
                  {/* Line connector */}
                  <div className="absolute left-2.5 top-5 bottom-5 w-0.5 border-l border-dashed border-slate-800" />

                  {(emergencyProtocol?.steps || [
                    { name: "Evacuation Zone Marked", reached: false, timestamp: null },
                    { name: "Response Team Alerted", reached: false, timestamp: null },
                    { name: "Sensor Evidence Preserved", reached: false, timestamp: null },
                    { name: "Preliminary Incident Report Drafted", reached: false, timestamp: null }
                  ]).map((step: any, sIdx: number) => {
                    const StepIcon = [ShieldAlert, Radio, Database, FileText][sIdx];
                    const formattedTime = step.timestamp 
                      ? new Date(step.timestamp).toLocaleTimeString() 
                      : null;

                    return (
                      <div key={sIdx} className="relative flex gap-3.5 items-start">
                        {/* Dot / Icon */}
                        <div className={`absolute -left-6 z-10 p-1 rounded-full border transition-all duration-300 ${
                          step.reached 
                            ? "bg-rose-950 border-rose-500/30 text-rose-400 shadow-md shadow-rose-500/25" 
                            : "bg-slate-950 border-slate-800 text-slate-500"
                        }`}>
                          <StepIcon className={`h-3 w-3 ${step.reached && sIdx === (emergencyProtocol?.steps.filter((s:any) => s.reached).length - 1) ? "animate-pulse" : ""}`} />
                        </div>

                        <div className="space-y-0.5 flex-1">
                          <div className="flex justify-between items-center gap-2">
                            <span className={`text-xs font-bold tracking-tight ${step.reached ? "text-slate-100 font-extrabold" : "text-slate-550"}`}>
                              {step.name}
                            </span>
                            {formattedTime && (
                              <span className="text-[9px] font-mono text-slate-400 font-bold uppercase bg-slate-950 px-1.5 py-0.2 rounded border border-slate-800">
                                {formattedTime}
                              </span>
                            )}
                          </div>
                          {!step.reached && (
                            <div className="text-[9px] text-slate-650 font-medium">
                              Awaiting trigger condition...
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Preliminary Report Dropdown Card */}
                {emergencyProtocol?.preliminary_report && (
                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-3 mt-4 text-xs animate-fade-in">
                    <div className="flex items-center gap-1.5 text-emerald-400 font-extrabold text-[10px] uppercase tracking-widest border-b border-slate-800/80 pb-1.5">
                      <FileText className="h-3.5 w-3.5" />
                      Preliminary Incident Draft
                    </div>
                    <div className="space-y-2 text-[11px] leading-relaxed">
                      <div>
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block mb-0.5">Summary:</span>
                        <span className="text-slate-350 font-medium">{emergencyProtocol.preliminary_report.summary}</span>
                      </div>
                      <div>
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block mb-0.5">Applicable Clause:</span>
                        <span className="text-slate-350 font-bold font-mono text-[10px] bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">{emergencyProtocol.preliminary_report.applicable_clause}</span>
                      </div>
                      <div>
                        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block mb-0.5">Clause Relation:</span>
                        <span className="text-slate-400 font-medium">{emergencyProtocol.preliminary_report.clause_relation}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Download PDF Button */}
                <button
                  onClick={() => {
                    const activeZone = emergencyProtocol?.zone || ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F"].find(z => 
                      riskAssessment?.triggered_rules?.some(r => r.severity === 3 && r.reason.includes(z))
                    ) || "Zone-A";
                    handleDownloadPdf(activeZone);
                  }}
                  className="w-full py-2 px-3 bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-400 hover:text-emerald-300 rounded-xl text-xs font-bold uppercase tracking-wider transition-all cursor-pointer flex items-center justify-center gap-2 shadow-sm"
                >
                  <Download className="h-4 w-4" />
                  Download Regulatory Evidence PDF
                </button>
                {/* Evacuation Confirmation Button */}
                <div className="pt-3 border-t border-slate-800/80">
                  {alarmState?.facility_evacuation_active ? (
                    <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-center space-y-1.5 animate-[pulse_1.8s_infinite]">
                      <span className="text-xs font-black uppercase tracking-wider text-rose-455 block">
                        🚨 Evacuation Siren Triggered
                      </span>
                      <p className="text-[9px] text-slate-400 font-medium">
                        Auditable Log: {alarmState.confirmation_log[0] ? `${alarmState.confirmation_log[0].confirmed_by_role} authorized evacuation at ${new Date(alarmState.confirmation_log[0].confirmed_at).toLocaleTimeString()}` : "Evacuation sirens active."}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-[10px] text-slate-400 leading-normal">
                        Critical Tier 3 incident detected. Evacuation recommended by SentinelGrid, requiring human authorization.
                      </p>
                      <button
                        onClick={() => {
                          const t3Rule = riskAssessment?.triggered_rules?.find(r => r.severity === 3);
                          if (t3Rule) {
                            handleConfirmEvacuation(t3Rule.flag_id || "T3_FLAG");
                          } else {
                            handleConfirmEvacuation("T3_FLAG");
                          }
                        }}
                        className="w-full py-2.5 bg-gradient-to-r from-rose-600 to-orange-600 hover:from-rose-500 hover:to-orange-500 text-slate-950 font-black uppercase rounded-xl transition-all cursor-pointer shadow-md shadow-rose-500/10 active:scale-[0.98]"
                      >
                        ⚠️ Confirm Facility Evacuation
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Footer simulation warning */}
              <div className="text-[9px] text-slate-500 leading-normal border-t border-slate-800/80 pt-3 flex items-start gap-1.5">
                <Info className="h-3.5 w-3.5 text-slate-600 shrink-0 mt-0.5" />
                <span>
                  Simulated orchestration — represents automated actions a production deployment would execute via SCADA/notification system integrations.
                </span>
              </div>
            </div>
          )}
        </div>
      </>
      )}

    </div>
  );
}
