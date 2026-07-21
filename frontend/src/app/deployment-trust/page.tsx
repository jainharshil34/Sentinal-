"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Shield, 
  CheckCircle2, 
  XCircle, 
  TrendingUp, 
  AlertTriangle, 
  Clock, 
  Info,
  Server,
  ChevronRight,
  UserCheck,
  Zap,
  Activity,
  Brain,
  Loader2,
  RefreshCw
} from "lucide-react";

interface ShadowPrediction {
  id: number;
  flag_id: string;
  rule_name: string;
  verdict: string;
  timestamp: string;
}

interface DeploymentStatus {
  plant_id: string;
  current_mode: string;
  trust_score: number;
  shadow_predictions_count: number;
  confirmed_count: number;
  false_alarm_count: number;
  graduation_eligible: boolean;
  history: ShadowPrediction[];
}

interface ModelPerformance {
  precision: number;
  recall: number;
  feature_importances: { feature: string; importance: number; direction: string }[];
}

export default function DeploymentTrustPage() {
  const [activePlant, setActivePlant] = useState<string>("Plant-A");
  const [status, setStatus] = useState<DeploymentStatus | null>(null);
  const [modelPerf, setModelPerf] = useState<ModelPerformance | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [promoting, setPromoting] = useState<boolean>(false);
  const [retraining, setRetraining] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchStatus = async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const res = await axios.get<DeploymentStatus>(`${apiUrl}/api/deployment-status`, {
        params: { plant_id: activePlant }
      });
      setStatus(res.data);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch deployment status", err);
      setError("Failed to fetch plant deployment status. Ensure python backend is running.");
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  const fetchModelPerformance = async () => {
    try {
      const res = await axios.get<ModelPerformance>(`${apiUrl}/api/model-performance`);
      setModelPerf(res.data);
    } catch (err) {
      console.error("Failed to fetch confidence model performance metrics", err);
    }
  };

  useEffect(() => {
    fetchStatus(true);
    fetchModelPerformance();
  }, [activePlant]);

  const triggerRetrain = async () => {
    setRetraining(true);
    try {
      const res = await axios.post<ModelPerformance>(`${apiUrl}/api/model-performance/retrain`);
      setModelPerf(res.data);
      await fetchStatus(false);
      alert("Confidence prediction model successfully retrained on updated Safety Officer feedback database!");
    } catch (err) {
      console.error("Failed to retrain confidence model", err);
      alert("Failed to retrain model. Verify backend connectivity.");
    } finally {
      setRetraining(false);
    }
  };

  const toggleDeploymentMode = async (targetMode: "shadow" | "live") => {
    setPromoting(true);
    try {
      await axios.post(`${apiUrl}/api/deployment-mode`, {
        plant_id: activePlant,
        mode: targetMode
      });
      // Refresh status
      await fetchStatus(false);
    } catch (err) {
      console.error("Failed to change deployment mode", err);
      alert("Failed to change deployment mode. Check backend connectivity.");
    } finally {
      setPromoting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-slate-400 gap-3">
        <Clock className="h-8 w-8 text-indigo-400 animate-spin" />
        <span className="text-sm font-semibold">Analyzing plant shadow deployment logs...</span>
      </div>
    );
  }

  if (error || !status) {
    return (
      <div className="p-6 text-center max-w-lg mx-auto bg-slate-900 border border-slate-800 rounded-2xl mt-12 space-y-4">
        <AlertTriangle className="h-10 w-10 text-rose-500 mx-auto" />
        <h3 className="text-slate-200 font-bold">System Error</h3>
        <p className="text-xs text-slate-400">{error || "Could not load deployment configuration."}</p>
        <button onClick={() => fetchStatus(true)} className="px-4 py-2 bg-slate-800 text-white rounded-lg text-xs font-bold hover:bg-slate-700 transition-colors">
          Retry Connection
        </button>
      </div>
    );
  }

  // Parameters for eligibility rules
  const minPredictions = 20;
  const minTrust = 90.0;

  const countMet = status.shadow_predictions_count >= minPredictions;
  const trustMet = status.trust_score >= minTrust;

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      
      {/* Header and Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-gradient-to-br from-indigo-500/20 to-pink-500/20 rounded-xl border border-indigo-500/30">
              <Shield className="h-7 w-7 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight text-white">
                Deployment Mode & Trust Graduation
              </h1>
              <p className="text-sm text-slate-400 mt-1">
                Monitor AI model accuracy in Shadow Mode before promoting to Live auto-escalations.
              </p>
            </div>
          </div>
        </div>

        {/* Plant selector tabs */}
        <div className="flex items-center gap-2 bg-slate-900/60 p-1 border border-slate-800/80 rounded-xl max-w-max">
          {["Plant-A", "Plant-B", "Plant-C"].map((pId) => (
            <button
              key={pId}
              onClick={() => setActivePlant(pId)}
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
      </div>

      {/* Main Grid: Checklist & Visual metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Graduation Eligibility Checklist */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Eligibility Card */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-5">
            <div>
              <h3 className="text-sm font-bold text-slate-200">
                Graduation Eligibility Checklist
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Rules governing the transition from Shadow Mode predictions to Live Mode authority.
              </p>
            </div>

            <div className="space-y-4">
              {/* Checklist 1: Prediction Count */}
              <div className={`p-4 rounded-xl border flex items-center gap-4 transition-colors ${
                countMet ? "bg-emerald-950/10 border-emerald-500/20" : "bg-rose-950/10 border-rose-500/20"
              }`}>
                {countMet ? (
                  <CheckCircle2 className="h-6 w-6 text-emerald-400 shrink-0" />
                ) : (
                  <XCircle className="h-6 w-6 text-rose-450 shrink-0" />
                )}
                <div className="flex-1">
                  <div className="flex justify-between items-center text-xs font-bold text-slate-200">
                    <span>Minimum Shadow Predictions</span>
                    <span className="font-mono">{status.shadow_predictions_count} / {minPredictions}</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Ensures a statistically significant historical verification dataset has been evaluated.
                  </p>
                </div>
              </div>

              {/* Checklist 2: Trust Score */}
              <div className={`p-4 rounded-xl border flex items-center gap-4 transition-colors ${
                trustMet ? "bg-emerald-950/10 border-emerald-500/20" : "bg-rose-950/10 border-rose-500/20"
              }`}>
                {trustMet ? (
                  <CheckCircle2 className="h-6 w-6 text-emerald-400 shrink-0" />
                ) : (
                  <XCircle className="h-6 w-6 text-rose-450 shrink-0" />
                )}
                <div className="flex-1">
                  <div className="flex justify-between items-center text-xs font-bold text-slate-200">
                    <span>Minimum Confidence / Trust Rate</span>
                    <span className="font-mono">{status.trust_score}% / {minTrust}%</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Requires safety officer verdicts to confirm risk flags with high true-positive accuracy.
                  </p>
                </div>
              </div>
            </div>

            {/* Promotion / Demotion Action Bar */}
            <div className="pt-4 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="text-xs text-slate-350">
                Current State: <span className={`font-extrabold font-mono px-2 py-0.5 rounded text-[10px] uppercase ml-1.5 ${
                  status.current_mode === "live" 
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                    : "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"
                }`}>
                  {status.current_mode === "live" ? "Live Mode" : "Shadow Mode"}
                </span>
              </div>
              
              {status.current_mode === "shadow" ? (
                <button
                  disabled={!status.graduation_eligible || promoting}
                  onClick={() => toggleDeploymentMode("live")}
                  className={`px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-wider flex items-center gap-2 transition-all ${
                    status.graduation_eligible
                      ? "bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 shadow-md shadow-emerald-500/10 cursor-pointer active:scale-[0.98]"
                      : "bg-slate-800 text-slate-500 border border-slate-750 cursor-not-allowed"
                  }`}
                >
                  <UserCheck className="h-4 w-4" />
                  {promoting ? "Promoting..." : "Promote to Live Mode"}
                </button>
              ) : (
                <button
                  disabled={promoting}
                  onClick={() => toggleDeploymentMode("shadow")}
                  className="px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-wider flex items-center gap-2 bg-slate-950 hover:bg-slate-800 text-rose-450 hover:text-rose-350 border border-slate-800 transition-all cursor-pointer"
                >
                  <AlertTriangle className="h-4 w-4" />
                  Demote to Shadow Mode
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Visual Trust Gauges */}
        <div className="space-y-6">
          
          {/* Trust Score Radial Card */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl flex flex-col items-center justify-center space-y-4">
            <div className="text-center w-full">
              <h3 className="text-sm font-bold text-slate-200">
                Deployment Trust Level
              </h3>
              <p className="text-[10px] text-slate-500 mt-0.5">
                Rolling True Positive rate for {activePlant}
              </p>
            </div>

            <div className="relative flex items-center justify-center h-40 w-40">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="80" cy="80" r="64" className="stroke-slate-800" strokeWidth="8" fill="transparent" />
                <circle 
                  cx="80" 
                  cy="80" 
                  r="64" 
                  className="transition-all duration-1000 ease-out" 
                  strokeWidth="8" 
                  strokeDasharray={2 * Math.PI * 64}
                  strokeDashoffset={2 * Math.PI * 64 * (1 - status.trust_score / 100)}
                  strokeLinecap="round" 
                  fill="transparent" 
                  style={{ stroke: status.trust_score >= minTrust ? "#10b981" : "#f43f5e" }}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none select-none text-center">
                <span className="text-3xl font-black text-slate-100">{status.trust_score}%</span>
                <span className="text-[9px] font-black uppercase text-slate-500 mt-1">Trust Score</span>
              </div>
            </div>

            <div className="w-full grid grid-cols-2 gap-2 text-center text-xs font-mono font-bold bg-slate-950/60 p-3 rounded-xl border border-slate-850">
              <div>
                <div className="text-emerald-450">{status.confirmed_count}</div>
                <div className="text-[9px] uppercase text-slate-500 font-sans mt-0.5">Confirmed</div>
              </div>
              <div className="border-l border-slate-800">
                <div className="text-rose-450">{status.false_alarm_count}</div>
                <div className="text-[9px] uppercase text-slate-500 font-sans mt-0.5">False Alarm</div>
              </div>
            </div>
          </div>

          {/* Model Performance Panel */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-5">
            <div>
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-1.5">
                <Brain className="h-4.5 w-4.5 text-indigo-400" />
                Adaptive Confidence Predictor
              </h3>
              <p className="text-[10px] text-slate-500 mt-0.5">
                Supervised classifier (Logistic Regression) predicting alert validity.
              </p>
            </div>

            {modelPerf ? (
              <div className="space-y-4">
                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-3 text-center">
                  <div className="p-2.5 bg-slate-950/60 rounded-xl border border-slate-800/80">
                    <span className="text-lg font-black text-indigo-400">
                      {Math.round(modelPerf.precision * 100)}%
                    </span>
                    <div className="text-[9px] font-extrabold uppercase text-slate-500 mt-0.5">Precision</div>
                  </div>
                  <div className="p-2.5 bg-slate-950/60 rounded-xl border border-slate-800/80">
                    <span className="text-lg font-black text-indigo-400">
                      {Math.round(modelPerf.recall * 100)}%
                    </span>
                    <div className="text-[9px] font-extrabold uppercase text-slate-500 mt-0.5">Recall</div>
                  </div>
                </div>

                {/* Plain-language explanation */}
                <p className="text-[10px] text-slate-400 leading-relaxed bg-slate-950/40 p-2.5 rounded-lg border border-slate-850/60">
                  Precision indicates how often a predicted positive risk is confirmed. Recall indicates how many actual risks are caught. The model trains dynamically on Officer verdicts.
                </p>

                {/* Feature Importances */}
                <div className="space-y-2">
                  <span className="text-[10px] font-black uppercase text-slate-500 tracking-wider">Top Predictors</span>
                  <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
                    {modelPerf.feature_importances.map((item, idx) => (
                      <div key={idx} className="flex justify-between items-center text-[10px] bg-slate-950/30 p-1.5 rounded border border-slate-900">
                        <span className="font-mono text-slate-350 font-semibold">{item.feature}</span>
                        <div className="flex items-center gap-1.5">
                          <span className={`h-1.5 w-1.5 rounded-full ${item.direction === "positive" ? "bg-emerald-500" : "bg-rose-500"}`} />
                          <span className="font-bold font-mono text-slate-400">{item.importance.toFixed(2)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-6 text-slate-500 text-xs">
                Loading model metrics...
              </div>
            )}

            {/* Retrain Button */}
            <button
              onClick={triggerRetrain}
              disabled={retraining}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-indigo-650 hover:bg-indigo-600 disabled:bg-slate-800 text-white disabled:text-slate-550 text-xs font-black uppercase rounded-xl transition-all cursor-pointer shadow-md shadow-indigo-500/10 active:scale-[0.99]"
            >
              {retraining ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin text-white" />
                  Retraining Model...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4" />
                  Retrain Model
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Shadow Predictions History Log */}
      <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-4">
        <div>
          <h3 className="text-sm font-bold text-slate-200">
            Shadow Prediction Audit Ledger
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Rolling historical audit of all detections evaluated in Shadow Mode.
          </p>
        </div>

        <div className="overflow-x-auto">
          {status.history.length === 0 ? (
            <div className="text-center py-10 text-slate-500 text-xs">
              No shadow prediction logs found for {activePlant}.
            </div>
          ) : (
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-[10px] font-black uppercase text-slate-500 tracking-wider">
                  <th className="py-3 px-4">Prediction ID</th>
                  <th className="py-3 px-4">Rule Fired</th>
                  <th className="py-3 px-4 text-center">Timestamp</th>
                  <th className="py-3 px-4 text-right">Verdict</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {status.history.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-950/40 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-slate-400">{log.flag_id}</td>
                    <td className="py-3 px-4 font-bold font-mono text-slate-200">{log.rule_name}</td>
                    <td className="py-3 px-4 text-center font-mono text-slate-450">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                        log.verdict === "Confirmed Risk"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                      }`}>
                        {log.verdict === "Confirmed Risk" ? "Confirmed Risk" : "False Alarm"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
