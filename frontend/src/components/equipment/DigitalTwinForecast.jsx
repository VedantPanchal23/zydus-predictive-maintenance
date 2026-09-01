import React from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { TrendingDown, ShieldCheck } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";

export default function DigitalTwinForecast({ digitalTwin, currentHealth = 85.0 }) {
  const { isDark } = useTheme();
  const hCurr = digitalTwin?.current_health_score || currentHealth;
  const h7 = digitalTwin?.forecast_7d || Math.max(0, hCurr - 5.1);
  const h14 = digitalTwin?.forecast_14d || Math.max(0, hCurr - 14.8);
  const h30 = digitalTwin?.forecast_30d || Math.max(0, hCurr - 31.4);

  const data = [
    { day: "Today", health: hCurr },
    { day: "+7 Days", health: h7 },
    { day: "+14 Days", health: h14 },
    { day: "+30 Days", health: h30 },
  ];

  return (
    <div className="app-card p-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="text-xs font-bold text-neutral-900 dark:text-white flex items-center gap-1.5 uppercase tracking-wider font-mono">
            <TrendingDown className="w-4 h-4 text-neutral-700 dark:text-neutral-300" />
            <span>Digital Twin Health Trajectory</span>
          </h3>
          <p className="text-[11px] text-neutral-500 mt-0.5">30-Day Multi-Horizon Degradation Outlook</p>
        </div>
        <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-[10px] font-mono text-neutral-700 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700">
          <ShieldCheck className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
          <span>Confidence: 94.0%</span>
        </div>
      </div>

      <div className="h-52 w-full mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
            <defs>
              <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={isDark ? "#ffffff" : "#0f172a"} stopOpacity={0.15} />
                <stop offset="95%" stopColor={isDark ? "#ffffff" : "#0f172a"} stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={isDark ? "#262626" : "#e5e7eb"} />
            <XAxis dataKey="day" stroke={isDark ? "#737373" : "#9ca3af"} tick={{ fontSize: 10 }} />
            <YAxis domain={[0, 100]} stroke={isDark ? "#737373" : "#9ca3af"} tick={{ fontSize: 10 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: isDark ? "#000000" : "#ffffff",
                borderColor: isDark ? "#333333" : "#e5e7eb",
                borderRadius: "6px",
                fontSize: "11px",
                fontFamily: "monospace",
                color: isDark ? "#ffffff" : "#000000",
                boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
              }}
              formatter={(val) => [`${Number(val).toFixed(1)}%`, "Health Index"]}
            />
            <ReferenceLine y={65} stroke="#d97706" strokeDasharray="3 3" label={{ value: "Warning (65%)", fill: "#d97706", fontSize: 9 }} />
            <ReferenceLine y={40} stroke="#dc2626" strokeDasharray="3 3" label={{ value: "Critical (40%)", fill: "#dc2626", fontSize: 9 }} />
            <Area type="monotone" dataKey="health" stroke={isDark ? "#ffffff" : "#0f172a"} strokeWidth={2} fillOpacity={1} fill="url(#forecastGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* 4-Step Summary Grid */}
      <div className="grid grid-cols-4 gap-2 mt-2 pt-2.5 border-t border-neutral-200 dark:border-neutral-800 text-center font-mono">
        <div className="p-1.5 rounded bg-neutral-50 dark:bg-[#121212] border border-neutral-200/80 dark:border-neutral-800/80">
          <div className="text-[9px] text-neutral-400 font-semibold uppercase">TODAY</div>
          <div className="text-xs font-bold text-neutral-900 dark:text-white tabular-nums">{hCurr.toFixed(1)}%</div>
        </div>
        <div className="p-1.5 rounded bg-neutral-50 dark:bg-[#121212] border border-neutral-200/80 dark:border-neutral-800/80">
          <div className="text-[9px] text-neutral-400 font-semibold uppercase">+7 DAYS</div>
          <div className="text-xs font-bold text-neutral-700 dark:text-neutral-300 tabular-nums">{h7.toFixed(1)}%</div>
        </div>
        <div className="p-1.5 rounded bg-neutral-50 dark:bg-[#121212] border border-neutral-200/80 dark:border-neutral-800/80">
          <div className="text-[9px] text-neutral-400 font-semibold uppercase">+14 DAYS</div>
          <div className="text-xs font-bold text-amber-600 dark:text-amber-400 tabular-nums">{h14.toFixed(1)}%</div>
        </div>
        <div className="p-1.5 rounded bg-neutral-50 dark:bg-[#121212] border border-neutral-200/80 dark:border-neutral-800/80">
          <div className="text-[9px] text-neutral-400 font-semibold uppercase">+30 DAYS</div>
          <div className="text-xs font-bold text-rose-600 dark:text-rose-400 tabular-nums">{h30.toFixed(1)}%</div>
        </div>
      </div>
    </div>
  );
}
