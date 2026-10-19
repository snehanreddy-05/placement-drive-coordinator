"use client";

import React, { useEffect, useState, useRef } from "react";
import {
  Users,
  Upload,
  Download,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  Sparkles,
  ChevronRight,
  FileSpreadsheet,
  X,
  Info,
} from "lucide-react";
import { Header } from "@/components/Header";
import { StatusBadge } from "@/components/StatusBadge";
import { fetchApi, uploadFileApi, getExportUrl } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface Student {
  student_id: string;
  full_name: string;
  email: string;
  branch: string;
  cgpa: number;
  active_backlogs: number;
  consent_given: boolean;
  is_sample: boolean;
  created_at: string;
  updated_at: string;
}

interface StudentDetailData {
  student: Student;
  eligibility_history: Array<{
    drive_id: string;
    is_eligible: boolean;
    reason: string;
    failure_reasons: string[];
    evaluated_at: string;
  }>;
}

export default function StudentRosterPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [branchFilter, setBranchFilter] = useState("");
  const [consentFilter, setConsentFilter] = useState<string>("all");
  const [selectedStudent, setSelectedStudent] = useState<StudentDetailData | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [importResult, setImportResult] = useState<any | null>(null);
  const [seeding, setSeeding] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const loadStudents = async () => {
    try {
      setLoading(true);
      let query = "/students?";
      if (search) query += `search=${encodeURIComponent(search)}&`;
      if (branchFilter) query += `branch=${encodeURIComponent(branchFilter)}&`;
      if (consentFilter === "true") query += `consent=true&`;
      if (consentFilter === "false") query += `consent=false&`;

      const data = await fetchApi<Student[]>(query);
      setStudents(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStudents();
  }, [branchFilter, consentFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadStudents();
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      setUploading(true);
      setImportResult(null);
      const res = await uploadFileApi<any>("/students/import", formData);
      setImportResult(res);
      await loadStudents();
    } catch (err: any) {
      alert(`Import failed: ${err.message}`);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleSeedDemo = async () => {
    try {
      setSeeding(true);
      await fetchApi("/students/seed-demo", { method: "POST" });
      await loadStudents();
    } catch (err: any) {
      alert(`Seeding failed: ${err.message}`);
    } finally {
      setSeeding(false);
    }
  };

  const handleSelectStudent = async (stuId: string) => {
    try {
      setDetailLoading(true);
      const data = await fetchApi<StudentDetailData>(`/students/${stuId}`);
      setSelectedStudent(data);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Student Roster Management"
        subtitle="Manage student profiles, consent verification, and academic criteria integrity"
      />

      <div className="p-8 space-y-6 max-w-7xl">
        {/* Action Header Banner */}
        <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-950/60 border border-indigo-800/60 rounded-lg text-indigo-400">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-zinc-100">Roster Repository ({students.length})</h3>
              <p className="text-xs text-zinc-400">
                Validate CGPA ranges (0-10), backlogs, and explicit recruitment consent
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <a
              href={getExportUrl("/students/template/download")}
              download="placement_roster_template.csv"
              className="px-3 py-1.5 bg-[#222226] hover:bg-zinc-800 border border-[#27272A] text-zinc-200 rounded-lg text-xs font-medium flex items-center gap-2 transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-zinc-400" />
              Download CSV Template
            </a>

            <button
              onClick={handleSeedDemo}
              disabled={seeding}
              className="px-3 py-1.5 bg-[#222226] hover:bg-zinc-800 border border-[#27272A] text-indigo-300 rounded-lg text-xs font-medium flex items-center gap-2 transition-colors"
            >
              <Sparkles className={`w-3.5 h-3.5 ${seeding ? "animate-spin" : ""}`} />
              {seeding ? "Seeding..." : "Seed 15 Demo Students"}
            </button>

            <label className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 cursor-pointer transition-colors shadow-sm shadow-indigo-600/30">
              <Upload className="w-3.5 h-3.5" />
              {uploading ? "Parsing File..." : "Import CSV / Excel"}
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv, .xlsx, .xls"
                className="hidden"
                onChange={handleFileUpload}
                disabled={uploading}
              />
            </label>
          </div>
        </div>

        {/* Import Results Notification */}
        {importResult && (
          <div className="bg-[#18181B] border border-zinc-700 rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <h4 className="text-sm font-semibold text-zinc-100">
                  Import Summary for {importResult.summary.filename}
                </h4>
              </div>
              <button
                onClick={() => setImportResult(null)}
                className="text-zinc-400 hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="grid grid-cols-4 gap-2 text-xs">
              <div className="bg-[#222226] p-2.5 rounded border border-[#27272A]">
                <span className="text-zinc-400 block">Total Rows:</span>
                <span className="text-zinc-100 font-bold">{importResult.summary.total_rows}</span>
              </div>
              <div className="bg-[#222226] p-2.5 rounded border border-[#27272A]">
                <span className="text-emerald-400 block">New Imported:</span>
                <span className="text-zinc-100 font-bold">{importResult.imported_new}</span>
              </div>
              <div className="bg-[#222226] p-2.5 rounded border border-[#27272A]">
                <span className="text-indigo-400 block">Updated Existing:</span>
                <span className="text-zinc-100 font-bold">{importResult.updated_existing}</span>
              </div>
              <div className="bg-[#222226] p-2.5 rounded border border-[#27272A]">
                <span className="text-rose-400 block">Rejected / Invalid:</span>
                <span className="text-zinc-100 font-bold">{importResult.summary.invalid_rows_count}</span>
              </div>
            </div>

            {importResult.invalid_rows?.length > 0 && (
              <div className="mt-3 p-3 bg-rose-950/30 border border-rose-900/60 rounded-lg space-y-1 text-xs">
                <span className="font-semibold text-rose-300 block">Row-level Validation Failures:</span>
                {importResult.invalid_rows.slice(0, 5).map((ir: any, idx: number) => (
                  <div key={idx} className="text-rose-200">
                    Row {ir.row_number}: {ir.errors.join("; ")}
                  </div>
                ))}
                {importResult.invalid_rows.length > 5 && (
                  <div className="text-rose-400 italic">
                    ...and {importResult.invalid_rows.length - 5} more invalid rows omitted.
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Search & Filter Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[280px] relative">
            <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by student ID, full name, or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-[#18181B] border border-[#27272A] rounded-lg pl-9 pr-4 py-2 text-xs text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-indigo-500"
            />
          </form>

          <div className="flex items-center gap-3">
            <select
              value={branchFilter}
              onChange={(e) => setBranchFilter(e.target.value)}
              className="bg-[#18181B] border border-[#27272A] rounded-lg px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Branches</option>
              <option value="CSE">CSE</option>
              <option value="IT">IT</option>
              <option value="ECE">ECE</option>
              <option value="MECH">MECH</option>
            </select>

            <select
              value={consentFilter}
              onChange={(e) => setConsentFilter(e.target.value)}
              className="bg-[#18181B] border border-[#27272A] rounded-lg px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Consent</option>
              <option value="true">Consented Only</option>
              <option value="false">Missing Consent</option>
            </select>

            <button
              onClick={loadStudents}
              className="p-2 bg-[#18181B] hover:bg-zinc-800 border border-[#27272A] rounded-lg text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Student Table */}
        <div className="bg-[#18181B] border border-[#27272A] rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-[#141417] text-zinc-400 border-b border-[#27272A] font-semibold uppercase tracking-wider">
                  <th className="py-3 px-4">Student ID</th>
                  <th className="py-3 px-4">Full Name</th>
                  <th className="py-3 px-4">Branch</th>
                  <th className="py-3 px-4">CGPA</th>
                  <th className="py-3 px-4">Backlogs</th>
                  <th className="py-3 px-4">Placement Consent</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#27272A] text-zinc-200">
                {students.length > 0 ? (
                  students.map((stu) => (
                    <tr
                      key={stu.student_id}
                      className="hover:bg-zinc-800/30 transition-colors cursor-pointer"
                      onClick={() => handleSelectStudent(stu.student_id)}
                    >
                      <td className="py-3 px-4 font-mono font-medium text-zinc-100">
                        {stu.student_id}
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-medium text-zinc-200">{stu.full_name}</div>
                        <div className="text-[11px] text-zinc-500">{stu.email}</div>
                      </td>
                      <td className="py-3 px-4 font-mono">{stu.branch}</td>
                      <td className="py-3 px-4 font-mono font-semibold">
                        <span
                          className={
                            stu.cgpa >= 8.0
                              ? "text-emerald-400"
                              : stu.cgpa >= 6.5
                              ? "text-zinc-200"
                              : "text-amber-400"
                          }
                        >
                          {stu.cgpa.toFixed(2)}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono">
                        {stu.active_backlogs === 0 ? (
                          <span className="text-zinc-400">0</span>
                        ) : (
                          <span className="text-rose-400 font-semibold">{stu.active_backlogs}</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {stu.consent_given ? (
                          <span className="inline-flex items-center gap-1 text-emerald-400 font-medium">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Consented
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-rose-400 font-medium">
                            <XCircle className="w-3.5 h-3.5" /> No Consent
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {stu.is_sample ? (
                          <span className="px-2 py-0.5 bg-zinc-800 text-zinc-400 rounded text-[10px] uppercase font-mono">
                            Demo
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 bg-indigo-950 text-indigo-300 rounded text-[10px] uppercase font-mono">
                            Real
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectStudent(stu.student_id);
                          }}
                          className="px-2.5 py-1 bg-[#222226] hover:bg-zinc-700 text-zinc-300 rounded text-xs font-medium"
                        >
                          History
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-zinc-500">
                      {loading ? "Loading roster records..." : "No student records match the selected filters."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Student Audit Detail Slide-over Modal */}
        {selectedStudent && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
            <div className="bg-[#18181B] border border-[#27272A] rounded-xl max-w-xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between pb-3 border-b border-[#27272A]">
                <div>
                  <h3 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
                    <span>{selectedStudent.student.full_name}</span>
                    <span className="text-xs font-mono text-zinc-400">
                      ({selectedStudent.student.student_id})
                    </span>
                  </h3>
                  <p className="text-xs text-zinc-400">{selectedStudent.student.email}</p>
                </div>
                <button
                  onClick={() => setSelectedStudent(null)}
                  className="p-1 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Attributes Grid */}
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="bg-[#222226] p-3 rounded-lg border border-[#27272A]">
                  <span className="text-zinc-500 block">Department</span>
                  <span className="font-semibold text-zinc-200 font-mono">
                    {selectedStudent.student.branch}
                  </span>
                </div>
                <div className="bg-[#222226] p-3 rounded-lg border border-[#27272A]">
                  <span className="text-zinc-500 block">CGPA</span>
                  <span className="font-semibold text-emerald-400 font-mono">
                    {selectedStudent.student.cgpa.toFixed(2)}
                  </span>
                </div>
                <div className="bg-[#222226] p-3 rounded-lg border border-[#27272A]">
                  <span className="text-zinc-500 block">Active Backlogs</span>
                  <span className="font-semibold text-zinc-200 font-mono">
                    {selectedStudent.student.active_backlogs}
                  </span>
                </div>
              </div>

              {/* Eligibility History */}
              <div className="space-y-2 pt-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  Drive Eligibility Evaluations
                </h4>
                {selectedStudent.eligibility_history?.length > 0 ? (
                  <div className="space-y-2">
                    {selectedStudent.eligibility_history.map((eh, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-[#222226] border border-[#27272A] rounded-lg space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono text-zinc-300">Drive ID: {eh.drive_id}</span>
                          <StatusBadge status={eh.is_eligible ? "ELIGIBLE" : "EXCLUDED"} />
                        </div>
                        <p className="text-xs text-zinc-400">{eh.reason}</p>
                        {eh.failure_reasons?.length > 0 && (
                          <ul className="list-disc pl-4 text-[11px] text-rose-300 space-y-0.5">
                            {eh.failure_reasons.map((fr, rIdx) => (
                              <li key={rIdx}>{fr}</li>
                            ))}
                          </ul>
                        )}
                        <span className="text-[10px] text-zinc-500 block">
                          Evaluated: {formatDateTime(eh.evaluated_at)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-zinc-500 py-3 bg-[#222226] rounded text-center">
                    No evaluations recorded for this student yet.
                  </p>
                )}
              </div>

              <div className="pt-3 border-t border-[#27272A] flex justify-end">
                <button
                  onClick={() => setSelectedStudent(null)}
                  className="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg text-xs font-medium"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
