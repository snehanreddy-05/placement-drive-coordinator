"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Briefcase,
  ShieldCheck,
  Bot,
  CheckCircle2,
  CloudUpload,
  ClipboardList,
  Settings,
  Sparkles,
  ShieldAlert,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Student Roster", href: "/students", icon: Users },
  { name: "Placement Drives", href: "/drives", icon: Briefcase },
  { name: "Eligibility Analysis", href: "/eligibility", icon: ShieldCheck },
  { name: "Agent Workspace", href: "/agent", icon: Bot },
  { name: "Approval Center", href: "/approvals", icon: CheckCircle2 },
  { name: "Upload History", href: "/uploads", icon: CloudUpload },
  { name: "Attendance", href: "/attendance", icon: ClipboardList },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-[#18181B] border-r border-[#27272A] flex flex-col shrink-0 h-screen sticky top-0">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-[#27272A] gap-3">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
          <Sparkles className="w-4 h-4" />
        </div>
        <div>
          <span className="font-bold text-base tracking-tight text-zinc-100 flex items-center gap-1.5">
            PlacementOS
          </span>
          <span className="text-[10px] text-zinc-400 block -mt-0.5">Recruitment Coordinator</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[11px] font-semibold tracking-wider text-zinc-500 uppercase">
          Operations
        </div>
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group",
                isActive
                  ? "bg-indigo-600 text-white shadow-sm shadow-indigo-600/30"
                  : "text-zinc-400 hover:text-zinc-100 hover:bg-[#27272A]/60"
              )}
            >
              <Icon
                className={cn(
                  "w-4 h-4 transition-colors",
                  isActive ? "text-white" : "text-zinc-400 group-hover:text-zinc-200"
                )}
              />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* Engine Status Footer */}
      <div className="p-4 border-t border-[#27272A] bg-[#121215]">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-medium text-zinc-300">Deterministic Engine</span>
        </div>
        <p className="text-[11px] text-zinc-500 mt-1">Rules v2026.1 • SHA-256 Gated</p>
      </div>
    </aside>
  );
}
