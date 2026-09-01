import React from "react";
import { useTelemetry } from "../../context/TelemetryContext";
import { Radio } from "lucide-react";

export default function LiveTelemetryTicker() {
  const { liveReadings, isConnected } = useTelemetry();
  const readings = Object.values(liveReadings).slice(-8);

  if (readings.length === 0) return null;

  return (
    <div className="app-card p-2.5 flex items-center gap-3 overflow-x-auto scrollbar-none">
      <div className="flex items-center gap-1.5 flex-shrink-0 text-[11px] font-mono font-bold text-neutral-900 dark:text-white pl-1 border-r border-neutral-200 dark:border-neutral-800 pr-3">
        <Radio className={`w-3.5 h-3.5 ${isConnected ? "text-emerald-600 dark:text-emerald-400 animate-pulse" : "text-rose-600 dark:text-rose-400"}`} />
        <span>KAFKA LIVE:</span>
      </div>

      <div className="flex items-center gap-2 overflow-x-auto scrollbar-none">
        {readings.map((r, i) => (
          <div
            key={i}
            className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-neutral-100 dark:bg-[#121212] border border-neutral-200 dark:border-neutral-800 text-[11px] whitespace-nowrap font-mono"
          >
            <span className="text-neutral-500 font-semibold">{r.equipment_id}</span>
            <span className="text-neutral-400">/</span>
            <span className="text-neutral-700 dark:text-neutral-300">{r.sensor_name}</span>
            <span className={`font-bold tabular-nums ${r.is_anomaly ? "text-rose-700 dark:text-rose-400" : "text-emerald-700 dark:text-emerald-400"}`}>
              {r.value} {r.unit}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
