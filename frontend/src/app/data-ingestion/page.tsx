"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { 
  UploadCloud, 
  CheckCircle2, 
  AlertTriangle, 
  FileSpreadsheet, 
  FileText, 
  ArrowRight,
  Database,
  Play,
  Activity,
  Info,
  Layers,
  ChevronDown
} from "lucide-react";

interface SuggestedMapping {
  [key: string]: string;
}

interface AnalysisResult {
  type: string;
  headers: string[];
  suggested_mapping: SuggestedMapping;
  method?: string;
}

export default function DataIngestionPage() {
  // File upload states
  const [file, setFile] = useState<File | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [selectedType, setSelectedType] = useState<string>("permit");
  const [columnMapping, setColumnMapping] = useState<SuggestedMapping>({});
  const [mappingMethod, setMappingMethod] = useState<string | null>(null);
  const [tagMappings, setTagMappings] = useState<Record<string, { zone: string; gas_type: string }>>({});
  
  // Ingestion results
  const [ingesting, setIngesting] = useState(false);
  const [ingestResult, setIngestResult] = useState<{ count: number; type: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // OPC-UA historian states
  const [tagLogs, setTagLogs] = useState<string>("");
  const [tagIngesting, setTagIngesting] = useState(false);
  const [tagResultCount, setTagResultCount] = useState<number | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch tag mapping table config on load
  useEffect(() => {
    const fetchTagMappings = async () => {
      try {
        const res = await axios.get<Record<string, { zone: string; gas_type: string }>>(`${apiUrl}/api/ingest/tag-mapping`);
        setTagMappings(res.data);
      } catch (err) {
        console.error("Failed to fetch tag mappings:", err);
      }
    };
    fetchTagMappings();
  }, [apiUrl]);

  // Target schema fields
  const schemaOptions = {
    permit: [
      { value: "skip", label: "— Skip Column —" },
      { value: "permit_id", label: "Permit ID (string)" },
      { value: "permit_type", label: "Work Type (string)" },
      { value: "issued_at", label: "Start Date/Time (datetime)" },
      { value: "closed_at", label: "End Date/Time (datetime)" },
      { value: "zone", label: "Zone / Sector (string)" },
      { value: "plant_id", label: "Plant ID (string)" },
      { value: "issued_by", label: "Issued By / Inspector (string)" }
    ],
    maintenance: [
      { value: "skip", label: "— Skip Column —" },
      { value: "equipment_id", label: "Equipment ID / Ref (string)" },
      { value: "zone", label: "Zone / Sector (string)" },
      { value: "event_type", label: "Event Type / Activity (string)" },
      { value: "logged_at", label: "Logged Timestamp (datetime)" },
      { value: "notes", label: "Notes / Description (string)" },
      { value: "plant_id", label: "Plant ID (string)" }
    ]
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setAnalysis(null);
      setIngestResult(null);
      setError(null);
      setMappingMethod(null);
    }
  };

  const handleAnalyze = async (forcedType?: string) => {
    if (!file) return;
    setAnalyzing(true);
    setError(null);
    
    const formData = new FormData();
    formData.append("file", file);

    let url = `${apiUrl}/api/ingest/analyze`;
    if (forcedType) {
      url += `?type=${forcedType}`;
    }

    try {
      const res = await axios.post<AnalysisResult>(url, formData);
      setAnalysis(res.data);
      setSelectedType(res.data.type);
      setMappingMethod(res.data.method || "Rule-based (Fuzzy)");
      
      // Initialize column mapping from suggested mappings
      const initialMap: SuggestedMapping = {};
      res.data.headers.forEach(h => {
        initialMap[h] = res.data.suggested_mapping[h] || "skip";
      });
      setColumnMapping(initialMap);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || "Failed to analyze headers.");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleMappingChange = (header: string, targetField: string) => {
    setColumnMapping(prev => ({
      ...prev,
      [header]: targetField
    }));
  };

  const handleIngest = async () => {
    if (!file || !analysis) return;
    setIngesting(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("type", selectedType);
    
    // Filter out skipped fields
    const finalMapping: SuggestedMapping = {};
    Object.entries(columnMapping).forEach(([h, target]) => {
      if (target !== "skip") {
        finalMapping[h] = target;
      }
    });
    formData.append("mapping", JSON.stringify(finalMapping));

    try {
      const res = await axios.post<{ count: number; type: string }>(`${apiUrl}/api/ingest/upload`, formData);
      setIngestResult(res.data);
      // Reset file selection
      setFile(null);
      setAnalysis(null);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || "Ingestion failed.");
    } finally {
      setIngesting(false);
    }
  };

  // Mock tags generation with realistic SCADA/Historian addresses
  const mockTags = [
    { tag: "ZC.GAS.CH4.PV", value: 3.4, timestamp: new Date().toISOString(), quality: "GOOD" },
    { tag: "ZC.GAS.H2S.PV", value: 5.1, timestamp: new Date().toISOString(), quality: "GOOD" },
    { tag: "40003.CO", value: 12.0, timestamp: new Date().toISOString(), quality: "GOOD" },
    { tag: "ZC.GAS.O2.PV", value: 20.9, timestamp: new Date().toISOString(), quality: "GOOD" }
  ];

  const handleMockTagsGeneration = () => {
    setTagLogs(JSON.stringify(mockTags, null, 2));
    setTagResultCount(null);
  };

  const handleTransmitTags = async () => {
    if (!tagLogs) return;
    setTagIngesting(true);
    try {
      const payload = JSON.parse(tagLogs);
      const res = await axios.post<{ parsed_count: number }>(`${apiUrl}/api/ingest/tag`, payload);
      setTagResultCount(res.data.parsed_count);
    } catch (err: any) {
      alert("Invalid JSON format in tag console!");
    } finally {
      setTagIngesting(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      
      {/* Title */}
      <div className="border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-gradient-to-br from-teal-500/20 to-cyan-500/20 rounded-xl border border-teal-500/30">
            <UploadCloud className="h-7 w-7 text-teal-400" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">
              Industrial Data Ingestion & Mapping Adapter
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Decouple the safety engine from hardcoded formats by mapping messy column layouts and historians to internal schemas.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: File Upload & Column Mapping */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Main uploader widget */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-4">
            <h3 className="text-sm font-bold text-slate-200">CSV & Excel Ingestion Panel</h3>
            
            <div className="border-2 border-dashed border-slate-800 hover:border-slate-700 rounded-xl p-8 text-center transition-colors bg-slate-950/20 relative group">
              <input
                type="file"
                accept=".csv, .xlsx, .xls"
                onChange={handleFileChange}
                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              />
              <FileSpreadsheet className="h-10 w-10 text-slate-500 group-hover:text-teal-400 mx-auto transition-colors" />
              <p className="text-xs text-slate-300 font-bold mt-3">
                {file ? file.name : "Drag & drop file or click to browse"}
              </p>
              <p className="text-[10px] text-slate-500 mt-1">
                Supports messy CSV, XLS, or XLSX permit and repair logs.
              </p>
            </div>

            {file && !analysis && (
              <button
                onClick={() => handleAnalyze()}
                disabled={analyzing}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-black uppercase tracking-wider rounded-xl transition-all cursor-pointer"
              >
                <Activity className="h-4 w-4" />
                {analyzing ? "Analyzing File Headers..." : "Analyze File Headers"}
              </button>
            )}

            {error && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/25 rounded-xl flex items-center gap-2 text-rose-450 text-xs font-mono">
                <AlertTriangle className="h-4.5 w-4.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {ingestResult && (
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/25 rounded-xl flex items-center gap-3 text-emerald-450 text-xs font-semibold">
                <CheckCircle2 className="h-5 w-5 shrink-0" />
                <div>
                  <span className="font-extrabold uppercase font-mono block text-[10px] tracking-wider text-emerald-300">
                    Ingestion Succeeded
                  </span>
                  Parsed and committed <span className="text-white font-black">{ingestResult.count}</span> records to the active {ingestResult.type} ledger!
                </div>
              </div>
            )}
          </div>

          {/* Dynamic Column Mapping Editor */}
          {analysis && (
            <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-slate-200">Schema Mapper Confirmation</h3>
                    {mappingMethod && (
                      <span className={`px-2 py-0.5 rounded-full text-[9px] font-extrabold tracking-wider uppercase border ${
                        mappingMethod.includes("LLM") 
                          ? "bg-purple-500/10 text-purple-400 border-purple-500/30" 
                          : "bg-teal-500/10 text-teal-400 border-teal-500/30"
                      }`}>
                        {mappingMethod}
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    Suggested columns mapped automatically. Adjust targets as needed before ingestion.
                  </p>
                </div>
                
                {/* Type toggle */}
                <div className="flex items-center gap-1 bg-slate-950 border border-slate-800/80 p-1 rounded-lg">
                  <button
                    onClick={() => {
                      setSelectedType("permit");
                      handleAnalyze("permit");
                    }}
                    className={`px-2 py-1 rounded text-[10px] font-bold uppercase transition-all ${
                      selectedType === "permit" ? "bg-teal-500 text-slate-950" : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Permit Log
                  </button>
                  <button
                    onClick={() => {
                      setSelectedType("maintenance");
                      handleAnalyze("maintenance");
                    }}
                    className={`px-2 py-1 rounded text-[10px] font-bold uppercase transition-all ${
                      selectedType === "maintenance" ? "bg-teal-500 text-slate-950" : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Maintenance Log
                  </button>
                </div>
              </div>

              {/* Mappings Form List */}
              <div className="space-y-2 max-h-[350px] overflow-y-auto pr-1">
                {analysis.headers.map((header) => {
                  const mapped = columnMapping[header] || "skip";
                  const currentOptions = selectedType === "permit" ? schemaOptions.permit : schemaOptions.maintenance;
                  
                  return (
                    <div key={header} className="p-3 bg-slate-950/60 rounded-xl border border-slate-850 flex items-center justify-between gap-4 text-xs">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-slate-500 shrink-0" />
                        <span className="font-mono font-bold text-slate-350">{header}</span>
                      </div>
                      
                      <div className="flex items-center gap-2 font-mono text-slate-450 shrink-0">
                        <ArrowRight className="h-3 w-3 text-slate-600" />
                        <div className="relative">
                          <select
                            value={mapped}
                            onChange={(e) => handleMappingChange(header, e.target.value)}
                            className="bg-slate-900 text-slate-200 border border-slate-850 px-2 py-1 rounded text-[10px] font-bold uppercase cursor-pointer appearance-none pr-7 focus:border-teal-500 focus:outline-none"
                          >
                            {currentOptions.map((opt) => (
                              <option key={opt.value} value={opt.value} className="bg-slate-900">
                                {opt.label.toUpperCase()}
                              </option>
                            ))}
                          </select>
                          <ChevronDown className="h-3 w-3 text-slate-500 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Confirm Action */}
              <button
                onClick={handleIngest}
                disabled={ingesting}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-gradient-to-r from-teal-500 to-cyan-600 hover:from-teal-400 hover:to-cyan-500 text-slate-950 text-xs font-black uppercase tracking-wider rounded-xl transition-all cursor-pointer"
              >
                <Layers className="h-4 w-4" />
                {ingesting ? "Ingesting Mapped Records..." : "Confirm & Ingest Logs"}
              </button>
            </div>
          )}
        </div>

        {/* Right Column: Supported Formats & OPC-UA Historian tag parser */}
        <div className="space-y-6">
          
          {/* Supported Formats Side Note */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-4">
            <div className="flex items-center gap-2">
              <Info className="h-4.5 w-4.5 text-teal-400" />
              <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                Supported Integrations
              </h3>
            </div>
            
            <div className="space-y-3 text-[11px] text-slate-400">
              <div className="space-y-1">
                <span className="font-bold text-slate-200 block">1. Excel & CSV Work Logs</span>
                <p>Ingests permits and safety maintenance tasks with automatic header alignment and manual mapping fallback.</p>
              </div>
              <div className="border-t border-slate-800/60 pt-2.5 space-y-1">
                <span className="font-bold text-slate-200 block">2. Tag Historian Telemetry</span>
                <p>Accepts raw tag-value matrices (OPC-UA/Modbus) and parses them into gas levels via tag address maps.</p>
              </div>
            </div>
          </div>

          {/* Active Tag Mapping Table */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-4">
            <div className="flex items-center gap-2">
              <Database className="h-4.5 w-4.5 text-teal-400" />
              <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                Active Tag-to-Zone Map
              </h3>
            </div>
            
            <p className="text-[10px] text-slate-400 leading-relaxed">
              Industrial plant historians publish tag streams. Below is the active configuration mapping tags to plant zones & sensor types.
            </p>
            
            <div className="border border-slate-850 rounded-xl overflow-hidden bg-slate-950/40">
              <div className="max-h-[180px] overflow-y-auto pr-1">
                <table className="w-full text-[10px] font-mono text-left">
                  <thead>
                    <tr className="bg-slate-900 text-slate-400 border-b border-slate-850">
                      <th className="p-2 font-bold uppercase">Historian Tag</th>
                      <th className="p-2 font-bold uppercase">Zone</th>
                      <th className="p-2 font-bold uppercase">Gas</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-850">
                    {Object.keys(tagMappings).length > 0 ? (
                      Object.entries(tagMappings).map(([tag, config]) => (
                        <tr key={tag} className="hover:bg-slate-900/60 transition-colors">
                          <td className="p-2 font-bold text-teal-350">{tag}</td>
                          <td className="p-2 text-slate-300">{config.zone}</td>
                          <td className="p-2 text-emerald-400">{config.gas_type}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={3} className="p-2 text-center text-slate-500 italic">
                          Loading tag mappings...
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* OPC-UA Modbus tag parser simulator */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-4">
            <div>
              <h3 className="text-sm font-bold text-slate-200">OPC-UA Tag Stream Simulator</h3>
              <p className="text-[10px] text-slate-500 mt-0.5">
                Simulates real-world historian telemetry using tag-to-zone mappings.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <button
                  onClick={handleMockTagsGeneration}
                  className="px-3 py-1.5 bg-slate-950 hover:bg-slate-800 text-teal-450 border border-slate-800 rounded-lg text-[10px] font-bold uppercase transition-all cursor-pointer"
                >
                  Load Mock Tag JSON
                </button>
                {tagLogs && (
                  <button
                    onClick={handleTransmitTags}
                    disabled={tagIngesting}
                    className="px-3 py-1.5 bg-teal-500 hover:bg-teal-400 text-slate-950 rounded-lg text-[10px] font-bold uppercase flex items-center gap-1 transition-all cursor-pointer"
                  >
                    <Play className="h-3 w-3 fill-slate-950" />
                    {tagIngesting ? "Posting..." : "Transmit"}
                  </button>
                )}
              </div>

              {tagLogs && (
                <textarea
                  value={tagLogs}
                  onChange={(e) => setTagLogs(e.target.value)}
                  rows={8}
                  className="w-full bg-slate-950 text-emerald-450 border border-slate-850 p-3 rounded-lg text-[10px] font-mono focus:outline-none focus:border-slate-700"
                />
              )}

              {tagResultCount !== null && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/25 rounded-lg flex items-center gap-2 text-emerald-450 text-[11px] font-semibold">
                  <Database className="h-4 w-4 shrink-0" />
                  <span>Successfully mapped & committed {tagResultCount} tags to Gas readings.</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
