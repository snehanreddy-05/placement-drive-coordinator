"use client";

import React, { useEffect, useState } from "react";
import {
  CloudUpload,
  CheckCircle2,
  AlertTriangle,
  Download,
  RefreshCw,
  FileCheck,
  Hash,
  ExternalLink,
  ShieldCheck,
  XCircle,
  Copy,
} from "lucide-react";
import { Header } from "@/components/Header";
import { StatusBadge } from "@/components/StatusBadge";
import { fetchApi, getExportUrl } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface UploadJobItem {
  id: string;
  drive_id: string;
  employer_name: string;
  drive_title: string;
  destination_url: string;
  status: string;
  expected_count: number;
  submitted_count: number;
  idempotency_key: string;
  created_at: string;
  receipt?: {
    receipt_reference: string;
    verification_status: string;
    reconciliation_details: string;
    actual_count: number;
  };
}

export default function UploadHistoryPage() {
  const [uploads, setUploads] = useState<UploadJobItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadUploads = async () => {
    try {
      setLoading(true);
      const data = await fetchApi<UploadJobItem[]>("/uploads");
      setUploads(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUploads();
  }, []);

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Upload Verification & Intake Receipts"
        subtitle="Automated read-back reconciliation — re-inspects destination records to verify exact ID matching"
      />

      <div className="p-8 space-y-8 max-w-7xl">
        {/* Banner */}
        <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-950/60 border border-emerald-800/60 rounded-lg text-emerald-400">
              <CloudUpload className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-zinc-100">
                Intake Submissions & Reconciled Records ({uploads.length})
              </h3>
              <p className="text-xs text-zinc-400">
                A submission is marked VERIFIED only when destination records re-read and reconcile 100% with the approved roster.
              </p>
            </div>
          </div>

          <button
            onClick={loadUploads}
            className="p-2 bg-[#222226] hover:bg-zinc-800 border border-[#27272A] rounded-lg text-zinc-300 text-xs font-medium flex items-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {/* Uploads List */}
        <div className="space-y-4">
          {uploads.length > 0 ? (
            uploads.map((u) => {
              const receipt = u.receipt;
              const isVerified = receipt?.verification_status === "VERIFIED";

              return (
                <div
                  key={u.id}
                  className="bg-[#18181B] border border-[#27272A] rounded-xl p-6 hover:border-zinc-700 transition-colors space-y-4"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-zinc-400">
                          {receipt?.receipt_reference || "NO-RECEIPT"}
                        </span>
                        <StatusBadge status={receipt?.verification_status || u.status} />
                      </div>
                      <h4 className="text-base font-bold text-zinc-100 mt-1">
                        {u.employer_name} — {u.drive_title}
                      </h4>
                      <p className="text-xs text-zinc-400 font-mono mt-0.5">
                        Target: {u.destination_url}
                      </p>
                    </div>

                    {receipt && (
                      <a
                        href={getExportUrl(`/uploads/${u.id}/receipt/download`)}
                        download={`receipt_${receipt.receipt_reference}.json`}
                        className="px-3 py-1.5 bg-[#222226] hover:bg-zinc-800 border border-[#27272A] text-zinc-200 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors"
                      >
                        <Download className="w-3.5 h-3.5 text-zinc-400" />
                        Download Receipt (JSON)
                      </a>
                    )}
                  </div>

                  {/* Reconciliation Breakdown */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                    <div className="bg-[#222226] p-3 rounded-lg border border-[#27272A]">
                      <span className="text-zinc-500 block">Expected Approved Count</span>
                      <span className="font-mono font-bold text-zinc-200">{u.expected_count} Students</span>
                    </div>
                    <div className="bg-[#222226] p-3 rounded-lg border border-[#27272A]">
                      <span className="text-zinc-500 block">Actual Read-back Count</span>
                      <span className="font-mono font-bold text-zinc-200">
                        {receipt ? `${receipt.actual_count} Records` : "Pending"}
                      </span>
                    </div>
                    <div className="bg-[#222226] p-3 rounded-lg border border-[#27272A]">
                      <span className="text-zinc-500 block">Reconciliation Status</span>
                      <span
                        className={`font-mono font-bold ${
                          isVerified ? "text-emerald-400" : "text-amber-400"
                        }`}
                      >
                        {receipt?.verification_status || u.status}
                      </span>
                    </div>
                    <div className="bg-[#222226] p-3 rounded-lg border border-[#27272A]">
                      <span className="text-zinc-500 block">Submission Timestamp</span>
                      <span className="font-mono text-zinc-300 text-[11px] block">
                        {formatDateTime(u.created_at)}
                      </span>
                    </div>
                  </div>

                  {/* Reconciliation Detail Message */}
                  <div
                    className={`p-3 rounded-lg border text-xs ${
                      isVerified
                        ? "bg-emerald-950/20 border-emerald-900/40 text-emerald-300"
                        : "bg-rose-950/30 border-rose-900/40 text-rose-300"
                    }`}
                  >
                    <span className="font-semibold mr-1">Reconciliation Audit:</span>
                    {receipt?.reconciliation_details || "Awaiting verification process."}
                  </div>

                  {/* Idempotency Footer */}
                  <div className="pt-2 border-t border-[#27272A] flex items-center justify-between text-[11px] text-zinc-500 font-mono">
                    <span>Idempotency Key: {u.idempotency_key}</span>
                    <span>Job ID: {u.id.slice(0, 12)}...</span>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-16 text-center text-xs text-zinc-500">
              {loading
                ? "Loading upload logs..."
                : "No uploads executed yet. Submissions approved in the Approval Center will appear here with read-back verification."}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
