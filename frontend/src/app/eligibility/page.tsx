"use client";

import React, { useEffect, useState, useTransition, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ShieldCheck,
  AlertTriangle,
  Play,
  Download,
  Filter,
  Search,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Info,
  RefreshCw,
  FileSpreadsheet,
} from "lucide-react";
import { Header } from "@/components/Header";
import { StatusBadge } from "@/components/StatusBadge";
import { fetchApi, getExportUrl } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface DriveSummary {
  id: string;
  employer_name: string;
  drive_title: string;
  min_cgpa: number;
  eligible_branches: string;
  max_backlogs: number;
  consent_required: boolean;
  criteria_version: number;
}

interface EvaluatedStudent {
  student_id: string;
  full_name: string;
  email: string;
  branch: string;
  cgpa: number;
  active_backlogs: number;
  consent_given: boolean;
  is_eligible: boolean;
  reason: string;
  failure_reasons: string[];
  rules_version: string;
  evaluated_at: string;
}

function EligibilityContent() {
  const searchParams = useSearchParams();
  const initialDriveId = searchParams.get("drive_id") || "";

  const [drives, setDrives] = useState<DriveSummary[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<string>(initialDriveId);
  const [activeDrive, setActiveDrive] = useState<DriveSummary | null>(null);
  const [students, setStudents] = useState<EvaluatedStudent[]>([]);
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  // Load drives
  useEffect(() => {
    fetchApi<DriveSummary[]>("/drives").then((data) => {
      setDrives(data);
      if (!selectedDriveId && data.length > 0) {
        setSelectedDriveId(data[0].id);
      }
    });
  }, []);

  const loadEligibility = async (driveId: string) => {
    if (!driveId) return;
    try {
      setLoading(true);
      let query = `/drives/${driveId}/eligibility?`;
      if (statusFilter === "eligible") query += "status=eligible&";
      if (statusFilter === "excluded") query += "status=excluded&";
      if (search) query += `search=${encodeURIComponent(search)}&`;

      const res = await fetchApi<{ drive: DriveSummary; total_count: number; students: EvaluatedStudent[] }>(query);
      setActiveDrive(res.drive);
      setStudents(res.students);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDriveId) {
      loadEligibility(selectedDriveId);
    }
  }, [selectedDriveId, statusFilter]);

  const handleRunEvaluation = async () => {
    if (!selectedDriveId) return;
    try {
      setEvaluating(true);
      await fetchApi(`/drives/${selectedDriveId}/evaluate`, { method: "POST" });
      await loadEligibility(selectedDriveId);
    } catch (err: any) {
      alert(`Evaluation failed: ${err.message}`);
    } finally {
      setEvaluating(false);
    }
  };

  const eligibleCount = students.filter((s) => s.is_eligible).length;
  const excludedCount = students.filter((s) => !s.is_eligible).length;

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Deterministic Eligibility Analysis"
        subtitle="Rule-based evaluation engine with explainable criteria breakdown and boundary verification"
      />

      <div className="p-8 space-y-8 max-w-7xl">
        {/* Drive Selector and Controls */}
        <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-950/60 border border-indigo-800/60 rounded-lg text-indigo-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block">
                Select Placement Drive
              </label>
              <select
                value={selectedDriveId}
                onChange={(e) => setSelectedDriveId(e.target.value)}
                className="bg-[#222226] border border-[#27272A] rounded-lg px-3 py-1.5 text-xs text-zinc-100 font-semibold focus:outline-none focus:border-indigo-500 mt-1"
              >
                {drives.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.employer_name} — {d.drive_title} (v{d.criteria_version})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            {selectedDriveId && (
              <>
                <a
                  href={getExportUrl(`/drives/${selectedDriveId}/eligibility/export?format=csv`)}
                  className="px-3 py-1.5 bg-[#222226] hover:bg-zinc-800 border border-[#27272A] text-zinc-300 rounded-lg text-xs font-medium flex items-center gap-2 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  Export Roster (CSV)
                </a>

                <a
                  href={getExportUrl(`/drives/${selectedDriveId}/eligibility/export?format=xlsx`)}
                  className="px-3 py-1.5 bg-[#222226] hover:bg-zinc-800 border border-[#27272A] text-zinc-300 rounded-lg text-xs font-medium flex items-center gap-2 transition-colors"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  Export Report (XLSX)
                </a>

                <button
                  onClick={handleRunEvaluation}
                  disabled={evaluating}
                  className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm shadow-indigo-600/30 transition-colors"
                >
                  <Play className={`w-3.5 h-3.5 ${evaluating ? "animate-spin" : ""}`} />
                  {evaluating ? "Evaluating Roster..." : "Run Evaluation Rules"}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Applied Rules Policy Banner */}
        {activeDrive && (
          <div className="bg-[#141417] border border-[#27272A] rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Applied Employer Policy (Rules v2026.1-deterministic • Policy v{activeDrive.criteria_version})
              </span>
              <span className="text-[11px] text-zinc-500 font-mono">
                Boundary: CGPA ≥ {activeDrive.min_cgpa.toFixed(1)} • Backlogs ≤ {activeDrive.max_backlogs}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <div className="bg-[#18181B] p-2.5 rounded border border-[#27272A]">
                <span className="text-zinc-500 block">Min CGPA</span>
                <span className="font-mono font-bold text-zinc-100">{activeDrive.min_cgpa.toFixed(1)}</span>
              </div>
              <div className="bg-[#18181B] p-2.5 rounded border border-[#27272A]">
                <span className="text-zinc-500 block">Permitted Branches</span>
                <span className="font-mono font-bold text-zinc-100">{activeDrive.eligible_branches}</span>
              </div>
              <div className="bg-[#18181B] p-2.5 rounded border border-[#27272A]">
                <span className="text-zinc-500 block">Max Permitted Backlogs</span>
                <span className="font-mono font-bold text-zinc-100">{activeDrive.max_backlogs}</span>
              </div>
              <div className="bg-[#18181B] p-2.5 rounded border border-[#27272A]">
                <span className="text-zinc-500 block">Consent Verification</span>
                <span className="font-bold text-zinc-100">
                  {activeDrive.consent_required ? "Mandatory Opt-in" : "Not Required"}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Breakdown Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-4 flex items-center justify-between">
            <div>
              <span className="text-xs text-zinc-400 uppercase font-semibold">Total Evaluated</span>
              <div className="text-2xl font-bold text-zinc-100 mt-1">{students.length}</div>
            </div>
            <div className="p-2.5 bg-zinc-800 rounded-lg text-zinc-300">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-4 flex items-center justify-between">
            <div>
              <span className="text-xs text-emerald-400 uppercase font-semibold">Eligible Roster</span>
              <div className="text-2xl font-bold text-emerald-300 mt-1">{eligibleCount}</div>
            </div>
            <div className="p-2.5 bg-emerald-950/60 border border-emerald-800/60 rounded-lg text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-4 flex items-center justify-between">
            <div>
              <span className="text-xs text-rose-400 uppercase font-semibold">Excluded Candidates</span>
              <div className="text-2xl font-bold text-rose-300 mt-1">{excludedCount}</div>
            </div>
            <div className="p-2.5 bg-rose-950/60 border border-rose-800/60 rounded-lg text-rose-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setStatusFilter("all")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                statusFilter === "all"
                  ? "bg-zinc-200 text-zinc-900 font-bold"
                  : "bg-[#18181B] text-zinc-400 hover:text-zinc-200 border border-[#27272A]"
              }`}
            >
              All Students ({students.length})
            </button>
            <button
              onClick={() => setStatusFilter("eligible")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                statusFilter === "eligible"
                  ? "bg-emerald-600 text-white font-bold"
                  : "bg-[#18181B] text-emerald-400 hover:bg-emerald-950/30 border border-[#27272A]"
              }`}
            >
              Eligible Only
            </button>
            <button
              onClick={() => setStatusFilter("excluded")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                statusFilter === "excluded"
                  ? "bg-rose-600 text-white font-bold"
                  : "bg-[#18181B] text-rose-400 hover:bg-rose-950/30 border border-[#27272A]"
              }`}
            >
              Excluded Only
            </button>
          </div>

          {/* Direct Pipeline to Approval */}
          {eligibleCount > 0 && selectedDriveId && (
            <Link
              href={`/approvals?drive_id=${selectedDriveId}`}
              className="px-4 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm shadow-amber-600/30 transition-colors"
            >
              Proceed to Approval Center ({eligibleCount} Students) <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>

        {/* Explainable Decision Table */}
        <div className="bg-[#18181B] border border-[#27272A] rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-[#141417] text-zinc-400 border-b border-[#27272A] font-semibold uppercase tracking-wider">
                  <th className="py-3 px-4">Student</th>
                  <th className="py-3 px-4">Branch</th>
                  <th className="py-3 px-4">CGPA</th>
                  <th className="py-3 px-4">Backlogs</th>
                  <th className="py-3 px-4">Consent</th>
                  <th className="py-3 px-4">Decision</th>
                  <th className="py-3 px-4">Explainable Justification</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#27272A] text-zinc-200">
                {students.length > 0 ? (
                  students.map((stu) => (
                    <tr key={stu.student_id} className="hover:bg-zinc-800/30 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-mono font-medium text-zinc-100">{stu.student_id}</div>
                        <div className="text-zinc-400 text-[11px]">{stu.full_name}</div>
                      </td>
                      <td className="py-3 px-4 font-mono">{stu.branch}</td>
                      <td className="py-3 px-4 font-mono font-semibold">
                        <span
                          className={
                            stu.cgpa >= (activeDrive?.min_cgpa ?? 0)
                              ? "text-emerald-400"
                              : "text-rose-400 font-bold"
                          }
                        >
                          {stu.cgpa.toFixed(2)}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono">
                        {stu.active_backlogs > (activeDrive?.max_backlogs ?? 0) ? (
                          <span className="text-rose-400 font-bold">{stu.active_backlogs}</span>
                        ) : (
                          <span className="text-zinc-300">{stu.active_backlogs}</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {stu.consent_given ? (
                          <span className="text-emerald-400 font-medium">Yes</span>
                        ) : (
                          <span className="text-rose-400 font-medium">No</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <StatusBadge status={stu.is_eligible ? "ELIGIBLE" : "EXCLUDED"} />
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-zinc-300 font-medium">{stu.reason}</div>
                        {stu.failure_reasons?.length > 0 && (
                          <div className="text-[11px] text-rose-400 mt-0.5 space-y-0.5">
                            {stu.failure_reasons.map((fr, idx) => (
                              <div key={idx} className="flex items-center gap-1">
                                <span className="w-1 h-1 rounded-full bg-rose-400" />
                                <span>{fr}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-zinc-500">
                      {loading
                        ? "Evaluating candidate roster..."
                        : "No evaluations found for this drive. Click 'Run Evaluation Rules' above."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function EligibilityAnalysisPage() {
  return (
    <Suspense fallback={<div className="p-8 text-xs text-zinc-500">Loading eligibility analysis...</div>}>
      <EligibilityContent />
    </Suspense>
  );
}
