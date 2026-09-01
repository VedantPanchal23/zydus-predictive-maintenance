import React from "react";
import { TrendingUp, TrendingDown } from "lucide-react";

export default function KpiCard({ title, value, subtitle, icon: Icon, trend, trendValue, color = "neutral" }) {
  return (
    <div className="app-card p-4 flex flex-col justify-between">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 tracking-wider uppercase font-mono">{title}</span>
        <div className="p-1.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300">
          <Icon className="w-4 h-4" />
        </div>
      </div>

      <div className="mt-3">
        <div className="text-2xl font-bold text-neutral-900 dark:text-white font-mono tracking-tight tabular-nums">{value}</div>
        <div className="mt-1 flex items-center justify-between text-xs text-neutral-500 dark:text-neutral-400">
          <span className="truncate pr-2">{subtitle}</span>
          {trend && (
            <span className={`inline-flex items-center gap-0.5 font-mono text-[11px] font-semibold flex-shrink-0 ${trend === "up" ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"}`}>
              {trend === "up" ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
              {trendValue}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
