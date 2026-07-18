"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import {
  Server,
  Activity,
  AlertTriangle,
  Brain,
  ShieldCheck,
  TrendingUp,
  Loader2,
  ChevronRight,
  Info,
  Radio
} from "lucide-react";

interface CrossPlantPattern {
  historical_incident_id: number;
  text: string;
  rule_type: string;
  regulatory_clause: string;
  other_plant_id: string;
  time_offset_desc: string;
  summary: string;
}

interface PlantSummary {
  plant_id: string;
  plant_name: string;
  score: number;
  tier: number;
  tier_name: string;
  active_flags_count: number;
  cross_plant_patterns: CrossPlantPattern[];
}

export default function FleetOverviewPage() {
  const router = useRouter();
  const [fleet, setFleet] = useState<PlantSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeScenario, setActiveScenario] = useState<string>("normal");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchFleetStatus = async (showSpinner = false) => {
    if (showSpinner) setLoading(true);
    try {
      // 1. Fetch simulation scenario state to display active controls
      const simRes = await axios.get(`${apiUrl}/api/simulation/state`);
      if (simRes.data && simRes.data.scenario) {
        setActiveScenario(simRes.data.scenario);
      }

      // 2. Fetch fleet overview metrics
      const fleetRes = await axios.get<PlantSummary[]>(`${apiUrl}/api/fleet-overview`);
      setFleet(fleetRes.data);
      setError(null);
    } catch (err: any) {
      console.error("Failed to load fleet status", err);
      setError("Failed to fetch fleet telemetry. Ensure the Python backend server is running.");
    } finally {
      if (showSpinner) setLoading(false);
    }
  };

  // Poll status every 5 seconds
  useEffect(() => {
    fetchFleetStatus(true);
    const interval = setInterval(() => {
      fetchFleetStatus(false);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handlePlantClick = (plantId: string) => {
    router.push(`/?plant_id=${plantId}`);
  };

  const getTierBadge = (tier: number) => {
    switch (tier) {
      case 3:
        return (
          <span className="px-3 py-1 text-xs font-semibold rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 shadow-sm animate-pulse">
            Action Required
          </span>
        );
      case 2:
        return (
          <span className="px-3 py-1 text-xs font-semibold rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-sm">
            Warning Active
          </span>
        );
      default:
        return (
          <span className="px-3 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm">
            Nominal
          </span>
        );
    }
  };

  const getPlantGradient = (tier: number) => {
    switch (tier) {
      case 3:
        return "from-rose-950/20 via-slate-900 to-slate-900 border-rose-500/30 hover:border-rose-500/50 shadow-[0_0_15px_rgba(244,63,94,0.05)]";
      case 2:
        return "from-amber-950/20 via-slate-900 to-slate-900 border-amber-500/30 hover:border-amber-500/50 shadow-[0_0_15px_rgba(245,158,11,0.05)]";
      default:
        return "from-slate-900 via-slate-900 to-slate-900 border-slate-800 hover:border-slate-700 shadow-sm";
    }
  };

  // Human readable scenario names
  const SCENARIO_NAMES: Record<string, string> = {
    normal: "Normal Operations",
    scenario_1: "Scenario 1: Hot Work + Methane (Zone-A)",
    scenario_2: "Scenario 2: Confined Space + CO (Zone-B)",
    scenario_3: "Scenario 3: Hot Work + H2S Leak (Zone-C)",
    scenario_4: "Scenario 4: Electrical + Methane (Zone-D)",
    silent_failure: "Scenario 5: Telemetry Offline (Zone-E)",
    vizag_buildup: "Vizag coke oven battery buildup",
    multi_gas_toxicity: "Scenario 6: Multi-Gas Toxicity (Zone-F)"
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg border border-indigo-500/20">
              <Server className="h-6 w-6" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white">Fleet Overview</h1>
          </div>
          <p className="text-slate-400 mt-2 text-sm max-w-2xl">
            Real-time operations monitor and safety intelligence coordinator across all fleet facilities.
            Synthesizes local telemetry streams to propagate compound risk patterns.
          </p>
        </div>

        {/* Status Indicator */}
        <div className="mt-4 md:mt-0 flex items-center gap-3 bg-slate-900/60 border border-slate-800 px-4 py-2 rounded-xl">
          <div className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
          </div>
          <div className="text-xs">
            <div className="text-slate-400 font-semibold">Active Simulation Scenario</div>
            <div className="text-indigo-400 font-medium">{SCENARIO_NAMES[activeScenario] || activeScenario}</div>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 bg-rose-500/10 border border-rose-500/30 text-rose-400 p-4 rounded-xl flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-sm">Connection Issue Detected</p>
            <p className="text-xs text-rose-400/80 mt-1">{error}</p>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="h-10 w-10 text-indigo-400 animate-spin mb-4" />
          <p className="text-slate-400 text-sm">Consolidating cross-plant metrics...</p>
        </div>
      ) : (
        <>
          {/* Main Plant Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
            {fleet.map((plant) => (
              <div
                key={plant.plant_id}
                className={`bg-gradient-to-b ${getPlantGradient(plant.tier)} border rounded-2xl p-6 transition-all duration-300 flex flex-col justify-between`}
              >
                <div>
                  {/* Top Row: Plant Info */}
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h2 className="text-xl font-bold text-white tracking-wide">{plant.plant_name}</h2>
                      <span className="text-xs text-slate-500 font-medium">Node ID: {plant.plant_id}</span>
                    </div>
                    {getTierBadge(plant.tier)}
                  </div>

                  {/* Safety Risk Meter */}
                  <div className="bg-slate-950/60 border border-slate-800/60 p-4 rounded-xl mb-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-xs text-slate-400 font-semibold">Safety Risk Score</span>
                      <span className={`text-lg font-black tracking-tight ${
                        plant.score >= 75 ? "text-rose-400" : plant.score >= 40 ? "text-amber-400" : "text-emerald-400"
                      }`}>
                        {plant.score} <span className="text-xs font-normal text-slate-500">/100</span>
                      </span>
                    </div>
                    
                    {/* Progress Bar */}
                    <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          plant.score >= 75 ? "bg-rose-500" : plant.score >= 40 ? "bg-amber-500" : "bg-emerald-500"
                        }`}
                        style={{ width: `${plant.score}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* Flag Count */}
                  <div className="flex justify-between items-center px-2 py-1.5 border-b border-slate-800/40 text-xs">
                    <span className="text-slate-400 font-medium">Active Compound Risks</span>
                    <span className={`font-bold px-2 py-0.5 rounded ${
                      plant.active_flags_count > 0 ? "bg-rose-500/10 text-rose-400" : "bg-slate-800 text-slate-400"
                    }`}>
                      {plant.active_flags_count} flags
                    </span>
                  </div>

                  {/* Telemetry Stream Badge */}
                  <div className="flex justify-between items-center px-2 py-1.5 text-xs">
                    <span className="text-slate-400 font-medium">Telemetry Streams</span>
                    <span className="text-emerald-400 font-semibold flex items-center gap-1">
                      <Radio className="h-3.5 w-3.5 animate-pulse" /> Active
                    </span>
                  </div>

                  {/* Fleet Intelligence Cross-Plant Patterns */}
                  {plant.cross_plant_patterns && plant.cross_plant_patterns.length > 0 ? (
                    <div className="mt-4 p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/20 text-xs text-indigo-200">
                      <div className="flex items-center gap-2 mb-2 text-indigo-400 font-bold tracking-wide">
                        <Brain className="h-4 w-4 animate-pulse" />
                        <span>FLEET INTELLIGENCE FLAG</span>
                      </div>
                      <p className="leading-relaxed font-medium text-slate-300">
                        💡 {plant.cross_plant_patterns[0].summary}
                      </p>
                      <div className="mt-2 text-[10px] text-slate-500 bg-slate-950/40 px-2 py-1 rounded">
                        Incident matches rule: <span className="font-semibold text-indigo-300">{plant.cross_plant_patterns[0].rule_type}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-4 p-4 rounded-xl bg-slate-900/40 border border-slate-800/40 text-xs text-slate-500 italic text-center">
                      No matching historical incident patterns detected.
                    </div>
                  )}
                </div>

                {/* View Details Action */}
                <button
                  onClick={() => handlePlantClick(plant.plant_id)}
                  className={`mt-6 w-full flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-bold transition-all duration-300 ${
                    plant.tier === 3 
                      ? "bg-rose-500 hover:bg-rose-600 text-white shadow-[0_4px_12px_rgba(244,63,94,0.2)]" 
                      : plant.tier === 2 
                      ? "bg-amber-500 hover:bg-amber-600 text-white shadow-[0_4px_12px_rgba(245,158,11,0.2)]"
                      : "bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800"
                  }`}
                >
                  <span>Access Live Dashboard</span>
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>

          {/* Explanation Section */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
              <Info className="h-5 w-5 text-indigo-400" />
              About Fleet-Wide Pattern Learning
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-slate-400 leading-relaxed">
              <div>
                <p className="mb-3">
                  Traditional safety systems operate as isolated data silos, assessing risk within single plants or standalone sensor networks. SentinelGrid addresses this vulnerability by building a consolidated incident pattern corpus accessible fleet-wide.
                </p>
                <p>
                  When a safety risk (Tier 2/3) is detected at one plant, our vector embedding agent immediately queries the historical incident graph. It correlates the live telemetry pattern with historical safety logs from other facilities.
                </p>
              </div>
              <div>
                <p className="mb-3">
                  This architecture ensures that a safety anomaly occurring at <span className="text-white font-semibold">Plant-C</span> directly informs the risk modeling at <span className="text-white font-semibold">Plant-A</span>. In doing so, operations managers acquire preventive intelligence before minor fluctuations turn into industrial hazards.
                </p>
                <div className="mt-4 p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/10 flex items-center gap-3">
                  <ShieldCheck className="h-6 w-6 text-indigo-400 shrink-0" />
                  <span className="text-xs text-indigo-300">
                    SentinelGrid facilitates real-time safety learning, transforming standalone sensors into a reasoning, cooperative fleet protection network.
                  </span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
