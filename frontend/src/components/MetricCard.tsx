import React from "react";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  variant?: "default" | "indigo" | "emerald" | "amber" | "rose";
  trend?: string;
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = "default",
  trend,
}: MetricCardProps) {
  const iconColor = {
    default: "text-zinc-400 bg-zinc-800/80 border-zinc-700/60",
    indigo: "text-indigo-400 bg-indigo-950/40 border-indigo-800/50",
    emerald: "text-emerald-400 bg-emerald-950/40 border-emerald-800/50",
    amber: "text-amber-400 bg-amber-950/40 border-amber-800/50",
    rose: "text-rose-400 bg-rose-950/40 border-rose-800/50",
  }[variant];

  return (
    <div className="bg-[#18181B] border border-[#27272A] rounded-xl p-5 shadow-sm hover:border-zinc-700 transition-colors">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">{title}</span>
        <div className={cn("p-2 rounded-lg border", iconColor)}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="mt-3 flex items-baseline justify-between">
        <div className="text-2xl font-bold text-zinc-100 tracking-tight">{value}</div>
        {trend && <span className="text-xs text-zinc-400 font-medium">{trend}</span>}
      </div>
      {subtitle && <p className="mt-1 text-xs text-zinc-500">{subtitle}</p>}
    </div>
  );
}
