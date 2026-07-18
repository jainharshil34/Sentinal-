"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { 
  FileText, 
  PlusCircle, 
  Search, 
  Filter, 
  Calendar, 
  ShieldAlert, 
  MapPin, 
  UserCheck, 
  TrendingUp, 
  AlertTriangle,
  Info,
  CheckCircle2
} from "lucide-react";

interface Incident {
  id: number;
  date: string;
  zone: string;
  category: string;
  contributing_factors: string;
  related_rule_type?: string;
  regulatory_clause?: string;
  resolution_notes: string;
  logged_by_role: string;
  severity_level: string;
  source?: string;
}

export default function IncidentLogPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  
  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [filterZone, setFilterZone] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterSeverity, setFilterSeverity] = useState("");

  // Form State
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split("T")[0],
    zone: "Zone-A",
    category: "near_miss",
    contributing_factors: "",
    related_rule_type: "None",
    regulatory_clause: "",
    resolution_notes: "",
    logged_by_role: "Safety Officer",
    severity_level: "first-aid only"
  });

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchIncidents = async () => {
    setLoading(true);
    try {
      const res = await axios.get<Incident[]>(`${apiUrl}/api/incident-history`);
      setIncidents(res.data);
    } catch (err: any) {
      console.error(err);
      setError("Failed to fetch incident log history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, [apiUrl]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    if (!formData.contributing_factors.trim() || !formData.resolution_notes.trim()) {
      setError("Please fill in both the contributing factors and resolution notes.");
      return;
    }

    try {
      // Send the incident to the database
      const res = await axios.post<Incident>(`${apiUrl}/api/incident-history`, {
        ...formData,
        date: new Date(formData.date).toISOString()
      });

      setSuccessMsg("Incident report logged successfully! RAG embeddings and systemic risk patterns have been regenerated.");
      
      // Reset form (except date/role defaults)
      setFormData(prev => ({
        ...prev,
        contributing_factors: "",
        regulatory_clause: "",
        resolution_notes: "",
        related_rule_type: "None"
      }));

      // Re-fetch incident history
      fetchIncidents();
      
      // Auto-clear success message after 5 seconds
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || "Failed to submit new incident.");
    }
  };

  // Filtered incidents calculation
  const filteredIncidents = incidents.filter(inc => {
    const matchesSearch = 
      inc.contributing_factors.toLowerCase().includes(searchTerm.toLowerCase()) || 
      inc.resolution_notes.toLowerCase().includes(searchTerm.toLowerCase()) || 
      (inc.regulatory_clause && inc.regulatory_clause.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesZone = filterZone ? inc.zone === filterZone : true;
    const matchesCategory = filterCategory ? inc.category === filterCategory : true;
    const matchesSeverity = filterSeverity ? inc.severity_level === filterSeverity : true;

    return matchesSearch && matchesZone && matchesCategory && matchesSeverity;
  });

  const getCategoryBadgeClass = (category: string) => {
    switch (category) {
      case "fatality":
        return "bg-rose-500/10 text-rose-450 border-rose-500/20";
      case "injury":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "equipment_failure":
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/20";
      case "repair_log":
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/20";
    }
  };

  const getSeverityBadgeClass = (severity: string) => {
    switch (severity) {
      case "fatality":
        return "bg-red-500/20 text-red-450 border-red-500/35";
      case "lost-time injury":
        return "bg-amber-500/20 text-amber-400 border-amber-500/35";
      default:
        return "bg-emerald-500/10 text-emerald-450 border-emerald-500/20";
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      
      {/* Title */}
      <div className="border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-gradient-to-br from-emerald-500/20 to-teal-500/20 rounded-xl border border-emerald-500/30">
            <FileText className="h-7 w-7 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">
              Incident & Repair History Log
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Maintain institutional, Factories Act compliance records without PII, continuously retraining safety threat pattern models.
            </p>
          </div>
        </div>
      </div>

      {/* Info grow-notice banner */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/30 to-cyan-950/20 border border-emerald-500/20 flex items-start gap-3">
        <Info className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300">
          <span className="font-bold text-white block mb-0.5">Continuous Threat Learning Active</span>
          This log grows over time — the more incidents and repairs your team records, the more risk patterns SentinelGrid can identify before they recur. Added logs are dynamically embedded using our local RAG pipeline to inform the live risk scoring engine.
        </div>
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/25 rounded-xl flex items-center gap-3 text-emerald-400 text-xs font-semibold animate-in fade-in duration-300">
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/25 rounded-xl flex items-center gap-3 text-rose-455 text-xs font-mono">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Filter & Incident List Table */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Filters card */}
          <div className="p-5 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-4">
            <div className="flex items-center gap-2 text-slate-200 font-bold text-xs uppercase tracking-wider">
              <Filter className="h-4 w-4 text-emerald-400" />
              <span>Search & Filters</span>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              <div className="sm:col-span-2 relative">
                <input
                  type="text"
                  placeholder="Search factors, resolutions..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full bg-slate-950 text-xs text-slate-200 border border-slate-850 rounded-lg pl-9 pr-4 py-2 focus:outline-none focus:border-emerald-500"
                />
                <Search className="h-4 w-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              </div>
              
              <div>
                <select
                  value={filterZone}
                  onChange={(e) => setFilterZone(e.target.value)}
                  className="w-full bg-slate-950 text-xs text-slate-200 border border-slate-850 rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500 appearance-none cursor-pointer"
                >
                  <option value="">All Zones</option>
                  <option value="Zone-A">Zone-A</option>
                  <option value="Zone-B">Zone-B</option>
                  <option value="Zone-C">Zone-C</option>
                  <option value="Zone-D">Zone-D</option>
                  <option value="Zone-E">Zone-E</option>
                  <option value="Zone-F">Zone-F</option>
                </select>
              </div>

              <div>
                <select
                  value={filterCategory}
                  onChange={(e) => setFilterCategory(e.target.value)}
                  className="w-full bg-slate-950 text-xs text-slate-200 border border-slate-850 rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500 appearance-none cursor-pointer"
                >
                  <option value="">All Categories</option>
                  <option value="near_miss">Near Miss</option>
                  <option value="injury">Injury</option>
                  <option value="fatality">Fatality</option>
                  <option value="equipment_failure">Equipment Failure</option>
                  <option value="repair_log">Repair Log</option>
                </select>
              </div>
            </div>
          </div>

          {/* List Table Card */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl overflow-hidden">
            <div className="flex justify-between items-center mb-4">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Logged Institutional History ({filteredIncidents.length})
              </span>
            </div>

            {loading ? (
              <div className="py-12 text-center text-slate-500 text-xs font-mono">
                Loading Incident Log Database...
              </div>
            ) : filteredIncidents.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-xs italic">
                No incidents match the search criteria.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 font-bold uppercase text-[10px]">
                      <th className="py-3 px-2">Date / Zone</th>
                      <th className="py-3 px-2">Classification</th>
                      <th className="py-3 px-2">Contributing Factors</th>
                      <th className="py-3 px-2">Resolution / Role</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-850">
                    {filteredIncidents.map((inc) => (
                      <tr key={inc.id} className="hover:bg-slate-900/40 transition-colors">
                        <td className="py-4 px-2 space-y-1 text-slate-350 shrink-0">
                          <div className="flex items-center gap-1 font-mono text-[10px] text-slate-400">
                            <Calendar className="h-3 w-3 shrink-0" />
                            <span>{new Date(inc.date).toLocaleDateString()}</span>
                          </div>
                          <div className="flex items-center gap-1 font-bold text-white text-[11px]">
                            <MapPin className="h-3.5 w-3.5 text-emerald-450 shrink-0" />
                            <span>{inc.zone}</span>
                          </div>
                        </td>
                        
                        <td className="py-4 px-2 space-y-1">
                          <span className={`px-2 py-0.5 rounded-md text-[9px] font-bold uppercase border block w-max ${getCategoryBadgeClass(inc.category)}`}>
                            {inc.category.replace("_", " ")}
                          </span>
                          <span className={`px-2 py-0.5 rounded-md text-[9px] font-bold uppercase border block w-max ${getSeverityBadgeClass(inc.severity_level)}`}>
                            {inc.severity_level}
                          </span>
                          {inc.source === "real_incident" ? (
                            <span className="px-2 py-0.5 rounded-md text-[9px] font-bold uppercase border block w-max bg-indigo-500/10 text-indigo-400 border-indigo-500/20">
                              Real Incident (CSB)
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-md text-[9px] font-bold uppercase border block w-max bg-purple-500/10 text-purple-400 border-purple-500/20">
                              Synthetic Scenario
                            </span>
                          )}
                        </td>
                        
                        <td className="py-4 px-2 max-w-xs">
                          <p className="text-slate-350 font-medium leading-relaxed break-words line-clamp-3 hover:line-clamp-none transition-all cursor-pointer" title="Click to expand">
                            {inc.contributing_factors}
                          </p>
                          {inc.regulatory_clause && (
                            <div className="mt-1 text-[10px] font-mono text-cyan-400 font-bold">
                              Clause: {inc.regulatory_clause}
                            </div>
                          )}
                          {inc.related_rule_type && (
                            <div className="text-[10px] font-mono text-purple-400">
                              Rule: {inc.related_rule_type}
                            </div>
                          )}
                        </td>

                        <td className="py-4 px-2 space-y-2">
                          <p className="text-slate-400 text-[11px] leading-relaxed break-words">
                            {inc.resolution_notes}
                          </p>
                          <div className="flex items-center gap-1 text-[10px] font-mono font-bold text-slate-500">
                            <UserCheck className="h-3 w-3 shrink-0" />
                            <span>By: {inc.logged_by_role}</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Add New Incident Form */}
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 shadow-xl space-y-5">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <PlusCircle className="h-5 w-5 text-emerald-400" />
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
                Log New Accident / Repair
              </h3>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              
              <div className="grid grid-cols-2 gap-3">
                {/* Date */}
                <div className="space-y-1">
                  <label className="text-slate-400 font-bold block">Incident Date</label>
                  <input
                    type="date"
                    name="date"
                    value={formData.date}
                    onChange={handleInputChange}
                    className="w-full bg-slate-950 border border-slate-855 p-2 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
                  />
                </div>
                
                {/* Zone */}
                <div className="space-y-1">
                  <label className="text-slate-400 font-bold block">Zone / Sector</label>
                  <select
                    name="zone"
                    value={formData.zone}
                    onChange={handleInputChange}
                    className="w-full bg-slate-950 border border-slate-855 p-2 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500 cursor-pointer"
                  >
                    <option value="Zone-A">Zone-A (Methane Grinding)</option>
                    <option value="Zone-B">Zone-B (Battery Prep)</option>
                    <option value="Zone-C">Zone-C (Coke Oven Battery)</option>
                    <option value="Zone-D">Zone-D (Switch Room)</option>
                    <option value="Zone-E">Zone-E (Acid Station)</option>
                    <option value="Zone-F">Zone-F (Loading Bay)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {/* Category */}
                <div className="space-y-1">
                  <label className="text-slate-400 font-bold block">Log Category</label>
                  <select
                    name="category"
                    value={formData.category}
                    onChange={handleInputChange}
                    className="w-full bg-slate-950 border border-slate-855 p-2 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500 cursor-pointer"
                  >
                    <option value="near_miss">Near Miss</option>
                    <option value="injury">Injury</option>
                    <option value="fatality">Fatality</option>
                    <option value="equipment_failure">Equipment Failure</option>
                    <option value="repair_log">Repair Log</option>
                  </select>
                </div>

                {/* Severity */}
                <div className="space-y-1">
                  <label className="text-slate-400 font-bold block">Severity Level</label>
                  <select
                    name="severity_level"
                    value={formData.severity_level}
                    onChange={handleInputChange}
                    className="w-full bg-slate-950 border border-slate-855 p-2 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500 cursor-pointer"
                  >
                    <option value="first-aid only">First-aid Only</option>
                    <option value="lost-time injury">Lost-time Injury</option>
                    <option value="fatality">Fatality</option>
                  </select>
                </div>
              </div>

              {/* Logged by role */}
              <div className="space-y-1">
                <label className="text-slate-400 font-bold block">Logged By Role (No PII)</label>
                <select
                  name="logged_by_role"
                  value={formData.logged_by_role}
                  onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-855 p-2 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500 cursor-pointer"
                >
                  <option value="Safety Officer">Safety Officer</option>
                  <option value="Shift Supervisor">Shift Supervisor</option>
                  <option value="Operations Manager">Operations Manager</option>
                  <option value="Safety Inspector">Safety Inspector</option>
                </select>
              </div>

              {/* Related Rule Type */}
              <div className="space-y-1">
                <label className="text-slate-400 font-bold block">Related Compound-Risk Rule</label>
                <select
                  name="related_rule_type"
                  value={formData.related_rule_type}
                  onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-855 p-2 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500 cursor-pointer font-mono text-[10px]"
                >
                  <option value="None">None / Unsupported Rule</option>
                  <option value="RULE_HOT_WORK_NEAR_GAS_SPIKE">RULE_HOT_WORK_NEAR_GAS_SPIKE</option>
                  <option value="RULE_CONFINED_SPACE_NEAR_GAS_SPIKE">RULE_CONFINED_SPACE_NEAR_GAS_SPIKE</option>
                  <option value="RULE_ELECTRICAL_WORK_NEAR_GAS_SPIKE">RULE_ELECTRICAL_WORK_NEAR_GAS_SPIKE</option>
                  <option value="RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT">RULE_OVERDUE_MAINTENANCE_ACTIVE_PERMIT</option>
                  <option value="RULE_SILENT_SENSOR_DURING_PERMIT">RULE_SILENT_SENSOR_DURING_PERMIT</option>
                  <option value="RULE_PERMIT_DURING_ACTIVE_REPAIR">RULE_PERMIT_DURING_ACTIVE_REPAIR</option>
                  <option value="RULE_MULTI_GAS_COMPOUND_TOXICITY">RULE_MULTI_GAS_COMPOUND_TOXICITY</option>
                </select>
              </div>

              {/* Regulatory Clause */}
              <div className="space-y-1">
                <label className="text-slate-400 font-bold block">Regulatory Clause (e.g. OISD 105)</label>
                <input
                  type="text"
                  name="regulatory_clause"
                  placeholder="OISD Standard 105 Section 4.1"
                  value={formData.regulatory_clause}
                  onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-855 p-2 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>

              {/* Contributing factors */}
              <div className="space-y-1">
                <label className="text-slate-400 font-bold block">Contributing Factors / Description</label>
                <textarea
                  name="contributing_factors"
                  rows={3}
                  placeholder="Describe the incident, pooling gas, overdue checks, ignition source details..."
                  value={formData.contributing_factors}
                  onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-855 p-2 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>

              {/* Resolution Notes */}
              <div className="space-y-1">
                <label className="text-slate-400 font-bold block">Resolution & Correction Notes</label>
                <textarea
                  name="resolution_notes"
                  rows={3}
                  placeholder="Describe standard corrective measures, isolation locks, equipment recalibration..."
                  value={formData.resolution_notes}
                  onChange={handleInputChange}
                  className="w-full bg-slate-950 border border-slate-855 p-2 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-black uppercase tracking-wider rounded-xl transition-all cursor-pointer shadow-lg shadow-emerald-950/40"
              >
                <ShieldAlert className="h-4.5 w-4.5" />
                <span>Log Accident Record</span>
              </button>

            </form>
          </div>
        </div>

      </div>
    </div>
  );
}
