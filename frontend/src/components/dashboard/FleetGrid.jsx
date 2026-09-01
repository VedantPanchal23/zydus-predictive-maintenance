import React from "react";
import { useNavigate } from "react-router-dom";
import StatusBadge from "../common/StatusBadge";
import HealthGauge from "../common/HealthGauge";
import { formatCurrency, formatPercent } from "../../utils/formatters";
import { Clock, ArrowRight, Cpu } from "lucide-react";

export default function FleetGrid({ equipmentList, liveReadings, searchQuery }) {
  const navigate = useNavigate();

  const filtered = equipmentList.filter((eq) => {
    const q = (searchQuery || "").toLowerCase();
    return (
      eq.name.toLowerCase().includes(q) ||
      (eq.equipment_id && eq.equipment_id.toLowerCase().includes(q)) ||
      (eq.facility && eq.facility.toLowerCase().includes(q)) ||
      (eq.category && eq.category.toLowerCase().includes(q))
    );
  });

  if (filtered.length === 0) {
    return (
      <div className="app-card p-12 text-center text-neutral-500">
        <Cpu className="w-8 h-8 mx-auto mb-3 text-neutral-400 animate-pulse" />
        <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200">No assets found matching query.</p>
        <p className="text-xs text-neutral-500 mt-1">Search by asset code, equipment name, or manufacturing facility.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5">
      {filtered.map((item) => {
        const id = item.id || item.equipment_id;
        const code = item.equipment_id || item.name;
        const health = item.health_score || (item.digital_twin ? item.digital_twin.current_health_score / 100 : 0.85);
        const status = (item.status || "NORMAL").toUpperCase();
        const rul = item.days_to_failure || item.rul_days || 45.0;
        const failProb = item.failure_probability || 0.05;
        const batchVal = item.batch_value_usd || 150000;
        const expectedLoss = batchVal * failProb;

        // Top border status line
        let topBorder = "border-t-2 border-t-emerald-600";
        if (status === "CRITICAL" || status === "LIFE_CRITICAL") {
          topBorder = "border-t-2 border-t-rose-600";
        } else if (status === "WARNING") {
          topBorder = "border-t-2 border-t-amber-500";
        } else if (status === "WATCH") {
          topBorder = "border-t-2 border-t-blue-600";
        }

        return (
          <div
            key={id}
            onClick={() => navigate(`/equipment/${id}`)}
            className={`app-card p-4 cursor-pointer hover:border-neutral-400 dark:hover:border-neutral-600 group flex flex-col justify-between ${topBorder}`}
          >
            {/* Header: Tag, Name, Status */}
            <div>
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-[11px] font-mono font-bold text-neutral-900 dark:text-white tracking-wider truncate">
                    {code}
                  </div>
                  <h4 className="text-xs font-semibold text-neutral-800 dark:text-neutral-200 group-hover:text-neutral-900 dark:group-hover:text-white transition-colors line-clamp-1 mt-0.5">
                    {item.name}
                  </h4>
                </div>
                <StatusBadge status={status} size="sm" />
              </div>

              <div className="mt-1 text-[10px] text-neutral-500 truncate">
                {item.facility || "Central Manufacturing Block"}
              </div>
            </div>

            {/* Middle: Gauge & Metrics Well */}
            <div className="my-3 flex items-center justify-between gap-3 p-2.5 rounded-md bg-neutral-50 dark:bg-[#121212] border border-neutral-200/80 dark:border-neutral-800/80">
              <HealthGauge score={health} size={64} strokeWidth={5} label="Health" />
              <div className="space-y-1 text-xs text-right font-mono">
                <div>
                  <div className="text-[9px] text-neutral-400 font-semibold uppercase">Est. RUL</div>
                  <div className="font-bold text-neutral-800 dark:text-neutral-200 flex items-center justify-end gap-1 tabular-nums">
                    <Clock className="w-3 h-3 text-neutral-500" />
                    <span>{rul.toFixed(1)}d</span>
                  </div>
                </div>
                <div>
                  <div className="text-[9px] text-neutral-400 font-semibold uppercase">Batch Exposure</div>
                  <div className="font-bold text-neutral-700 dark:text-neutral-300 tabular-nums">
                    {formatCurrency(expectedLoss)}
                  </div>
                </div>
                <div>
                  <div className="text-[9px] text-neutral-400 font-semibold uppercase">Failure Prob</div>
                  <div className={`font-bold tabular-nums ${failProb > 0.4 ? "text-rose-700 dark:text-rose-400" : failProb > 0.2 ? "text-amber-700 dark:text-amber-400" : "text-emerald-700 dark:text-emerald-400"}`}>
                    {formatPercent(failProb)}
                  </div>
                </div>
              </div>
            </div>

            {/* Footer: Category & Action */}
            <div className="pt-2 border-t border-neutral-100 dark:border-neutral-800/80 flex items-center justify-between text-xs">
              <span className="text-[10px] font-mono text-neutral-500 truncate max-w-[130px]">
                {item.category || "Solid Dosage"}
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] text-neutral-900 dark:text-white font-medium group-hover:translate-x-0.5 transition-transform flex-shrink-0">
                <span>View Details</span>
                <ArrowRight className="w-3 h-3" />
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
