"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Search, 
  Brain, 
  Loader2, 
  ShieldAlert, 
  HelpCircle,
  TrendingUp,
  FileText,
  AlertTriangle,
  Link as LinkIcon,
  Sparkles,
  ArrowRight
} from "lucide-react";

interface IncidentMatch {
  id: number;
  text: string;
  rule_type: string;
  regulatory_clause: string;
  zone: string;
  score: number;
  reasons: string[];
  source?: string;
}

interface Pattern {
  category: string;
  count: number;
  percentage: number;
  description: string;
  type: "clause" | "rule";
  key: string;
}

const SAMPLE_QUERIES = [
  "Hot work grinding with rising methane levels",
  "Confined space entry and carbon monoxide poisoning",
  "Overdue equipment maintenance during active permit",
  "Methane sensor silent failure in process room",
  "Synergistic toxicity from multiple gases",
  "Clerical error on permit with no gas present"
];

export default function PatternIntelligence() {
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<IncidentMatch[]>([]);
  const [briefing, setBriefing] = useState<string | null>(null);
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [loadingPatterns, setLoadingPatterns] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch systemic risk patterns on load
  useEffect(() => {
    fetchPatterns();
  }, []);

  const fetchPatterns = async () => {
    setLoadingPatterns(true);
    try {
      const res = await axios.get<Pattern[]>(`${apiUrl}/api/incident-intelligence/patterns`);
      setPatterns(res.data);
    } catch (err) {
      console.error("Failed to fetch patterns", err);
    } finally {
      setLoadingPatterns(false);
    }
  };

  const handleSearch = async (searchQuery: string) => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    setError(null);
    setBriefing(null);
    try {
      const res = await axios.post<{ incidents: IncidentMatch[]; synthesized_briefing: string }>(
        `${apiUrl}/api/incident-intelligence/query`,
        { query: searchQuery }
      );
      setResults(res.data.incidents || []);
      setBriefing(res.data.synthesized_briefing || null);
    } catch (err) {
      console.error("Query failed", err);
      setError("Failed to query incident intelligence. Make sure backend is running.");
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const selectSampleQuery = (q: string) => {
    setQuery(q);
    handleSearch(q);
  };

  const getReasonBadgeStyle = (reason: string) => {
    const r = reason.toLowerCase();
    if (r.includes("semantic")) {
      return "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20";
    }
    if (r.includes("rule")) {
      return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    }
    if (r.includes("clause")) {
      return "bg-violet-500/10 text-violet-400 border border-violet-500/20";
    }
    return "bg-slate-800 text-slate-300 border border-slate-700";
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Title Header */}
      <div className="border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 rounded-xl border border-emerald-500/30">
            <Brain className="h-7 w-7 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
              Incident Pattern Intelligence
            </h1>
            <p className="mt-1.5 text-xs text-slate-400">
              Semantic analysis and multi-hop graph reasoning identifying systemic safety correlations across past incidents.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Columns - Query and Results */}
        <div className="lg:col-span-2 space-y-6">
          {/* Query Console */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-4">
            <h2 className="text-base font-bold text-slate-200 flex items-center gap-2">
              <Search className="h-4.5 w-4.5 text-emerald-400" />
              Safety Inquiry Console
            </h2>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch(query)}
                  placeholder="Enter natural language safety query (e.g. 'hot work grinding near methane')..."
                  className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500/50 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none transition-all pr-10"
                />
                <Brain className="absolute right-3.5 top-3.5 h-4.5 w-4.5 text-slate-600" />
              </div>
              <button
                onClick={() => handleSearch(query)}
                disabled={searching}
                className="px-6 py-3 bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-400 hover:to-cyan-400 text-slate-950 font-bold rounded-xl text-sm transition-all duration-300 shadow-md shadow-emerald-500/10 flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {searching ? (
                  <Loader2 className="h-4 w-4 animate-spin text-slate-950" />
                ) : (
                  <>
                    Analyze
                    <ArrowRight className="h-4 w-4 text-slate-950" />
                  </>
                )}
              </button>
            </div>

            {/* Sample Queries List */}
            <div className="space-y-2">
              <span className="text-[10px] uppercase font-bold tracking-widest text-slate-500">
                Suggested Scenarios
              </span>
              <div className="flex flex-wrap gap-1.5">
                {SAMPLE_QUERIES.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => selectSampleQuery(q)}
                    className="px-3 py-1.5 bg-slate-950/60 hover:bg-slate-900 text-xs text-slate-400 hover:text-slate-200 border border-slate-850 rounded-lg transition-colors cursor-pointer"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Results Console */}
          <div className="space-y-4">
            <h2 className="text-sm font-extrabold uppercase tracking-widest text-slate-450 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-cyan-400" />
              Intelligent Search Matches ({results.length})
            </h2>

            {error && (
              <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-sm font-semibold">
                {error}
              </div>
            )}

            {!searching && briefing && (
              <div className="p-5 rounded-2xl bg-gradient-to-br from-indigo-950/20 via-slate-900 to-slate-950 border border-indigo-500/30 shadow-xl shadow-indigo-500/5 space-y-2">
                <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs uppercase tracking-wider">
                  <Brain className="h-4.5 w-4.5" />
                  AI-Synthesized Pattern Briefing
                </div>
                <p className="text-xs text-slate-200 leading-relaxed font-semibold">
                  {briefing}
                </p>
              </div>
            )}

            {searching ? (
              <div className="flex flex-col items-center justify-center py-20 text-slate-400 bg-slate-900/30 border border-slate-900 rounded-2xl">
                <Loader2 className="h-10 w-10 animate-spin text-emerald-400 mb-3" />
                <span className="text-sm">Executing semantic query & knowledge graph traversal...</span>
              </div>
            ) : results.length === 0 ? (
              <div className="p-12 text-center bg-slate-900/20 rounded-2xl border border-slate-900 text-slate-500 flex flex-col items-center justify-center">
                <HelpCircle className="h-10 w-10 text-slate-700 mb-3" />
                <span className="text-sm font-bold text-slate-400">Inquiry Awaiting Input</span>
                <span className="text-xs text-slate-500 mt-1 max-w-sm">
                  Use the inquiry console above to lookup past incident files. Returns semantic and graph matches.
                </span>
              </div>
            ) : (
              <div className="space-y-4">
                {results.map((match) => (
                  <div
                    key={match.id}
                    className="p-5 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-850 hover:border-slate-700 transition-all duration-200 flex flex-col gap-3"
                  >
                    {/* Header */}
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2.5">
                        <span className="text-[10px] font-black uppercase bg-slate-950 border border-slate-800 text-slate-350 px-2 py-0.5 rounded font-mono">
                          ID: #{match.id}
                        </span>
                        <span className="text-[10px] font-black uppercase bg-slate-950 border border-slate-800 text-slate-350 px-2 py-0.5 rounded font-mono">
                          {match.zone}
                        </span>
                        <span className="text-[10px] font-black uppercase bg-slate-950 border border-slate-800 text-slate-350 px-2 py-0.5 rounded font-mono">
                          {match.regulatory_clause}
                        </span>
                        {match.source === "real_incident" ? (
                          <span className="text-[10px] font-black uppercase bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded font-mono">
                            Real Incident (CSB)
                          </span>
                        ) : (
                          <span className="text-[10px] font-black uppercase bg-purple-500/10 border border-purple-500/20 text-purple-400 px-2 py-0.5 rounded font-mono">
                            Synthetic Scenario
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] font-bold text-slate-400">
                        Match Score: <span className="text-emerald-400">{(match.score * 100).toFixed(0)}%</span>
                      </div>
                    </div>

                    {/* Prose */}
                    <p className="text-xs text-slate-200 leading-relaxed font-medium">
                      {match.text}
                    </p>

                    {/* Match Reasons */}
                    <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-slate-800/40">
                      <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest mr-1.5">
                        REASON RETRIEVED:
                      </span>
                      {match.reasons.map((reason, idx) => (
                        <span
                          key={idx}
                          className={`px-2.5 py-0.5 rounded text-[10px] font-extrabold uppercase flex items-center gap-1 transition-all ${getReasonBadgeStyle(reason)}`}
                        >
                          <LinkIcon className="h-3 w-3 shrink-0" />
                          {reason}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Systemic Risk Patterns */}
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-5">
            <div>
              <h2 className="text-base font-bold text-slate-200 flex items-center gap-2">
                <TrendingUp className="h-4.5 w-4.5 text-cyan-400" />
                Systemic Risk Patterns
              </h2>
              <p className="text-[11px] text-slate-400 mt-1">
                Deep cross-corpus clustering revealing the regulatory clauses and rules linked to the most near-misses.
              </p>
            </div>

            {loadingPatterns ? (
              <div className="flex flex-col items-center justify-center py-12 text-slate-500">
                <Loader2 className="h-8 w-8 animate-spin text-cyan-400 mb-2" />
                <span className="text-xs">Analyzing historical corpus...</span>
              </div>
            ) : (
              <div className="space-y-4">
                {patterns.slice(0, 8).map((pattern, idx) => (
                  <div key={idx} className="space-y-1.5 p-3 rounded-xl bg-slate-950/40 border border-slate-850 hover:border-slate-800 transition-colors">
                    <div className="flex justify-between items-center text-xs">
                      <div className="flex items-center gap-2">
                        <span className="text-slate-200 font-bold font-mono text-[11px]">
                          {pattern.key}
                        </span>
                        <span className={`text-[8px] px-1.5 py-0.2 rounded font-black uppercase ${
                          pattern.type === "clause" 
                            ? "bg-violet-500/10 text-violet-400 border border-violet-500/20" 
                            : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        }`}>
                          {pattern.type}
                        </span>
                      </div>
                      <span className="text-[11px] font-black text-slate-300">
                        {pattern.count} incidents
                      </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${pattern.percentage}%` }}
                        className={`h-full rounded-full bg-gradient-to-r ${
                          pattern.type === "clause" 
                            ? "from-violet-500 to-fuchsia-500 shadow-md shadow-violet-500/25" 
                            : "from-emerald-500 to-cyan-500 shadow-md shadow-emerald-500/25"
                        }`}
                      />
                    </div>

                    <p className="text-[10px] text-slate-400 leading-normal font-medium">
                      {pattern.description}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
