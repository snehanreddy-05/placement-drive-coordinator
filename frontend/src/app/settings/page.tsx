"use client";

import React, { useEffect, useState } from "react";
import {
  Settings,
  ShieldCheck,
  Save,
  Key,
  Globe,
  Clock,
  Cpu,
  History,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import { Header } from "@/components/Header";
import { StatusBadge } from "@/components/StatusBadge";
import { fetchApi } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface AppSettings {
  project_name: string;
  version: string;
  environment: string;
  default_timezone: string;
  llm_provider: string;
  llm_model: string;
  llm_api_key_configured: boolean;
  llm_api_key_masked?: string;
  mock_destination_default: string;
  rules_engine_version: string;
}

interface AuditLogEvent {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  actor: string;
  action_details: string;
  created_at: string;
}

export default function SettingsPage() {
  const [config, setConfig] = useState<AppSettings | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form
  const [provider, setProvider] = useState("deterministic");
  const [model, setModel] = useState("gemini-1.5-flash");
  const [apiKey, setApiKey] = useState("");
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [savedSuccess, setSavedSuccess] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [settingsData, auditData] = await Promise.all([
        fetchApi<AppSettings>("/settings"),
        fetchApi<AuditLogEvent[]>("/audit?limit=25"),
      ]);
      setConfig(settingsData);
      setProvider(settingsData.llm_provider);
      setModel(settingsData.llm_model);
      setTimezone(settingsData.default_timezone);
      setAuditLogs(auditData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      setSavedSuccess(false);
      await fetchApi("/settings", {
        method: "POST",
        body: JSON.stringify({
          llm_provider: provider,
          llm_model: model,
          llm_api_key: apiKey ? apiKey : undefined,
          default_timezone: timezone,
        }),
      });
      setSavedSuccess(true);
      setApiKey("");
      await loadData();
    } catch (err: any) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Settings & System Governance"
        subtitle="Configure LLM abstraction, deployment environment, and inspect immutable audit events"
      />

      <div className="p-8 space-y-8 max-w-7xl">
        {/* Settings Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Configuration Form */}
          <div className="lg:col-span-2 bg-[#18181B] border border-[#27272A] rounded-xl p-6 space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-[#27272A]">
              <div>
                <h3 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-indigo-400" />
                  Provider Abstraction & AI Configuration
                </h3>
                <p className="text-xs text-zinc-400">
                  Switch between deterministic rule-based orchestrator and external LLM providers
                </p>
              </div>
              <StatusBadge status={config?.environment || "development"} />
            </div>

            {savedSuccess && (
              <div className="p-3 bg-emerald-950/40 border border-emerald-800 rounded-lg text-xs text-emerald-300 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                <span>Settings updated successfully. Secret credentials safely persisted server-side.</span>
              </div>
            )}

            <form onSubmit={handleSave} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-zinc-400 block mb-1 font-medium">Orchestrator Mode *</label>
                  <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full bg-[#222226] border border-[#27272A] rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500 font-medium"
                  >
                    <option value="deterministic">Deterministic Engine (Local Safe Fallback)</option>
                    <option value="gemini">Google Gemini (Provider API)</option>
                    <option value="openai">OpenAI Compatible (Provider API)</option>
                  </select>
                  <span className="text-[11px] text-zinc-500 mt-1 block">
                    Core workflows function 100% locally without external keys.
                  </span>
                </div>

                <div>
                  <label className="text-zinc-400 block mb-1 font-medium">Model Identifier</label>
                  <input
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full bg-[#222226] border border-[#27272A] rounded-lg px-3 py-2 text-zinc-100 font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-zinc-400 block mb-1 font-medium flex items-center justify-between">
                  <span>API Key (Optional for External LLMs)</span>
                  {config?.llm_api_key_configured && (
                    <span className="text-emerald-400 font-mono text-[10px]">
                      Configured: {config.llm_api_key_masked}
                    </span>
                  )}
                </label>
                <input
                  type="password"
                  placeholder="Enter new key to update or leave blank to keep existing..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full bg-[#222226] border border-[#27272A] rounded-lg px-3 py-2 text-zinc-100 font-mono focus:outline-none focus:border-indigo-500"
                />
                <span className="text-[11px] text-zinc-500 mt-1 block">
                  Keys are stored server-side only and never transmitted to the frontend.
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-zinc-400 block mb-1 font-medium">Default Timezone</label>
                  <input
                    type="text"
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    className="w-full bg-[#222226] border border-[#27272A] rounded-lg px-3 py-2 text-zinc-100 font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-zinc-400 block mb-1 font-medium">Default Mock Employer Endpoint</label>
                  <input
                    type="text"
                    disabled
                    value={config?.mock_destination_default || "mock://employer.recruitment/v1/intake"}
                    className="w-full bg-[#18181B] border border-[#27272A] rounded-lg px-3 py-2 text-zinc-400 font-mono text-[11px]"
                  />
                </div>
              </div>

              <div className="pt-4 border-t border-[#27272A] flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm shadow-indigo-600/30 transition-colors"
                >
                  <Save className="w-3.5 h-3.5" />
                  {saving ? "Saving Changes..." : "Save Settings"}
                </button>
              </div>
            </form>
          </div>

          {/* Quick Engine Specifications */}
          <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-6 space-y-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
              Governance & Integrity Specs
            </h4>
            <div className="space-y-3 text-xs">
              <div className="p-3 bg-[#222226] rounded-lg border border-[#27272A]">
                <span className="text-zinc-500 block">Eligibility Rules Engine</span>
                <span className="text-zinc-200 font-semibold font-mono">
                  {config?.rules_engine_version || "2026.1-deterministic"}
                </span>
              </div>
              <div className="p-3 bg-[#222226] rounded-lg border border-[#27272A]">
                <span className="text-zinc-500 block">Safety Gate Invalidation</span>
                <span className="text-zinc-200 font-semibold">
                  SHA-256 Roster Binding Active
                </span>
              </div>
              <div className="p-3 bg-[#222226] rounded-lg border border-[#27272A]">
                <span className="text-zinc-500 block">Audit Log Policy</span>
                <span className="text-zinc-200 font-semibold">
                  Append-Only Immutable Ledger
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Append-Only Audit Trail */}
        <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#27272A]">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-semibold text-zinc-100">
                Immutable System Audit Trail ({auditLogs.length} Events)
              </h3>
            </div>
            <button
              onClick={loadData}
              className="p-1.5 bg-[#222226] hover:bg-zinc-800 border border-[#27272A] rounded text-zinc-400 hover:text-zinc-200"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2 max-h-96 overflow-y-auto font-mono text-xs">
            {auditLogs.length > 0 ? (
              auditLogs.map((log) => (
                <div
                  key={log.id}
                  className="p-3 bg-[#222226] border border-[#27272A] rounded-lg flex flex-wrap items-center justify-between gap-2"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-zinc-800 text-zinc-300 font-bold">
                        {log.event_type}
                      </span>
                      <span className="text-zinc-400 text-[11px]">by {log.actor}</span>
                    </div>
                    <p className="text-zinc-300 font-sans text-xs">{log.action_details}</p>
                  </div>
                  <span className="text-[10px] text-zinc-500 shrink-0">
                    {formatDateTime(log.created_at)}
                  </span>
                </div>
              ))
            ) : (
              <div className="py-6 text-center text-xs text-zinc-500 font-sans">
                No audit events recorded yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
