"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Briefcase,
  Plus,
  Clock,
  Calendar,
  MapPin,
  Globe,
  AlertTriangle,
  CheckCircle2,
  X,
  RefreshCw,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";
import { Header } from "@/components/Header";
import { StatusBadge } from "@/components/StatusBadge";
import { fetchApi } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface PlacementDrive {
  id: string;
  employer_name: string;
  drive_title: string;
  min_cgpa: number;
  eligible_branches: string;
  max_backlogs: number;
  consent_required: boolean;
  registration_deadline: string;
  start_time: string;
  end_time: string;
  timezone: string;
  venue: string;
  employer_form_url: string;
  status: string;
  criteria_version: number;
  created_at: string;
}

interface ClashItem {
  id: string;
  drive1_title: string;
  drive2_title: string;
  clash_type: string;
  start_time_overlap: string;
  end_time_overlap: string;
  affected_students_count: number;
  affected_students: string[];
}

export default function DrivesPage() {
  const [drives, setDrives] = useState<PlacementDrive[]>([]);
  const [clashes, setClashes] = useState<ClashItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    employer_name: "",
    drive_title: "",
    min_cgpa: 7.0,
    eligible_branches: "CSE,IT,ECE",
    max_backlogs: 0,
    consent_required: true,
    registration_deadline: "2026-10-25T18:00",
    start_time: "2026-10-30T09:00",
    end_time: "2026-10-30T17:00",
    timezone: "Asia/Kolkata",
    venue: "Main Campus Auditorium",
    employer_form_url: "mock://employer.recruitment/v1/intake",
    status: "Active",
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [drivesData, clashesData] = await Promise.all([
        fetchApi<PlacementDrive[]>("/drives"),
        fetchApi<{ clashes: ClashItem[] }>("/drives/clashes/all"),
      ]);
      setDrives(drivesData);
      setClashes(clashesData.clashes || []);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    try {
      setSubmitting(true);
      await fetchApi("/drives", {
        method: "POST",
        body: JSON.stringify(formData),
      });
      setShowCreateModal(false);
      await loadData();
    } catch (err: any) {
      setFormError(err.message || "Failed to create drive");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Placement Drives & Schedule Management"
        subtitle="Configure recruitment criteria, validate time windows, and detect schedule conflicts"
      />

      <div className="p-8 space-y-8 max-w-7xl">
        {/* Top Control Bar */}
        <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-950/60 border border-indigo-800/60 rounded-lg text-indigo-400">
              <Briefcase className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-zinc-100">
                Scheduled Drives ({drives.length})
              </h3>
              <p className="text-xs text-zinc-400">
                Active criteria versioning protects approvals from silent policy drift
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              className="p-2 bg-[#222226] hover:bg-zinc-800 border border-[#27272A] text-zinc-300 rounded-lg text-xs font-medium"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm shadow-indigo-600/30 transition-colors"
            >
              <Plus className="w-4 h-4" /> Create Placement Drive
            </button>
          </div>
        </div>

        {/* Schedule Clash Warning Alert */}
        {clashes.length > 0 && (
          <div className="bg-amber-950/30 border border-amber-800/60 rounded-xl p-5 space-y-3">
            <div className="flex items-center gap-2.5 text-amber-300">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <h4 className="text-sm font-semibold">
                Schedule Conflict Detected ({clashes.length} Overlapping Window{clashes.length > 1 ? "s" : ""})
              </h4>
            </div>
            <p className="text-xs text-amber-200/80">
              The deterministic clash detection engine detected overlapping time intervals across active drives.
            </p>
            <div className="space-y-2 mt-2">
              {clashes.map((c, idx) => (
                <div
                  key={idx}
                  className="bg-[#18181B]/80 border border-amber-900/40 rounded-lg p-3 text-xs flex flex-wrap items-center justify-between gap-2"
                >
                  <div>
                    <span className="font-semibold text-zinc-200">
                      {c.drive1_title} <span className="text-amber-400">vs</span> {c.drive2_title}
                    </span>
                    <span className="text-zinc-400 block font-mono text-[11px] mt-0.5">
                      Overlap Window: {formatDateTime(c.start_time_overlap)} — {formatDateTime(c.end_time_overlap)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {c.affected_students_count > 0 && (
                      <span className="px-2.5 py-0.5 bg-amber-950 text-amber-300 border border-amber-800 rounded text-xs font-medium">
                        {c.affected_students_count} Conflicted Students
                      </span>
                    )}
                    <StatusBadge status="SCHEDULE_OVERLAP" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Drives Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {drives.map((d) => (
            <div
              key={d.id}
              className="bg-[#18181B] border border-[#27272A] rounded-xl p-6 hover:border-zinc-700 transition-colors flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 font-mono">
                      v{d.criteria_version} Criteria Policy
                    </span>
                    <h3 className="text-lg font-bold text-zinc-100">{d.employer_name}</h3>
                    <p className="text-xs text-zinc-400">{d.drive_title}</p>
                  </div>
                  <StatusBadge status={d.status} />
                </div>

                {/* Criteria Pills */}
                <div className="flex flex-wrap gap-2 text-xs">
                  <div className="bg-[#222226] px-2.5 py-1 rounded border border-[#27272A] text-zinc-300">
                    Min CGPA: <span className="font-bold text-zinc-100 font-mono">{d.min_cgpa.toFixed(1)}</span>
                  </div>
                  <div className="bg-[#222226] px-2.5 py-1 rounded border border-[#27272A] text-zinc-300">
                    Branches: <span className="font-bold text-zinc-100 font-mono">{d.eligible_branches}</span>
                  </div>
                  <div className="bg-[#222226] px-2.5 py-1 rounded border border-[#27272A] text-zinc-300">
                    Max Backlogs: <span className="font-bold text-zinc-100 font-mono">{d.max_backlogs}</span>
                  </div>
                  <div className="bg-[#222226] px-2.5 py-1 rounded border border-[#27272A] text-zinc-300">
                    Consent: <span className="font-bold text-zinc-100">{d.consent_required ? "Mandatory" : "Optional"}</span>
                  </div>
                </div>

                {/* Logistics */}
                <div className="space-y-1.5 text-xs text-zinc-400 pt-2 border-t border-[#27272A]">
                  <div className="flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                    <span>
                      {formatDateTime(d.start_time)} to {formatDateTime(d.end_time)} ({d.timezone})
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <MapPin className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                    <span>{d.venue}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Globe className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                    <span className="font-mono text-[11px] truncate max-w-sm">{d.employer_form_url}</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-3 border-t border-[#27272A] flex items-center justify-between">
                <span className="text-[11px] text-zinc-500 font-mono">ID: {d.id.slice(0, 8)}...</span>
                <div className="flex items-center gap-2">
                  <Link
                    href={`/eligibility?drive_id=${d.id}`}
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    Evaluate Eligibility <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Create Drive Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
            <div className="bg-[#18181B] border border-[#27272A] rounded-xl max-w-xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between pb-3 border-b border-[#27272A]">
                <h3 className="text-base font-semibold text-zinc-100">Create Placement Recruitment Drive</h3>
                <button onClick={() => setShowCreateModal(false)} className="text-zinc-400 hover:text-zinc-100">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {formError && (
                <div className="p-3 bg-rose-950/40 border border-rose-800 rounded text-xs text-rose-300">
                  {formError}
                </div>
              )}

              <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-zinc-400 block mb-1">Employer Name *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Amazon Web Services"
                      value={formData.employer_name}
                      onChange={(e) => setFormData({ ...formData, employer_name: e.target.value })}
                      className="w-full bg-[#222226] border border-[#27272A] rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-zinc-400 block mb-1">Drive Title *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Graduate Software Engineer"
                      value={formData.drive_title}
                      onChange={(e) => setFormData({ ...formData, drive_title: e.target.value })}
                      className="w-full bg-[#222226] border border-[#27272A] rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-zinc-400 block mb-1">Minimum CGPA (0 - 10) *</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="10"
                      required
                      value={formData.min_cgpa}
                      onChange={(e) => setFormData({ ...formData, min_cgpa: parseFloat(e.target.value) })}
                      className="w-full bg-[#222226] border border-[#27272A] rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500 font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-zinc-400 block mb-1">Eligible Branches *</label>
                    <input
                      type="text"
                      required
                      placeholder="CSE,IT,ECE"
                      value={formData.eligible_branches}
                      onChange={(e) => setFormData({ ...formData, eligible_branches: e.target.value })}
                      className="w-full bg-[#222226] border border-[#27272A] rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500 uppercase font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-zinc-400 block mb-1">Max Permitted Backlogs *</label>
                    <input
                      type="number"
                      min="0"
                      required
                      value={formData.max_backlogs}
                      onChange={(e) => setFormData({ ...formData, max_backlogs: parseInt(e.target.value) })}
                      className="w-full bg-[#222226] border border-[#27272A] rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500 font-mono"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-zinc-400 block mb-1">Drive Start Time *</label>
                    <input
                      type="datetime-local"
                      required
                      value={formData.start_time}
                      onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                      className="w-full bg-[#222226] border border-[#27272A] rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-zinc-400 block mb-1">Drive End Time *</label>
                    <input
                      type="datetime-local"
                      required
                      value={formData.end_time}
                      onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                      className="w-full bg-[#222226] border border-[#27272A] rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-zinc-400 block mb-1">Venue / Online Link</label>
                    <input
                      type="text"
                      value={formData.venue}
                      onChange={(e) => setFormData({ ...formData, venue: e.target.value })}
                      className="w-full bg-[#222226] border border-[#27272A] rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-zinc-400 block mb-1">Employer Intake URL</label>
                    <input
                      type="text"
                      value={formData.employer_form_url}
                      onChange={(e) => setFormData({ ...formData, employer_form_url: e.target.value })}
                      className="w-full bg-[#222226] border border-[#27272A] rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500 font-mono text-[11px]"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <input
                    type="checkbox"
                    id="consent_check"
                    checked={formData.consent_required}
                    onChange={(e) => setFormData({ ...formData, consent_required: e.target.checked })}
                    className="rounded bg-[#222226] border-[#27272A] text-indigo-600 focus:ring-0"
                  />
                  <label htmlFor="consent_check" className="text-zinc-300">
                    Require explicit placement consent from each student
                  </label>
                </div>

                <div className="pt-4 border-t border-[#27272A] flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-xs font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm shadow-indigo-600/30"
                  >
                    {submitting ? "Saving..." : "Save Placement Drive"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
