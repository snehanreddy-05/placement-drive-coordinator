"use client";

import React, { useEffect, useState } from "react";
import { Bell, ShieldCheck, Activity } from "lucide-react";
import { fetchApi } from "@/lib/api";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);

  useEffect(() => {
    fetchApi<{ status: string }>("/health")
      .then((data) => setApiOnline(data.status === "healthy"))
      .catch(() => setApiOnline(false));
  }, []);

  return (
    <header className="h-16 bg-[#18181B] border-b border-[#27272A] px-8 flex items-center justify-between shrink-0">
      <div>
        <h1 className="text-lg font-bold text-zinc-100 tracking-tight">{title}</h1>
        {subtitle && <p className="text-xs text-zinc-400">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-4">
        {/* Environment Badge */}
        <div className="flex items-center gap-2 bg-[#27272A]/80 border border-zinc-700/60 px-3 py-1 rounded-full text-xs">
          <div
            className={`w-2 h-2 rounded-full ${
              apiOnline === true ? "bg-emerald-400" : apiOnline === false ? "bg-rose-500" : "bg-amber-400"
            }`}
          />
          <span className="text-zinc-300 font-medium">
            {apiOnline === true ? "API Connected" : apiOnline === false ? "Backend Offline" : "Connecting..."}
          </span>
        </div>

        {/* Mock Mode Pill */}
        <div className="hidden sm:flex items-center gap-1.5 bg-indigo-950/50 border border-indigo-800/50 px-2.5 py-1 rounded-full text-xs text-indigo-300 font-medium">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Local Safe Mock Mode</span>
        </div>
      </div>
    </header>
  );
}
