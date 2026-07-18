"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";
import {
  ShieldCheck,
  FileText,
  AlertTriangle,
  Loader2,
  XCircle,
  Sparkles,
  TrendingUp,
  Activity,
  CheckCircle2
} from "lucide-react";

interface ClauseCount {
  clause: string;
  count: number;
  description: string;
}

interface TrendPoint {
  period: string;
  alerts: number;
  compliance_rate: number;
}

interface AuditData {
  total_permits_issued: number;
  permits_with_no_flagged_risk: number;
  compliance_rate: number;
  clause_counts: ClauseCount[];
  trend: TrendPoint[];
  summary: string;
}

interface RuleConfidence {
  rule_name: string;
  description: string;
  original_weight: number;
  current_weight: number;
  confirmed_count: number;
  false_alarm_count: number;
  total_count: number;
  tpr: number;
  adjustments: Array<{
    rule_name: string;
    original_severity: number;
    adjusted_severity: number;
    verdict_ratio: string;
    reason: string;
  }>;
  history: Array<{
    id: number;
    flag_id: string;
    verdict: string;
    timestamp: string;
  }>;
}

export default function ComplianceAuditPage() {
  const [data, setData] = useState<AuditData | null>(null);
  const [confidenceData, setConfidenceData] = useState<RuleConfidence[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    const fetchAllData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [auditRes, confidenceRes] = await Promise.all([
          axios.get<AuditData>(`${apiUrl}/api/compliance-audit`),
          axios.get<RuleConfidence[]>(`${apiUrl}/api/rule-confidence`)
        ]);
        setData(auditRes.data);
        setConfidenceData(confidenceRes.data);
      } catch (err: any) {
        console.error("Failed to fetch compliance audit and confidence data", err);
        setError("Failed to load compliance audit analytics. Ensure python backend is running.");
      } finally {
        setLoading(false);
      }
    };

    fetchAllData();
  }, []);

  // Custom tooltips for Recharts
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 shadow-xl space-y-1.5 text-xs text-slate-200">
          <p className="font-bold text-slate-100">{label}</p>
          {payload.map((pld: any, idx: number) => (
            <p key={idx} className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: pld.color || pld.fill }} />
              {pld.name}: <span className="font-mono font-bold" style={{ color: pld.color || pld.fill }}>{pld.value}{pld.unit || ""}</span>
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Title Header */}
      <div className="border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 rounded-xl border border-emerald-500/30">
            <ShieldCheck className="h-7 w-7 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
              Continuous Compliance Audit
            </h1>
            <p className="mt-1.5 text-xs text-slate-400">
              Automated auditing and continuous compliance monitoring of safety permits and regulatory clauses.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-sm font-semibold flex items-center gap-2">
          <XCircle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 text-slate-400">
          <Loader2 className="h-10 w-10 animate-spin text-emerald-400 mb-3" />
          <span>Analyzing permit directories and safety telemetry audit trails...</span>
        </div>
      ) : !data ? (
        <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-2xl max-w-lg mx-auto">
          <XCircle className="h-12 w-12 text-rose-500 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-slate-200">Compliance Console Offline</h3>
          <p className="text-xs text-slate-400 mt-2 leading-relaxed">
            Unable to communicate with the SentinelGrid analytics engine. Please ensure the Python backend server is running and database is seeded.
          </p>
        </div>
      ) : (
        <>
          {/* Baseline Compliance Rate Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            
            {/* Stat Card 1: Compliance Rate */}
            <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-850 shadow-xl flex items-center justify-between hover:border-slate-800 transition-all relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl group-hover:scale-110 transition-transform" />
              <div className="space-y-1">
                <span className="text-[10px] font-black uppercase text-slate-500 tracking-wider">Permit Compliance Rate</span>
                <div className="text-3xl font-black text-emerald-400">{data.compliance_rate}%</div>
                <p className="text-[9px] text-slate-400">Baseline safety adherence score.</p>
              </div>
              <div className="p-3 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-xl shrink-0">
                <ShieldCheck className="h-6 w-6" />
              </div>
            </div>

            {/* Stat Card 2: Total Permits */}
            <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-850 shadow-xl flex items-center justify-between hover:border-slate-800 transition-all relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-full blur-2xl group-hover:scale-110 transition-transform" />
              <div className="space-y-1">
                <span className="text-[10px] font-black uppercase text-slate-500 tracking-wider">Total Permits Issued</span>
                <div className="text-3xl font-black text-cyan-400">{data.total_permits_issued}</div>
                <p className="text-[9px] text-slate-400">All registered job authorizations.</p>
              </div>
              <div className="p-3 bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded-xl shrink-0">
                <FileText className="h-6 w-6" />
              </div>
            </div>

            {/* Stat Card 3: Compliant Permits */}
            <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-850 shadow-xl flex items-center justify-between hover:border-slate-800 transition-all relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-24 h-24 bg-sky-500/5 rounded-full blur-2xl group-hover:scale-110 transition-transform" />
              <div className="space-y-1">
                <span className="text-[10px] font-black uppercase text-slate-500 tracking-wider">Compliant Permits</span>
                <div className="text-3xl font-black text-sky-400">{data.permits_with_no_flagged_risk}</div>
                <p className="text-[9px] text-slate-400">Permits with no flagged risk factors.</p>
              </div>
              <div className="p-3 bg-sky-500/10 text-sky-400 border border-sky-500/20 rounded-xl shrink-0">
                <CheckCircle2 className="h-6 w-6" />
              </div>
            </div>

            {/* Stat Card 4: Flagged Risks */}
            <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-850 shadow-xl flex items-center justify-between hover:border-slate-800 transition-all relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-24 h-24 bg-rose-500/5 rounded-full blur-2xl group-hover:scale-110 transition-transform" />
              <div className="space-y-1">
                <span className="text-[10px] font-black uppercase text-slate-500 tracking-wider">Flagged Risk Permits</span>
                <div className="text-3xl font-black text-rose-400">{data.total_permits_issued - data.permits_with_no_flagged_risk}</div>
                <p className="text-[9px] text-slate-400">Co-firing permit + sensor violations.</p>
              </div>
              <div className="p-3 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded-xl shrink-0">
                <AlertTriangle className="h-6 w-6 animate-[pulse_2s_infinite]" />
              </div>
            </div>

          </div>

          {/* Dynamic AI Narration Executive Summary */}
          <div className="p-5.5 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-emerald-500/20 shadow-xl relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-3xl animate-pulse" />
            <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-extrabold uppercase tracking-wider mb-2.5">
              <Sparkles className="h-4.5 w-4.5" />
              AI Compliance Auditor Directive
            </div>
            <p className="text-xs text-slate-350 leading-relaxed font-medium font-sans">
              {data.summary}
            </p>
          </div>

          {/* Visualizations Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            
            {/* Chart 1: Bar Chart of Flags per Clause */}
            <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                  <Activity className="h-4.5 w-4.5 text-violet-400" />
                  Flags per Regulatory Clause
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Distribution of compound-risk flag occurrences grouped by regulatory safety clauses.
                </p>
              </div>
              
              <div className="h-72 w-full pt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.clause_counts} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
                    <XAxis 
                      dataKey="clause" 
                      stroke="#64748b" 
                      fontSize={9} 
                      fontWeight="bold"
                      tickLine={false}
                    />
                    <YAxis 
                      stroke="#64748b" 
                      fontSize={9} 
                      fontWeight="bold"
                      tickLine={false}
                      allowDecimals={false}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: '#334155', opacity: 0.15 }} />
                    <Bar 
                      name="Risk Event Flags" 
                      dataKey="count" 
                      fill="url(#barGradient)" 
                      radius={[4, 4, 0, 0]}
                    >
                      {/* Gradient definition in SVG */}
                      <defs>
                        <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.8} />
                          <stop offset="100%" stopColor="#d946ef" stopOpacity={0.2} />
                        </linearGradient>
                      </defs>
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 2: Trend Line of Compliance over Time */}
            <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                  <TrendingUp className="h-4.5 w-4.5 text-cyan-400" />
                  Audit Compliance Rate Trend
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Historical progress showing baseline compliance rate (%) and safety alerts logged.
                </p>
              </div>

              <div className="h-72 w-full pt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.trend} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
                    <XAxis 
                      dataKey="period" 
                      stroke="#64748b" 
                      fontSize={9} 
                      fontWeight="bold"
                      tickLine={false}
                    />
                    <YAxis 
                      stroke="#64748b" 
                      fontSize={9} 
                      fontWeight="bold"
                      tickLine={false}
                      unit="%"
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend 
                      verticalAlign="top" 
                      height={36} 
                      iconType="circle"
                      iconSize={8}
                      wrapperStyle={{ fontSize: '10px', fontWeight: 'bold' }}
                    />
                    <Line
                      name="Adherence Rate"
                      type="monotone"
                      dataKey="compliance_rate"
                      stroke="#06b6d4"
                      strokeWidth={3}
                      dot={{ r: 4, stroke: '#0891b2', strokeWidth: 2, fill: '#slate-950' }}
                      activeDot={{ r: 6 }}
                      unit="%"
                    />
                    <Line
                      name="Incident Warnings"
                      type="monotone"
                      dataKey="alerts"
                      stroke="#f43f5e"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      dot={{ r: 4, stroke: '#e11d48', strokeWidth: 1, fill: '#slate-950' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

          </div>

          {/* Detailed Clauses Table Panel */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-4">
            <div>
              <h3 className="text-sm font-bold text-slate-200">
                Compliance Audit Trail Ledger
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Comprehensive status report of safety directives tracked under facility classification.
              </p>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-[10px] font-black uppercase text-slate-500 tracking-wider">
                    <th className="py-3 px-4">Safety Standard / Directive</th>
                    <th className="py-3 px-4">Description</th>
                    <th className="py-3 px-4 text-center">Fires Logged</th>
                    <th className="py-3 px-4 text-right">Audit Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40">
                  {data.clause_counts.map((item, index) => (
                    <tr key={index} className="hover:bg-slate-950/40 transition-colors">
                      <td className="py-3.5 px-4 font-bold font-mono text-slate-200">{item.clause}</td>
                      <td className="py-3.5 px-4 text-slate-400 leading-normal">{item.description}</td>
                      <td className="py-3.5 px-4 text-center font-mono font-bold text-slate-200">{item.count}</td>
                      <td className="py-3.5 px-4 text-right">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                          item.count === 0 
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                            : item.count === 1
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        }`}>
                          {item.count === 0 ? "Compliant" : item.count === 1 ? "Review Recommended" : "Action Required"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Rule Confidence & alarm fatigue mitigation panel */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-indigo-400" />
                  Evolving Rule Confidence & Alarm Fatigue Mitigation
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Dynamic severity weight adjustments based on rolling safety officer verdicts to prevent alert fatigue.
                </p>
              </div>
              <div className="text-[10px] font-black uppercase text-indigo-450 bg-indigo-500/10 border border-indigo-500/25 px-2.5 py-1 rounded">
                Transparent & Auditable Adaptation
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-[10px] font-black uppercase text-slate-500 tracking-wider">
                    <th className="py-3 px-4">Rule Name</th>
                    <th className="py-3 px-4">Description</th>
                    <th className="py-3 px-4 text-center">Weight (Orig → Curr)</th>
                    <th className="py-3 px-4 text-center">Verdicts (TP / FA)</th>
                    <th className="py-3 px-4 text-center">TPR %</th>
                    <th className="py-3 px-4 text-right">Adjustment Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40">
                  {confidenceData.map((item, index) => {
                    const isAdjusted = item.current_weight < item.original_weight;
                    return (
                      <tr key={index} className="hover:bg-slate-950/40 transition-colors">
                        <td className="py-3.5 px-4 font-bold font-mono text-slate-200">{item.rule_name}</td>
                        <td className="py-3.5 px-4 text-slate-400 leading-normal">{item.description}</td>
                        <td className="py-3.5 px-4 text-center font-mono font-bold">
                          <span className="text-slate-400">{item.original_weight.toFixed(1)}</span>
                          {isAdjusted ? (
                            <>
                              <span className="mx-1.5 text-rose-500 font-extrabold">→</span>
                              <span className="text-rose-450 font-black">{item.current_weight.toFixed(1)}</span>
                            </>
                          ) : (
                            <span className="text-emerald-500 font-normal"> (No Change)</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-center font-mono">
                          <span className="text-emerald-400">{item.confirmed_count}</span>
                          <span className="text-slate-650 mx-1">/</span>
                          <span className="text-rose-450">{item.false_alarm_count}</span>
                        </td>
                        <td className="py-3.5 px-4 text-center font-mono font-bold text-slate-300">
                          {item.total_count > 0 ? `${item.tpr}%` : "—"}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          {isAdjusted ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/20 animate-pulse">
                              Fatigue Mitigated (-{(item.original_weight - item.current_weight).toFixed(1)})
                            </span>
                          ) : item.false_alarm_count > 0 ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20">
                              Monitoring Ratio
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              High Confidence
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Auditable Adjustments Log */}
            {confidenceData.some(item => item.adjustments.length > 0) && (
              <div className="mt-4 p-4.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-2">
                <div className="text-[10px] font-black uppercase text-rose-400 tracking-wider">
                  ⚠️ Active Systemic Severity Weight Adjustments (Audit Trail)
                </div>
                <div className="space-y-1.5">
                  {confidenceData.flatMap(item => item.adjustments).map((adj, idx) => (
                    <div key={idx} className="text-xs text-slate-300 flex items-start gap-2 bg-slate-900/40 p-2.5 rounded border border-slate-850">
                      <span className="h-1.5 w-1.5 rounded-full bg-rose-500 mt-1.5 shrink-0" />
                      <div>
                        <span className="font-bold text-slate-200 font-mono">{adj.rule_name}</span>: {adj.reason}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
