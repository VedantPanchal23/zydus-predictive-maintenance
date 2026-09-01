import React from "react";
import { Activity, ShieldCheck, AlertTriangle } from "lucide-react";

export default function PhysicsCouplingCard({ physicsDiagnostics }) {
  const isAnom = physicsDiagnostics?.is_physically_anomalous || false;
  const patterns = physicsDiagnostics?.detected_patterns || [];
  const matrix = physicsDiagnostics?.correlation_matrix || physicsDiagnostics?.cross_correlation_matrix || {};
  const sensors = Object.keys(matrix).slice(0, 5);

  return (
    <div className="app-card p-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="text-xs font-bold text-neutral-900 dark:text-white flex items-center gap-1.5 uppercase tracking-wider font-mono">
            <Activity className="w-4 h-4 text-neutral-700 dark:text-neutral-300" />
            <span>Physics Cross-Sensor Diagnostics</span>
          </h3>
          <p className="text-[11px] text-neutral-500 mt-0.5">Thermodynamic & Electromechanical Coupling</p>
        </div>
        <span
          className={`text-[9px] font-mono font-semibold px-2 py-0.5 rounded border uppercase ${
            isAnom
              ? "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800"
              : "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800"
          }`}
        >
          {isAnom ? "Decoupling Alert" : "Nominal Coupling"}
        </span>
      </div>

      {patterns.length > 0 ? (
        <div className="my-2 space-y-1.5">
          {patterns.map((p, i) => (
            <div key={i} className="p-2 rounded bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-700 dark:text-rose-300 flex items-start gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              <span>{p}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="my-2 p-2 rounded bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-700 dark:text-emerald-300 flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 flex-shrink-0" />
          <span className="text-[11px]">Thermodynamic & electromechanical cross-correlation within 99% nominal bounds.</span>
        </div>
      )}

      {/* Matrix Table */}
      {sensors.length > 0 && (
        <div className="mt-2">
          <div className="text-[10px] text-neutral-400 font-mono font-semibold uppercase mb-1">Pearson Correlation Matrix</div>
          <div className="overflow-x-auto rounded border border-neutral-200 dark:border-neutral-800">
            <table className="w-full text-[10px] font-mono text-center">
              <thead>
                <tr className="border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-[#121212] text-neutral-500">
                  <th className="p-1 text-left font-medium">Sensor</th>
                  {sensors.map((s) => (
                    <th key={s} className="p-1 font-medium truncate max-w-[60px]">{s.replace("_", "")}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800/60">
                {sensors.map((row) => (
                  <tr key={row} className="hover:bg-neutral-50 dark:hover:bg-[#121212]">
                    <td className="p-1 text-left text-neutral-700 dark:text-neutral-300 font-medium truncate max-w-[80px]">{row}</td>
                    {sensors.map((col) => {
                      const val = matrix[row]?.[col] ?? 0.0;
                      let colorClass = "text-neutral-500";
                      if (val >= 0.7) colorClass = "text-neutral-900 dark:text-white font-bold";
                      else if (val <= -0.4) colorClass = "text-amber-700 dark:text-amber-400 font-bold";
                      return (
                        <td key={col} className={`p-1 tabular-nums ${colorClass}`}>
                          {val.toFixed(2)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
