"use client";

import React, { useEffect, useState } from "react";
import {
  ClipboardList,
  Download,
  FileSpreadsheet,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Search,
  UserCheck,
  AlertCircle,
} from "lucide-react";
import { Header } from "@/components/Header";
import { StatusBadge } from "@/components/StatusBadge";
import { fetchApi, getExportUrl } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface DriveSummary {
  id: string;
  employer_name: string;
  drive_title: string;
}

interface AttendanceRecord {
  id: string;
  student_id: string;
  student_name: string;
  branch: string;
  status: string;
  check_in_time?: string;
  notes?: string;
  roster_hash: string;
  generated_at: string;
}

export default function AttendancePage() {
  const [drives, setDrives] = useState<DriveSummary[]>([]);
  const [selectedDriveId, setSelectedDriveId] = useState<string>("");
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    fetchApi<DriveSummary[]>("/drives").then((data) => {
      setDrives(data);
      if (data.length > 0) setSelectedDriveId(data[0].id);
    });
  }, []);

  const loadAttendance = async (driveId: string) => {
    if (!driveId) return;
    try {
      setLoading(true);
      const res = await fetchApi<{
        records: AttendanceRecord[];
        total_records: number;
        present_count: number;
        absent_count: number;
        not_marked_count: number;
      }>(`/drives/${driveId}/attendance`);
      setRecords(res.records || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDriveId) loadAttendance(selectedDriveId);
  }, [selectedDriveId]);

  const handleGenerateAttendance = async () => {
    if (!selectedDriveId) return;
    try {
      setGenerating(true);
      await fetchApi(`/drives/${selectedDriveId}/attendance/generate`, { method: "POST" });
      await loadAttendance(selectedDriveId);
    } catch (err: any) {
      alert(`Failed to generate attendance: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleStatusChange = async (recordId: string, newStatus: string) => {
    try {
      await fetchApi(`/attendance/${recordId}`, {
        method: "PATCH",
        body: JSON.stringify({ attendance_status: newStatus }),
      });
      await loadAttendance(selectedDriveId);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const presentCount = records.filter((r) => r.status === "Present").length;
  const absentCount = records.filter((r) => r.status === "Absent").length;
  const notMarkedCount = records.filter((r) => r.status === "Not Marked").length;

  const filteredRecords = records.filter((r) => {
    if (statusFilter !== "all" && r.status !== statusFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return r.student_id.toLowerCase().includes(q) || r.student_name.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Recruitment Attendance Management"
        subtitle="Generate official attendance sheets from approved rosters and track live check-ins"
      />

      <div className="p-8 space-y-8 max-w-7xl">
        {/* Top Control Bar */}
        <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-950/60 border border-indigo-800/60 rounded-lg text-indigo-400">
              <ClipboardList className="w-5 h-5" />
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
                    {d.employer_name} — {d.drive_title}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            {selectedDriveId && (
              <>
                <a
                  href={getExportUrl(`/drives/${selectedDriveId}/attendance/export?format=csv`)}
                  className="px-3 py-1.5 bg-[#222226] hover:bg-zinc-800 border border-[#27272A] text-zinc-300 rounded-lg text-xs font-medium flex items-center gap-2 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  Export Sheet (CSV)
                </a>

                <a
                  href={getExportUrl(`/drives/${selectedDriveId}/attendance/export?format=xlsx`)}
                  className="px-3 py-1.5 bg-[#222226] hover:bg-zinc-800 border border-[#27272A] text-zinc-300 rounded-lg text-xs font-medium flex items-center gap-2 transition-colors"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  Export Sheet (XLSX)
                </a>

                <button
                  onClick={handleGenerateAttendance}
                  disabled={generating}
                  className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm shadow-indigo-600/30 transition-colors"
                >
                  <UserCheck className={`w-3.5 h-3.5 ${generating ? "animate-spin" : ""}`} />
                  {generating ? "Generating..." : "Generate from Approved Roster"}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Attendance Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-4">
            <span className="text-xs text-zinc-400 uppercase font-semibold">Total Approved</span>
            <div className="text-2xl font-bold text-zinc-100 mt-1">{records.length}</div>
          </div>
          <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-4">
            <span className="text-xs text-emerald-400 uppercase font-semibold">Present (Checked In)</span>
            <div className="text-2xl font-bold text-emerald-300 mt-1">{presentCount}</div>
          </div>
          <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-4">
            <span className="text-xs text-amber-400 uppercase font-semibold">Not Marked</span>
            <div className="text-2xl font-bold text-amber-300 mt-1">{notMarkedCount}</div>
          </div>
          <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-4">
            <span className="text-xs text-rose-400 uppercase font-semibold">Absent</span>
            <div className="text-2xl font-bold text-rose-300 mt-1">{absentCount}</div>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setStatusFilter("all")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium ${
                statusFilter === "all" ? "bg-zinc-200 text-zinc-900 font-bold" : "bg-[#18181B] text-zinc-400"
              }`}
            >
              All ({records.length})
            </button>
            <button
              onClick={() => setStatusFilter("Present")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium ${
                statusFilter === "Present" ? "bg-emerald-600 text-white font-bold" : "bg-[#18181B] text-emerald-400"
              }`}
            >
              Present ({presentCount})
            </button>
            <button
              onClick={() => setStatusFilter("Not Marked")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium ${
                statusFilter === "Not Marked" ? "bg-amber-600 text-white font-bold" : "bg-[#18181B] text-amber-400"
              }`}
            >
              Not Marked ({notMarkedCount})
            </button>
          </div>

          <div className="relative min-w-[240px]">
            <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter by ID or name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-[#18181B] border border-[#27272A] rounded-lg pl-8 pr-3 py-1.5 text-xs text-zinc-200 focus:outline-none w-full"
            />
          </div>
        </div>

        {/* Attendance Sheet Table */}
        <div className="bg-[#18181B] border border-[#27272A] rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-[#141417] text-zinc-400 border-b border-[#27272A] font-semibold uppercase tracking-wider">
                  <th className="py-3 px-4">Student ID</th>
                  <th className="py-3 px-4">Candidate Name</th>
                  <th className="py-3 px-4">Branch</th>
                  <th className="py-3 px-4">Attendance Status</th>
                  <th className="py-3 px-4">Check-in Timestamp</th>
                  <th className="py-3 px-4 text-right">Quick Mark Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#27272A] text-zinc-200">
                {filteredRecords.length > 0 ? (
                  filteredRecords.map((r) => (
                    <tr key={r.id} className="hover:bg-zinc-800/30 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-zinc-100">{r.student_id}</td>
                      <td className="py-3 px-4 font-medium text-zinc-200">{r.student_name}</td>
                      <td className="py-3 px-4 font-mono">{r.branch}</td>
                      <td className="py-3 px-4">
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-zinc-400">
                        {r.check_in_time ? formatDateTime(r.check_in_time) : "—"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleStatusChange(r.id, "Present")}
                            className="px-2 py-1 bg-emerald-950/60 hover:bg-emerald-900 border border-emerald-800 text-emerald-300 rounded text-[11px] font-medium transition-colors"
                          >
                            Mark Present
                          </button>
                          <button
                            onClick={() => handleStatusChange(r.id, "Absent")}
                            className="px-2 py-1 bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 rounded text-[11px] font-medium transition-colors"
                          >
                            Mark Absent
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-zinc-500">
                      {loading
                        ? "Loading attendance sheet..."
                        : "No attendance records generated yet for this drive. Click 'Generate from Approved Roster' above."}
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
