"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Users,
  Briefcase,
  ShieldCheck,
  CheckCircle2,
  CloudUpload,
  AlertTriangle,
  Bot,
  ArrowRight,
  TrendingUp,
  FileCheck,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { Header } from "@/components/Header";
import { MetricCard } from "@/components/MetricCard";
import { StatusBadge } from "@/components/StatusBadge";
import { fetchApi } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface DashboardData {
  metrics: {
    total_students: number;
    active_drives: number;
    total_drives: number;
    selected_drive_id?: string;
    selected_drive_title?: string;
    eligible_students: number;
    excluded_students: number;
    pending_approvals: number;
    verified_uploads: number;
  };
  recent_drives: Array<{
    id: string;
    employer_name: string;
    drive_title: string;
    min_cgpa: number;
    status: string;
    start_time: string;
  }>;
  recent_uploads: Array<{
    id: string;
    receipt_reference: string;
    verification_status: string;
    expected_count: number;
    actual_destination_count: number;
    reconciliation_details: string;
    verified_at: string;
  }>;
  recent_agent_executions: Array<{
    id: string;
    prompt: string;
    status: string;
    summary: string;
    tools_used: number;
    created_at: string;
  }>;
}

export default function OverviewPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchApi<DashboardData>("/dashboard/summary");
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Operations Dashboard"
        subtitle="Real-time recruitment metrics, eligibility status, and verification outcomes"
      />

      <div className="p-8 space-y-8 max-w-7xl">
        {/* Top notification bar if empty state */}
        {data && data.metrics.total_students === 0 && (
          <div className="bg-indigo-950/40 border border-indigo-800/60 rounded-xl p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-indigo-400 shrink-0" />
              <div>
                <h4 className="text-sm font-semibold text-zinc-100">Quick Start: No Student Records Found</h4>
                <p className="text-xs text-zinc-400">
                  Import a student roster or seed demo records to begin evaluating eligibility and schedule analysis.
                </p>
              </div>
            </div>
            <Link
              href="/students"
              className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
            >
              Go to Student Roster <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        )}

        {/* Action Controls */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
              {data?.metrics.selected_drive_title
                ? `Evaluation Context: ${data.metrics.selected_drive_title}`
                : "System-wide Metric Overview"}
            </h2>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 bg-[#18181B] hover:bg-zinc-800 border border-[#27272A] rounded-lg text-xs font-medium text-zinc-300 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh Metrics
          </button>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          <MetricCard
            title="Total Students"
            value={data?.metrics.total_students ?? 0}
            subtitle="Registered in Roster"
            icon={Users}
            variant="default"
          />
          <MetricCard
            title="Active Drives"
            value={data?.metrics.active_drives ?? 0}
            subtitle={`${data?.metrics.total_drives ?? 0} total scheduled`}
            icon={Briefcase}
            variant="indigo"
          />
          <MetricCard
            title="Eligible Students"
            value={data?.metrics.eligible_students ?? 0}
            subtitle="Selected drive criteria"
            icon={ShieldCheck}
            variant="emerald"
          />
          <MetricCard
            title="Excluded Students"
            value={data?.metrics.excluded_students ?? 0}
            subtitle="Explainable reasons logged"
            icon={AlertTriangle}
            variant="rose"
          />
          <MetricCard
            title="Pending Approvals"
            value={data?.metrics.pending_approvals ?? 0}
            subtitle="Awaiting officer sign-off"
            icon={CheckCircle2}
            variant="amber"
          />
          <MetricCard
            title="Verified Uploads"
            value={data?.metrics.verified_uploads ?? 0}
            subtitle="100% Reconciled receipts"
            icon={CloudUpload}
            variant="emerald"
          />
        </div>

        {/* Main Sections Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Drives */}
          <div className="lg:col-span-2 bg-[#18181B] border border-[#27272A] rounded-xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-[#27272A]">
              <div>
                <h3 className="text-base font-semibold text-zinc-100">Placement Drive Schedules</h3>
                <p className="text-xs text-zinc-400">Configured recruitment drives and eligibility standards</p>
              </div>
              <Link
                href="/drives"
                className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
              >
                View all drives <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="mt-4 divide-y divide-[#27272A]">
              {data?.recent_drives && data.recent_drives.length > 0 ? (
                data.recent_drives.map((d) => (
                  <div key={d.id} className="py-3.5 flex items-center justify-between hover:bg-zinc-800/20 px-2 rounded-lg transition-colors">
                    <div>
                      <h4 className="text-sm font-medium text-zinc-100">{d.employer_name}</h4>
                      <p className="text-xs text-zinc-400">{d.drive_title}</p>
                      <span className="text-[11px] text-zinc-500 font-mono mt-0.5 block">
                        Min CGPA: {d.min_cgpa.toFixed(1)} • Starts: {formatDateTime(d.start_time)}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge status={d.status} />
                      <Link
                        href={`/eligibility?drive_id=${d.id}`}
                        className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded text-xs font-medium"
                      >
                        Evaluate
                      </Link>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-xs text-zinc-500">
                  No placement drives configured. Click "Placement Drives" to create one.
                </div>
              )}
            </div>
          </div>

          {/* Quick Shortcuts */}
          <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-6 flex flex-col justify-between">
            <div>
              <h3 className="text-base font-semibold text-zinc-100">Operations Control</h3>
              <p className="text-xs text-zinc-400">Direct shortcuts to high-impact workflows</p>

              <div className="mt-5 space-y-3">
                <Link
                  href="/agent"
                  className="p-3.5 rounded-lg bg-indigo-950/30 hover:bg-indigo-950/50 border border-indigo-800/40 flex items-center gap-3 transition-colors block"
                >
                  <Bot className="w-5 h-5 text-indigo-400 shrink-0" />
                  <div>
                    <h5 className="text-sm font-semibold text-zinc-100">Launch Agent Workspace</h5>
                    <p className="text-xs text-zinc-400">Natural language goal execution with validated tools</p>
                  </div>
                </Link>

                <Link
                  href="/approvals"
                  className="p-3.5 rounded-lg bg-[#222226] hover:bg-zinc-800 border border-[#27272A] flex items-center gap-3 transition-colors block"
                >
                  <CheckCircle2 className="w-5 h-5 text-amber-400 shrink-0" />
                  <div>
                    <h5 className="text-sm font-semibold text-zinc-100">Review Pending Approvals</h5>
                    <p className="text-xs text-zinc-400">Cryptographically verify and sign off eligible rosters</p>
                  </div>
                </Link>

                <Link
                  href="/students"
                  className="p-3.5 rounded-lg bg-[#222226] hover:bg-zinc-800 border border-[#27272A] flex items-center gap-3 transition-colors block"
                >
                  <Users className="w-5 h-5 text-zinc-400 shrink-0" />
                  <div>
                    <h5 className="text-sm font-semibold text-zinc-100">Import & Validate Roster</h5>
                    <p className="text-xs text-zinc-400">Upload CSV/XLSX with strict schema integrity check</p>
                  </div>
                </Link>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-[#27272A] text-[11px] text-zinc-500">
              Safe execution environment: submissions are blocked without explicit human approval.
            </div>
          </div>
        </div>

        {/* Secondary Grid: Recent Upload Receipts & Agent Runs */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Upload Receipts */}
          <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-[#27272A]">
              <div>
                <h3 className="text-base font-semibold text-zinc-100">Upload Verification Receipts</h3>
                <p className="text-xs text-zinc-400">Employer intake audit logs and reconciliation outcomes</p>
              </div>
              <Link href="/uploads" className="text-xs text-indigo-400 hover:text-indigo-300 font-medium">
                View all receipts
              </Link>
            </div>

            <div className="mt-4 space-y-3">
              {data?.recent_uploads && data.recent_uploads.length > 0 ? (
                data.recent_uploads.map((u) => (
                  <div key={u.id} className="p-3.5 bg-[#222226] border border-[#27272A] rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-semibold text-zinc-200">{u.receipt_reference}</span>
                      <StatusBadge status={u.verification_status} />
                    </div>
                    <p className="text-xs text-zinc-400 mt-2">{u.reconciliation_details}</p>
                    <div className="mt-2 text-[11px] text-zinc-500 font-mono">
                      Expected: {u.expected_count} • Actual: {u.actual_destination_count} • Verified: {formatDateTime(u.verified_at)}
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-xs text-zinc-500">
                  No submissions recorded yet. Approved rosters submitted to employer forms will generate receipts here.
                </div>
              )}
            </div>
          </div>

          {/* Recent Agent Executions */}
          <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-[#27272A]">
              <div>
                <h3 className="text-base font-semibold text-zinc-100">Agent Activity Trace</h3>
                <p className="text-xs text-zinc-400">Autonomous tool calls executed with audit logs</p>
              </div>
              <Link href="/agent" className="text-xs text-indigo-400 hover:text-indigo-300 font-medium">
                Open Workspace
              </Link>
            </div>

            <div className="mt-4 space-y-3">
              {data?.recent_agent_executions && data.recent_agent_executions.length > 0 ? (
                data.recent_agent_executions.map((a) => (
                  <div key={a.id} className="p-3.5 bg-[#222226] border border-[#27272A] rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-zinc-200 italic">"{a.prompt}"</span>
                      <StatusBadge status={a.status} />
                    </div>
                    <p className="text-xs text-zinc-400 mt-2 line-clamp-2">{a.summary}</p>
                    <div className="mt-2 text-[11px] text-zinc-500 flex items-center justify-between font-mono">
                      <span>Tools called: {a.tools_used}</span>
                      <span>{formatDateTime(a.created_at)}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-xs text-zinc-500">
                  No recent agent executions. Ask the agent questions in the Agent Workspace.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
