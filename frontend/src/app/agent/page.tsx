"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Bot,
  Send,
  Terminal,
  ShieldAlert,
  Sparkles,
  CheckCircle2,
  Clock,
  ArrowRight,
  RefreshCw,
  Cpu,
  ShieldCheck,
  AlertCircle,
} from "lucide-react";
import { Header } from "@/components/Header";
import { StatusBadge } from "@/components/StatusBadge";
import { fetchApi } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface ToolCallItem {
  id: string;
  tool_name: string;
  arguments: any;
  result_summary: string;
  status: string;
  timestamp: string;
}

interface AgentResponse {
  execution_id: string;
  prompt: string;
  status: string;
  summary: string;
  current_task: string;
  next_action: string;
  provider_used: string;
  created_at: string;
  tool_calls: ToolCallItem[];
}

interface ExecutionHistoryItem {
  id: string;
  prompt: string;
  status: string;
  summary: string;
  next_action: string;
  tool_calls_count: number;
  created_at: string;
}

const PRESET_PROMPTS = [
  "Evaluate eligibility for the selected drive.",
  "Explain why student STU104 was excluded.",
  "Find students with missing consent.",
  "Detect schedule clashes.",
  "Prepare the eligible roster for review.",
  "Show the result of the latest upload verification.",
];

export default function AgentWorkspacePage() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentExecution, setCurrentExecution] = useState<AgentResponse | null>(null);
  const [history, setHistory] = useState<ExecutionHistoryItem[]>([]);

  const loadHistory = async () => {
    try {
      const data = await fetchApi<ExecutionHistoryItem[]>("/agent/executions");
      setHistory(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleSendPrompt = async (textToSend?: string) => {
    const q = textToSend || prompt;
    if (!q.trim()) return;

    try {
      setLoading(true);
      const res = await fetchApi<AgentResponse>("/agent/chat", {
        method: "POST",
        body: JSON.stringify({ prompt: q }),
      });
      setCurrentExecution(res);
      setPrompt("");
      await loadHistory();
    } catch (err: any) {
      alert(`Agent execution failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadPastExecution = async (id: string) => {
    try {
      const data = await fetchApi<{ execution: any; tool_calls: ToolCallItem[] }>(`/agent/executions/${id}`);
      setCurrentExecution({
        execution_id: data.execution.id,
        prompt: data.execution.prompt,
        status: data.execution.status,
        summary: data.execution.summary,
        current_task: data.execution.current_task,
        next_action: data.execution.next_action,
        provider_used: data.execution.provider_used,
        created_at: data.execution.created_at,
        tool_calls: data.tool_calls,
      });
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Agent Workspace"
        subtitle="Autonomous recruitment orchestrator with tool execution logs and mandatory human safety gates"
      />

      <div className="p-8 space-y-6 max-w-7xl">
        {/* Safety Gate Banner */}
        <div className="bg-gradient-to-r from-indigo-950/60 to-purple-950/40 border border-indigo-800/60 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600 rounded-lg text-white shadow-md shadow-indigo-600/30">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold text-zinc-100">
                  PlacementOS Autonomous Agent Orchestrator
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono">
                  Controlled Execution
                </span>
              </div>
              <p className="text-xs text-zinc-400">
                Agent invokes genuine backend tools. External submissions halt at the human approval gate.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-zinc-400 bg-black/40 px-3 py-1.5 rounded-lg border border-zinc-800">
            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
            <span>Mode: {currentExecution?.provider_used || "Deterministic Rule-Based"}</span>
          </div>
        </div>

        {/* Preset Prompt Pills */}
        <div className="space-y-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block">
            Suggested Placement Queries
          </span>
          <div className="flex flex-wrap gap-2">
            {PRESET_PROMPTS.map((p, idx) => (
              <button
                key={idx}
                onClick={() => handleSendPrompt(p)}
                disabled={loading}
                className="px-3 py-1.5 bg-[#18181B] hover:bg-zinc-800 border border-[#27272A] hover:border-indigo-500/60 rounded-lg text-xs text-zinc-300 hover:text-white transition-colors text-left"
              >
                "{p}"
              </button>
            ))}
          </div>
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendPrompt();
          }}
          className="relative"
        >
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Type your recruitment request (e.g. 'Evaluate eligibility for drive', 'Explain why student STU104 was excluded')..."
            disabled={loading}
            className="w-full bg-[#18181B] border border-[#27272A] rounded-xl pl-4 pr-24 py-3.5 text-xs text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-indigo-500 shadow-sm"
          />
          <button
            type="submit"
            disabled={loading || !prompt.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm shadow-indigo-600/30 transition-colors"
          >
            {loading ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <>
                <span>Execute</span>
                <Send className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </form>

        {/* Main Content: Execution Trace & History */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Active Execution Trace */}
          <div className="lg:col-span-2 space-y-4">
            {currentExecution ? (
              <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-6 space-y-5">
                <div className="flex items-start justify-between pb-4 border-b border-[#27272A]">
                  <div>
                    <span className="text-[11px] font-mono text-zinc-500 block">
                      Execution #{currentExecution.execution_id.slice(0, 8)} • {formatDateTime(currentExecution.created_at)}
                    </span>
                    <h4 className="text-base font-semibold text-zinc-100 mt-0.5">
                      "{currentExecution.prompt}"
                    </h4>
                  </div>
                  <StatusBadge status={currentExecution.status} />
                </div>

                {/* Summary Box */}
                <div className="p-4 bg-[#222226] border border-[#27272A] rounded-lg space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 block">
                    Execution Outcome
                  </span>
                  <p className="text-xs text-zinc-200 leading-relaxed">{currentExecution.summary}</p>

                  {/* Safety Gate Warning Pill if waiting approval */}
                  {currentExecution.status === "WAITING_APPROVAL" && (
                    <div className="mt-3 p-3 bg-amber-950/40 border border-amber-800/80 rounded-lg flex items-center justify-between">
                      <div className="flex items-center gap-2 text-amber-300 text-xs">
                        <ShieldAlert className="w-4 h-4 shrink-0" />
                        <span>MANDATORY SAFETY GATE: External upload halted awaiting human sign-off.</span>
                      </div>
                      <Link
                        href="/approvals"
                        className="px-3 py-1 bg-amber-600 hover:bg-amber-500 text-white rounded text-xs font-semibold flex items-center gap-1 shrink-0"
                      >
                        Review in Approval Center <ArrowRight className="w-3 h-3" />
                      </Link>
                    </div>
                  )}

                  {/* Next Action Recommendation */}
                  {currentExecution.next_action && currentExecution.status !== "WAITING_APPROVAL" && (
                    <div className="mt-2 text-xs text-indigo-300 font-medium flex items-center gap-1.5">
                      <ArrowRight className="w-3.5 h-3.5" />
                      <span>Next Action: {currentExecution.next_action}</span>
                    </div>
                  )}
                </div>

                {/* Tool Execution Logs */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                      <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                      Tool Execution Trace ({currentExecution.tool_calls?.length || 0} calls)
                    </span>
                  </div>

                  <div className="space-y-2 font-mono text-xs">
                    {currentExecution.tool_calls && currentExecution.tool_calls.length > 0 ? (
                      currentExecution.tool_calls.map((tc, idx) => (
                        <div
                          key={tc.id || idx}
                          className="bg-[#121215] border border-[#27272A] rounded-lg p-3 space-y-2"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-indigo-400 font-bold">
                              tool_call: {tc.tool_name}()
                            </span>
                            <span className="text-[10px] text-zinc-500">{formatDateTime(tc.timestamp)}</span>
                          </div>
                          <div className="text-[11px] text-zinc-400">
                            <span className="text-zinc-500">args:</span> {JSON.stringify(tc.arguments)}
                          </div>
                          <div className="text-[11px] text-zinc-300 bg-[#18181B] p-2 rounded border border-[#27272A] overflow-x-auto">
                            <span className="text-emerald-400">output:</span> {tc.result_summary}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="p-4 bg-[#141417] rounded-lg text-center text-xs text-zinc-500 font-sans">
                        No sub-tools called. Request handled directly.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-12 text-center space-y-3">
                <Bot className="w-10 h-10 text-zinc-600 mx-auto" />
                <h4 className="text-sm font-semibold text-zinc-300">Agent Ready</h4>
                <p className="text-xs text-zinc-500 max-w-sm mx-auto">
                  Select a suggested query above or type a natural language goal to orchestrate recruitment operations.
                </p>
              </div>
            )}
          </div>

          {/* Past Executions Sidebar */}
          <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-5 space-y-4 h-fit">
            <div className="flex items-center justify-between pb-3 border-b border-[#27272A]">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
                Execution History
              </h4>
              <button
                onClick={loadHistory}
                className="text-zinc-500 hover:text-zinc-300 text-xs"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {history.length > 0 ? (
                history.map((h) => (
                  <div
                    key={h.id}
                    onClick={() => loadPastExecution(h.id)}
                    className="p-3 bg-[#222226] hover:bg-zinc-800 border border-[#27272A] rounded-lg cursor-pointer transition-colors space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-zinc-200 line-clamp-1">
                        "{h.prompt}"
                      </span>
                      <StatusBadge status={h.status} />
                    </div>
                    <p className="text-[11px] text-zinc-400 line-clamp-1">{h.summary}</p>
                    <div className="flex items-center justify-between text-[10px] text-zinc-500 font-mono">
                      <span>Tools: {h.tool_calls_count}</span>
                      <span>{formatDateTime(h.created_at)}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-6 text-center text-xs text-zinc-500">
                  No execution history yet.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
