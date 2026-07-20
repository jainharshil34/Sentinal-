"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";
import { HelpCircle, ChevronDown, ChevronUp, Loader2 } from "lucide-react";

const FEATURE_LABELS: Record<string, string> = {
  "Rule_RULE_HOT_WORK_NEAR_GAS_SPIKE": "Active hot work permit present",
  "Rule_RULE_CONFINED_SPACE_NEAR_GAS_SPIKE": "Active confined space permit present",
  "Rule_RULE_ELECTRICAL_WORK_NEAR_GAS_SPIKE": "Active electrical permit present",
  "Rule_RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT": "Overdue equipment maintenance log",
  "Rule_RULE_SILENT_SENSOR_DURING_PERMIT": "Sensor signal silent/unresponsive",
  "Rule_RULE_PERMIT_DURING_ACTIVE_REPAIR": "Active equipment repair in zone",
  "Rule_RULE_MULTI_GAS_COMPOUND_TOXICITY": "Multi-gas synergistic toxicity",
  "Rule_RULE_ADJACENT_ZONE_ESCALATION": "Adjacent zone risk escalation",
  "Zone_Zone-A": "Location in Zone-A (Ventilation)",
  "Zone_Zone-B": "Location in Zone-B (Confined Storage)",
  "Zone_Zone-C": "Location in Zone-C (Acid Gas Valve)",
  "Zone_Zone-D": "Location in Zone-D (Electrical Switch)",
  "Zone_Zone-E": "Location in Zone-E (Refinery Tank)",
  "Zone_Zone-F": "Location in Zone-F (Routine Loading)",
  "Shift_Morning": "Morning operational shift",
  "Shift_Afternoon": "Afternoon operational shift",
  "Shift_Night": "Night operational shift",
  "co_firing_rules": "Concurrent co-firing rules count",
  "days_since_maintenance": "Days elapsed since maintenance",
  "historical_rule_false_alarm_rate": "Historical false alarm rate",
  "zone_incident_frequency": "Historical zone incident frequency"
};

export function getPlainEnglishFeatureName(rawFeature: string): string {
  if (FEATURE_LABELS[rawFeature]) return FEATURE_LABELS[rawFeature];
  const clean = rawFeature.replace(/_onehot$/, "").replace(/^Rule_/, "").replace(/^Zone_/, "");
  return FEATURE_LABELS[clean] || clean.replace(/_/g, " ");
}

interface FeatureImportance {
  feature: string;
  importance: number;
  direction: string;
}

interface AlertExplainabilityChartProps {
  apiUrl?: string;
  featureImportances?: FeatureImportance[];
}

export function AlertExplainabilityChart({ apiUrl, featureImportances }: AlertExplainabilityChartProps) {
  const [expanded, setExpanded] = useState(false);
  const [data, setData] = useState<Array<{ name: string; rawImportance: number; displayValue: number }>>([]);
  const [loading, setLoading] = useState(false);
  const [fetched, setFetched] = useState(false);

  const endpoint = apiUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const formatData = (rawList: FeatureImportance[]) => {
    const top5 = rawList.slice(0, 5);
    const maxVal = Math.max(...top5.map(f => f.importance), 0.001);
    const formatted = top5.map((f) => ({
      name: getPlainEnglishFeatureName(f.feature),
      rawImportance: f.importance,
      displayValue: Number(((f.importance / maxVal) * 100).toFixed(1))
    }));
    setData(formatted);
  };

  useEffect(() => {
    if (expanded && !fetched && !featureImportances) {
      setLoading(true);
      axios.get(`${endpoint}/api/model-performance`)
        .then((res) => {
          const raw = res.data.feature_importances || [];
          formatData(raw);
          setFetched(true);
        })
        .catch((err) => {
          console.error("Failed to load feature importances for explainability", err);
        })
        .finally(() => {
          setLoading(false);
        });
    } else if (featureImportances && data.length === 0) {
      formatData(featureImportances);
    }
  }, [expanded, featureImportances, fetched, endpoint]);

  return (
    <div className="mt-2 pt-2 border-t border-slate-800/60">
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 hover:text-cyan-300 flex items-center gap-1 cursor-pointer transition-all bg-cyan-950/40 hover:bg-cyan-950/80 px-2.5 py-1 rounded border border-cyan-500/20"
      >
        <HelpCircle className="h-3 w-3" />
        <span>Explain this alert</span>
        {expanded ? <ChevronUp className="h-3 w-3 ml-0.5" /> : <ChevronDown className="h-3 w-3 ml-0.5" />}
      </button>

      {expanded && (
        <div className="mt-3 p-3.5 rounded-xl bg-slate-950/90 border border-slate-800/80 space-y-2.5 animate-in fade-in duration-200">
          <div className="text-[11px] font-bold text-slate-300 flex items-center justify-between">
            <span>Why did the AI flag this alert?</span>
            <span className="text-[9px] text-slate-500 font-mono">Logistic Regression Classifier (Top 5 Factors)</span>
          </div>

          {loading ? (
            <div className="flex items-center gap-2 py-4 text-xs text-slate-400 justify-center">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-cyan-400" />
              <span>Loading feature importances...</span>
            </div>
          ) : data.length === 0 ? (
            <p className="text-[10px] text-slate-500">Feature importance data unavailable.</p>
          ) : (
            <div className="w-full h-44 pt-1">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data}
                  layout="vertical"
                  margin={{ top: 0, right: 20, left: 10, bottom: 0 }}
                >
                  <XAxis type="number" domain={[0, 100]} hide />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={180}
                    tick={{ fill: "#94a3b8", fontSize: 9, fontWeight: 600 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    content={({ payload }) => {
                      if (!payload || !payload.length) return null;
                      const item = payload[0].payload;
                      return (
                        <div className="bg-slate-900 border border-slate-700 px-2.5 py-1.5 rounded text-[10px] shadow-xl">
                          <div className="font-bold text-slate-200">{item.name}</div>
                          <div className="text-cyan-400 font-mono font-bold">Relative Weight: {item.displayValue}%</div>
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="displayValue" radius={[0, 4, 4, 0]} barSize={12}>
                    {data.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={index === 0 ? "#38bdf8" : index === 1 ? "#06b6d4" : "#0284c7"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          <p className="text-[9px] text-slate-500 leading-normal italic">
            Relative weight shows feature influence calculated by the offline/online retraining pipeline.
          </p>
        </div>
      )}
    </div>
  );
}
