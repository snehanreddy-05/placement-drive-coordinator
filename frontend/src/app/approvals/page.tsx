"use client";

import React, { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  CheckCircle2,
  XCircle,
  ShieldCheck,
  ShieldAlert,
  Lock,
  ArrowRight,
  RefreshCw,
  Hash,
  AlertTriangle,
  UploadCloud,
  FileCheck,
  UserCheck,
} from "lucide-react";
import { Header } from "@/components/Header";
import { StatusBadge } from "@/components/StatusBadge";
import { fetchApi } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface ApprovalItem {
  id: string;
  drive_id: string;
  drive_title: string;
  employer_name: string;
  roster_hash: string;
  criteria_version: number;
  eligible_count: number;
  destination_url: string;
  approver_name: string;
  approver_email: string;
  status: string;
  rejection_reason?: string;
  created_at: string;
  approved_at?: string;
}

interface ApprovalDetail {
  id: string;
  drive_id: string;
  drive_title: string;
  employer_name: string;
  roster_hash: string;
  criteria_version: number;
  eligible_count: number;
  student_ids: string[];
  destination_url: string;
  approver_name: string;
  approver_email: string;
  status: string;
  is_valid: boolean;
  validity_message: string;
  rejection_reason?: string;
  created_at: string;
  approved_at?: string;
}

function ApprovalsContent() {
  const searchParams = useSearchParams();
  const filterDriveId = searchParams.get("drive_id") || "";

  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [selectedApproval, setSelectedApproval] = useState<ApprovalDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [submittingUpload, setSubmittingUpload] = useState(false);
  const [uploadOutcome, setUploadOutcome] = useState<any | null>(null);

  // New approval preparation modal state
  const [prepareDriveId, setPrepareDriveId] = useState(filterDriveId);
  const [preparing, setPreparing] = useState(false);
  const [drives, setDrives] = useState<any[]>([]);

  // Approver input
  const [officerName, setOfficerName] = useState("Placement Director");
  const [officerEmail, setOfficerEmail] = useState("placement-director@campus.edu");
  const [rejectReason, setRejectReason] = useState("");

  const loadApprovals = async () => {
    try {
      setLoading(true);
      const query = filterDriveId ? `/approvals?drive_id=${filterDriveId}` : "/approvals";
      const data = await fetchApi<ApprovalItem[]>(query);
      setApprovals(data);

      if (data.length > 0) {
        await loadApprovalDetail(data[0].id);
      } else {
        setSelectedApproval(null);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadDrives = async () => {
    try {
      const data = await fetchApi<any[]>("/drives");
      setDrives(data);
      if (!prepareDriveId && data.length > 0) {
        setPrepareDriveId(data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadApprovals();
    loadDrives();
  }, [filterDriveId]);

  const loadApprovalDetail = async (id: string) => {
    try {
      const res = await fetchApi<{ approval: ApprovalDetail }>(`/approvals/${id}`);
      setSelectedApproval(res.approval);
      setUploadOutcome(null);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDecision = async (decision: "APPROVE" | "REJECT") => {
    if (!selectedApproval) return;
    try {
      setActing(true);
      await fetchApi(`/approvals/${selectedApproval.id}/action`, {
        method: "POST",
        body: JSON.stringify({
          decision,
          approver_name: officerName,
          approver_email: officerEmail,
          rejection_reason: decision === "REJECT" ? rejectReason : undefined,
        }),
      });
      await loadApprovals();
      await loadApprovalDetail(selectedApproval.id);
    } catch (err: any) {
      alert(`Decision error: ${err.message}`);
    } finally {
      setActing(false);
    }
  };

  const handleCreateApprovalRequest = async () => {
    if (!prepareDriveId) return;
    try {
      setPreparing(true);
      await fetchApi("/approvals", {
        method: "POST",
        body: JSON.stringify({
          drive_id: prepareDriveId,
          approver_name: officerName,
          approver_email: officerEmail,
        }),
      });
      await loadApprovals();
    } catch (err: any) {
      alert(`Failed to prepare approval: ${err.message}`);
    } finally {
      setPreparing(false);
    }
  };

  const handleSubmitApprovedUpload = async () => {
    if (!selectedApproval) return;
    try {
      setSubmittingUpload(true);
      setUploadOutcome(null);
      const res = await fetchApi<any>("/uploads", {
        method: "POST",
        body: JSON.stringify({
          drive_id: selectedApproval.drive_id,
          approval_id: selectedApproval.id,
        }),
      });
      setUploadOutcome(res);
      await loadApprovals();
      await loadApprovalDetail(selectedApproval.id);
    } catch (err: any) {
      alert(`Upload rejected: ${err.message}`);
    } finally {
      setSubmittingUpload(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Human Approval Center"
        subtitle="Mandatory cryptographic safety gate — require explicit verified sign-off before external roster submission"
      />

      <div className="p-8 space-y-8 max-w-7xl">
        {/* Banner: Non-bypassable Gate */}
        <div className="bg-[#18181B] border border-amber-800/60 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-amber-950 border border-amber-800/80 rounded-lg text-amber-400">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
                Mandatory Human Sign-off Verification
              </h3>
              <p className="text-xs text-zinc-400">
                Approvals are bound to SHA-256 fingerprint, student ID ordering, and criteria version. Any subsequent edit immediately invalidates approval.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <select
              value={prepareDriveId}
              onChange={(e) => setPrepareDriveId(e.target.value)}
              className="bg-[#222226] border border-[#27272A] rounded-lg px-3 py-1.5 text-xs text-zinc-100 focus:outline-none"
            >
              {drives.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.employer_name} ({d.drive_title})
                </option>
              ))}
            </select>
            <button
              onClick={handleCreateApprovalRequest}
              disabled={preparing}
              className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm shadow-amber-600/30 transition-colors"
            >
              <FileCheck className="w-3.5 h-3.5" />
              {preparing ? "Preparing..." : "Prepare Approval Gate"}
            </button>
          </div>
        </div>

        {/* Two-column layout: Approvals List & Active Approval Review Card */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Approval Requests List */}
          <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-5 space-y-4 h-fit">
            <div className="flex items-center justify-between pb-3 border-b border-[#27272A]">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
                Approval Queue ({approvals.length})
              </h4>
              <button onClick={loadApprovals} className="text-zinc-500 hover:text-zinc-300">
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              </button>
            </div>

            <div className="space-y-2.5 max-h-[600px] overflow-y-auto">
              {approvals.length > 0 ? (
                approvals.map((a) => (
                  <div
                    key={a.id}
                    onClick={() => loadApprovalDetail(a.id)}
                    className={`p-3.5 rounded-lg border cursor-pointer transition-all ${
                      selectedApproval?.id === a.id
                        ? "bg-[#27272A] border-indigo-500/80 shadow-sm"
                        : "bg-[#222226] border-[#27272A] hover:bg-zinc-800"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-xs text-zinc-100">{a.employer_name}</span>
                      <StatusBadge status={a.status} />
                    </div>
                    <p className="text-[11px] text-zinc-400 mt-1 line-clamp-1">{a.drive_title}</p>
                    <div className="mt-2 text-[10px] text-zinc-500 flex items-center justify-between font-mono">
                      <span>Eligible: {a.eligible_count} students</span>
                      <span>v{a.criteria_version}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-xs text-zinc-500">
                  No approval requests. Click "Prepare Approval Gate" above or evaluate a drive in Eligibility Analysis.
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Detailed Gate Review */}
          <div className="lg:col-span-2 space-y-5">
            {selectedApproval ? (
              <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-6 space-y-6">
                {/* Header */}
                <div className="flex items-start justify-between pb-4 border-b border-[#27272A]">
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 font-mono">
                      Gate #{selectedApproval.id.slice(0, 8)}
                    </span>
                    <h3 className="text-lg font-bold text-zinc-100 mt-0.5">
                      {selectedApproval.employer_name} — {selectedApproval.drive_title}
                    </h3>
                    <p className="text-xs text-zinc-400 mt-0.5">
                      Target Destination: <span className="font-mono text-zinc-300">{selectedApproval.destination_url}</span>
                    </p>
                  </div>
                  <StatusBadge status={selectedApproval.status} />
                </div>

                {/* Validity Alert */}
                {!selectedApproval.is_valid && (
                  <div className="p-3 bg-rose-950/40 border border-rose-800 rounded-lg flex items-center gap-2.5 text-xs text-rose-300">
                    <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>{selectedApproval.validity_message}</span>
                  </div>
                )}

                {/* Cryptographic SHA-256 Binding */}
                <div className="bg-[#121215] border border-[#27272A] rounded-lg p-3.5 space-y-1.5 font-mono text-xs">
                  <div className="flex items-center gap-2 text-indigo-300 font-semibold">
                    <Hash className="w-3.5 h-3.5" />
                    <span>SHA-256 Cryptographic Fingerprint</span>
                  </div>
                  <p className="text-[11px] text-zinc-300 break-all bg-[#18181B] p-2 rounded border border-zinc-800">
                    {selectedApproval.roster_hash}
                  </p>
                  <span className="text-[10px] text-zinc-500 block">
                    Binds {selectedApproval.eligible_count} sorted student IDs + criteria v{selectedApproval.criteria_version} + destination.
                  </span>
                </div>

                {/* Student IDs Preview */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold uppercase tracking-wider text-zinc-400">
                      Approved Student Roster ({selectedApproval.student_ids.length} Students)
                    </span>
                  </div>
                  <div className="p-3 bg-[#222226] border border-[#27272A] rounded-lg max-h-36 overflow-y-auto flex flex-wrap gap-1.5">
                    {selectedApproval.student_ids.map((id, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 bg-[#18181B] border border-zinc-700/60 rounded text-[11px] font-mono text-zinc-300"
                      >
                        {id}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Approver Identity & Actions */}
                <div className="bg-[#222226] border border-[#27272A] rounded-lg p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-zinc-300 flex items-center gap-1.5">
                      <UserCheck className="w-3.5 h-3.5 text-indigo-400" />
                      Sign-off Identity
                    </span>
                    {selectedApproval.approved_at && (
                      <span className="text-[11px] text-emerald-400 font-mono">
                        Approved on {formatDateTime(selectedApproval.approved_at)}
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <label className="text-zinc-400 block mb-1">Placement Officer Name</label>
                      <input
                        type="text"
                        value={officerName}
                        onChange={(e) => setOfficerName(e.target.value)}
                        disabled={selectedApproval.status === "APPROVED"}
                        className="w-full bg-[#18181B] border border-[#27272A] rounded px-3 py-1.5 text-zinc-200 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-zinc-400 block mb-1">Official University Email</label>
                      <input
                        type="email"
                        value={officerEmail}
                        onChange={(e) => setOfficerEmail(e.target.value)}
                        disabled={selectedApproval.status === "APPROVED"}
                        className="w-full bg-[#18181B] border border-[#27272A] rounded px-3 py-1.5 text-zinc-200 focus:outline-none"
                      />
                    </div>
                  </div>

                  {selectedApproval.status === "PENDING" && (
                    <div className="pt-2 border-t border-[#27272A] flex items-center justify-between gap-3">
                      <div className="flex-1">
                        <input
                          type="text"
                          placeholder="Rejection reason if denying approval..."
                          value={rejectReason}
                          onChange={(e) => setRejectReason(e.target.value)}
                          className="w-full bg-[#18181B] border border-[#27272A] rounded px-3 py-1.5 text-xs text-zinc-200 focus:outline-none"
                        />
                      </div>
                      <button
                        onClick={() => handleDecision("REJECT")}
                        disabled={acting}
                        className="px-3.5 py-1.5 bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 rounded text-xs font-semibold flex items-center gap-1 transition-colors"
                      >
                        <XCircle className="w-3.5 h-3.5" /> Reject
                      </button>
                      <button
                        onClick={() => handleDecision("APPROVE")}
                        disabled={acting}
                        className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold flex items-center gap-1.5 shadow-sm shadow-emerald-600/30 transition-colors"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" /> Sign & Approve Roster
                      </button>
                    </div>
                  )}

                  {/* Immediate Upload Trigger if APPROVED */}
                  {selectedApproval.status === "APPROVED" && (
                    <div className="pt-3 border-t border-[#27272A] flex items-center justify-between bg-emerald-950/20 p-3 rounded-lg border border-emerald-900/40">
                      <div>
                        <span className="text-xs font-semibold text-emerald-300 block">
                          Approval Valid & Verified
                        </span>
                        <p className="text-[11px] text-zinc-400">
                          Ready to transmit roster of {selectedApproval.eligible_count} students to mock employer endpoint.
                        </p>
                      </div>
                      <button
                        onClick={handleSubmitApprovedUpload}
                        disabled={submittingUpload}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm shadow-indigo-600/30 transition-colors"
                      >
                        <UploadCloud className={`w-4 h-4 ${submittingUpload ? "animate-bounce" : ""}`} />
                        {submittingUpload ? "Transmitting..." : "Submit to Destination"}
                      </button>
                    </div>
                  )}
                </div>

                {/* Upload Outcome Notification */}
                {uploadOutcome && (
                  <div className="p-4 bg-[#18181B] border border-zinc-700 rounded-lg space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-zinc-100 flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        Destination Submission Reconciled
                      </span>
                      <StatusBadge status={uploadOutcome.receipt.verification_status} />
                    </div>
                    <p className="text-zinc-300">{uploadOutcome.receipt.reconciliation_details}</p>
                    <div className="flex items-center justify-between text-zinc-500 font-mono text-[11px] pt-1 border-t border-zinc-800">
                      <span>Receipt: {uploadOutcome.receipt.receipt_reference}</span>
                      <Link href="/uploads" className="text-indigo-400 hover:underline">
                        View in Upload History →
                      </Link>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-12 text-center text-zinc-500 text-xs">
                Select an approval from the queue to inspect the cryptographic gate and sign off.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ApprovalCenterPage() {
  return (
    <Suspense fallback={<div className="p-8 text-xs text-zinc-500">Loading Approval Center...</div>}>
      <ApprovalsContent />
    </Suspense>
  );
}
