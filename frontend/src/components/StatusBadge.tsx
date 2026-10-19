import React from "react";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const norm = status?.toLowerCase() || "";

  let colorClasses = "bg-zinc-800 text-zinc-300 border-zinc-700";

  if (["verified", "eligible", "approved", "success", "active", "healthy", "present"].includes(norm)) {
    colorClasses = "bg-emerald-950/60 text-emerald-300 border-emerald-800/80";
  } else if (["pending", "waiting_approval", "warning", "not marked"].includes(norm)) {
    colorClasses = "bg-amber-950/60 text-amber-300 border-amber-800/80";
  } else if (["mismatch", "failed", "excluded", "rejected", "invalidated", "absent", "error"].includes(norm)) {
    colorClasses = "bg-rose-950/60 text-rose-300 border-rose-800/80";
  } else if (["submitted", "completed", "running"].includes(norm)) {
    colorClasses = "bg-indigo-950/60 text-indigo-300 border-indigo-800/80";
  }

  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border tracking-wide uppercase",
        colorClasses,
        className
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-80" />
      {status}
    </span>
  );
}
