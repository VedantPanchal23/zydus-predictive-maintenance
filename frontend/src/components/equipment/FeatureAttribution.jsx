import React from "react";
import { Brain, Wrench } from "lucide-react";

export default function FeatureAttribution({ featureAttribution = [] }) {
  const items = featureAttribution.length > 0
    ? featureAttribution
    : [
        { sensor_name: "vibration_hz", impact_percentage: 45.2, current_value: 32.4, unit: "Hz" },
        { sensor_name: "current_draw_a", impact_percentage: 31.8, current_value: 24.1, unit: "A" },
        { sensor_name: "temperature_c", impact_percentage: 14.5, current_value: 28.5, unit: "C" },
        { sensor_name: "pressure_bar", impact_percentage: 8.5, current_value: 0.45, unit: "bar" },
      ];

  return (
    <div className="app-card p-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="text-xs font-bold text-neutral-900 dark:text-white flex items-center gap-1.5 uppercase tracking-wider font-mono">
            <Brain className="w-4 h-4 text-neutral-700 dark:text-neutral-300" />
            <span>Root-Cause Feature Attribution</span>
          </h3>
          <p className="text-[11px] text-neutral-500 mt-0.5">SHAP-based Sensor Impact Decomposition</p>
        </div>
        <span className="text-[9px] font-mono font-semibold px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 uppercase">
          XAI MODEL
        </span>
      </div>

      <div className="space-y-2.5 mt-3">
        {items.map((item, idx) => {
          const pct = item.impact_percentage || 0;
          return (
            <div key={idx} className="space-y-1">
              <div className="flex items-center justify-between text-xs font-mono">
                <div className="flex items-center gap-1.5">
                  <span className="text-neutral-800 dark:text-neutral-200 font-semibold">{item.sensor_name}</span>
                  {item.current_value !== undefined && (
                    <span className="text-[10px] text-neutral-400">
                      ({item.current_value} {item.unit})
                    </span>
                  )}
                </div>
                <span className="text-neutral-900 dark:text-white font-bold tabular-nums">{pct.toFixed(1)}%</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-neutral-100 dark:bg-neutral-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-neutral-900 dark:bg-white transition-all duration-300"
                  style={{ width: `${Math.min(100, Math.max(3, pct))}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-3 pt-2.5 border-t border-neutral-200 dark:border-neutral-800 text-xs text-neutral-600 dark:text-neutral-400 flex items-start gap-2 bg-neutral-50 dark:bg-[#121212] p-2.5 rounded-md">
        <Wrench className="w-3.5 h-3.5 text-neutral-500 flex-shrink-0 mt-0.5" />
        <span className="text-[11px] leading-relaxed">
          Primary driver: <strong className="text-neutral-900 dark:text-white font-mono">{items[0]?.sensor_name}</strong> ({items[0]?.impact_percentage?.toFixed(1)}%). Recommend mechanical coupling check per SOP.
        </span>
      </div>
    </div>
  );
}
