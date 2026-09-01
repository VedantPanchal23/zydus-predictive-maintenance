import React from "react";
import { ShieldCheck, AlertTriangle, AlertOctagon, Activity, HelpCircle } from "lucide-react";

export default function StatusBadge({ status, size = "md", showIcon = true }) {
  const norm = (status || "NORMAL").toUpperCase();

  const configs = {
    NORMAL: {
      label: "NORMAL",
      bg: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800",
      dot: "bg-emerald-600 dark:bg-emerald-400",
      icon: ShieldCheck,
    },
    HEALTHY: {
      label: "HEALTHY",
      bg: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800",
      dot: "bg-emerald-600 dark:bg-emerald-400",
      icon: ShieldCheck,
    },
    ACTIVE: {
      label: "ACTIVE",
      bg: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800",
      dot: "bg-emerald-600 dark:bg-emerald-400",
      icon: ShieldCheck,
    },
    WATCH: {
      label: "WATCH",
      bg: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800",
      dot: "bg-blue-600 dark:bg-blue-400",
      icon: Activity,
    },
    WARNING: {
      label: "WARNING",
      bg: "bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800",
      dot: "bg-amber-600 dark:bg-amber-400",
      icon: AlertTriangle,
    },
    CRITICAL: {
      label: "CRITICAL",
      bg: "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800",
      dot: "bg-rose-600 dark:bg-rose-400",
      icon: AlertOctagon,
    },
    LIFE_CRITICAL: {
      label: "LIFE CRITICAL",
      bg: "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-800",
      dot: "bg-purple-600 dark:bg-purple-400",
      icon: AlertOctagon,
    },
  };

  const config = configs[norm] || {
    label: norm,
    bg: "bg-neutral-100 text-neutral-700 border-neutral-200 dark:bg-neutral-800 dark:text-neutral-300 dark:border-neutral-700",
    dot: "bg-neutral-500",
    icon: HelpCircle,
  };

  const Icon = config.icon;
  const sizeClasses = size === "sm"
    ? "px-2 py-0.5 text-[10px] tracking-wider font-mono font-medium"
    : "px-2.5 py-0.5 text-xs tracking-wider font-mono font-medium";

  return (
    <span className={`inline-flex items-center gap-1.5 border rounded-full ${sizeClasses} ${config.bg}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      {showIcon && <Icon className="w-3 h-3 flex-shrink-0" />}
      <span>{config.label}</span>
    </span>
  );
}
