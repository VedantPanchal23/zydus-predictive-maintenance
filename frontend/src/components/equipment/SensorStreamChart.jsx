import React, { useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Activity } from "lucide-react";
import { formatDateTime } from "../../utils/formatters";
import { useTheme } from "../../context/ThemeContext";

export default function SensorStreamChart({ sensorHistory = {} }) {
  const { isDark } = useTheme();
  const sensorNames = Object.keys(sensorHistory);
  const [selectedSensor, setSelectedSensor] = useState(sensorNames[0] || "vibration_hz");

  const activeSensor = sensorNames.includes(selectedSensor) ? selectedSensor : (sensorNames[0] || "vibration_hz");
  const data = (sensorHistory[activeSensor] || []).slice(-30).map((pt) => ({
    time: formatDateTime(pt.timestamp),
    value: pt.value,
  }));

  return (
    <div className="app-card p-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-2">
        <div>
          <h3 className="text-xs font-bold text-neutral-900 dark:text-white flex items-center gap-1.5 uppercase tracking-wider font-mono">
            <Activity className="w-4 h-4 text-neutral-700 dark:text-neutral-300" />
            <span>Sensor Waveform Stream</span>
          </h3>
          <p className="text-[11px] text-neutral-500 mt-0.5">High-Resolution Time-Series Channel Waveform</p>
        </div>

        {/* Channel Selector */}
        <div className="flex items-center gap-1 flex-wrap">
          {sensorNames.map((s) => (
            <button
              key={s}
              onClick={() => setSelectedSensor(s)}
              className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                activeSensor === s
                  ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 font-bold shadow-sm"
                  : "bg-neutral-100 dark:bg-[#121212] text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white border border-neutral-200 dark:border-neutral-800"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="h-52 w-full mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={isDark ? "#262626" : "#e5e7eb"} />
            <XAxis dataKey="time" stroke={isDark ? "#737373" : "#9ca3af"} tick={{ fontSize: 9 }} />
            <YAxis stroke={isDark ? "#737373" : "#9ca3af"} tick={{ fontSize: 9 }} />
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
              formatter={(val) => [val, activeSensor]}
            />
            <Line type="monotone" dataKey="value" stroke={isDark ? "#ffffff" : "#003b73"} strokeWidth={1.75} dot={{ r: 1.5, fill: isDark ? "#ffffff" : "#003b73" }} activeDot={{ r: 3.5 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
