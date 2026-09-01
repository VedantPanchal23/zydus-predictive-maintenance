import React, { useState, useEffect } from "react";
import { getDlqRecords } from "../services/api";
import { formatDateTime } from "../utils/formatters";
import { Archive, RefreshCw, AlertTriangle } from "lucide-react";

export default function DlqInspectorPage() {
  const [dlqRecords, setDlqRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadDlq = async (manual = false) => {
    if (manual) setIsRefreshing(true);
    try {
      const data = await getDlqRecords(100);
      const items = data?.dlq_records || data?.records || (Array.isArray(data) ? data : []);
      setDlqRecords(items);
    } catch (err) {
      console.error("Failed to load DLQ records:", err);
      setDlqRecords([]);
    } finally {
      setLoading(false);
      if (manual) {
        setTimeout(() => setIsRefreshing(false), 500);
      }
    }
  };

  useEffect(() => {
    loadDlq();
  }, []);

  const safeRecords = Array.isArray(dlqRecords) ? dlqRecords : [];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-neutral-900 dark:text-white flex items-center gap-2 uppercase tracking-wider font-mono">
            <Archive className="w-4 h-4 text-neutral-700 dark:text-neutral-300" />
            <span>Telemetry Dead Letter Queue (DLQ)</span>
          </h2>
          <p className="text-xs text-neutral-500 mt-0.5">Physical sensor boundary, NaN/Inf, and clock skew validation quarantine</p>
        </div>

        <button
          onClick={() => loadDlq(true)}
          disabled={isRefreshing}
          className="app-btn-secondary text-xs py-1.5 px-3"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-neutral-900 dark:text-white" : "text-neutral-500"}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Quarantine Table */}
      <div className="app-card overflow-hidden">
        <div className="p-3.5 border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-[#121212] flex items-center justify-between">
          <span className="text-xs font-mono text-neutral-700 dark:text-neutral-300">
            Total Quarantined Records: <strong className="font-bold">{safeRecords.length}</strong>
          </span>
          <span className="text-[11px] font-mono text-neutral-400">Auto-Filtered before DB Ingestion</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-white dark:bg-black text-neutral-500 font-mono uppercase text-[10px] border-b border-neutral-200 dark:border-neutral-800">
              <tr>
                <th className="p-3">ID</th>
                <th className="p-3">Asset Code</th>
                <th className="p-3">Sensor Channel</th>
                <th className="p-3">Rejection Reason</th>
                <th className="p-3">Quarantine Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800/60 font-sans">
              {safeRecords.map((r) => (
                <tr key={r.id} className="hover:bg-neutral-50 dark:hover:bg-[#121212] transition-colors">
                  <td className="p-3 font-mono text-neutral-400">#{r.id}</td>
                  <td className="p-3 font-mono font-bold text-neutral-900 dark:text-white">{r.equipment_id}</td>
                  <td className="p-3 font-mono text-neutral-700 dark:text-neutral-300">{r.sensor_name}</td>
                  <td className="p-3 text-rose-700 dark:text-rose-400 font-medium flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                    <span>{r.error_reason}</span>
                  </td>
                  <td className="p-3 font-mono text-neutral-500 whitespace-nowrap text-[11px]">
                    {formatDateTime(r.created_at || r.timestamp)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
