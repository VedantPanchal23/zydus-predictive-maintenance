import React from "react";
import StatusBadge from "../common/StatusBadge";
import { formatDateTime } from "../../utils/formatters";
import { CheckCircle2, AlertOctagon, Clock } from "lucide-react";

export default function AlertsTable({ alerts = [], onAcknowledge, canAcknowledge }) {
  const safeAlerts = Array.isArray(alerts) ? alerts : [];

  if (safeAlerts.length === 0) {
    return (
      <div className="clinical-card p-12 text-center text-slate-500">
        <CheckCircle2 className="w-8 h-8 mx-auto mb-3 text-emerald-500/60" />
        <p className="text-sm font-medium text-slate-300">All Clear — Zero Active Incidents</p>
        <p className="text-xs text-slate-500 mt-1">Hysteresis monitoring confirms all 20 assets are operating within nominal bands.</p>
      </div>
    );
  }

  return (
    <div className="clinical-card overflow-hidden">
      <div className="p-3.5 border-b border-surface-border bg-surface-panel flex items-center justify-between">
        <h3 className="text-xs font-bold text-slate-100 flex items-center gap-2 uppercase font-mono tracking-wider">
          <AlertOctagon className="w-4 h-4 text-rose-400" />
          <span>Active GxP Incident Ledger</span>
        </h3>
        <span className="text-xs font-mono text-slate-400 font-semibold">Total: {safeAlerts.length} Incidents</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-surface-base text-slate-400 font-mono uppercase text-[10px] border-b border-surface-border">
            <tr>
              <th className="p-3">Severity</th>
              <th className="p-3">Asset Tag</th>
              <th className="p-3">Incident Description</th>
              <th className="p-3">Detected At</th>
              <th className="p-3">Status</th>
              <th className="p-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border/50 font-sans">
            {safeAlerts.map((alert) => {
              const isAck = !!alert.acknowledged_at;
              return (
                <tr key={alert.id} className="hover:bg-surface-elevated/40 transition-colors">
                  <td className="p-3">
                    <StatusBadge status={alert.severity} size="sm" />
                  </td>
                  <td className="p-3 font-mono font-bold text-slate-200">
                    {alert.equipment_name || alert.equipment_id}
                  </td>
                  <td className="p-3 text-slate-300 max-w-md text-[11px] leading-relaxed">
                    {alert.message}
                  </td>
                  <td className="p-3 font-mono text-slate-400 whitespace-nowrap text-[11px]">
                    {formatDateTime(alert.created_at)}
                  </td>
                  <td className="p-3">
                    {isAck ? (
                      <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-mono font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>ACKNOWLEDGED</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] text-amber-400 font-mono font-semibold animate-pulse">
                        <Clock className="w-3.5 h-3.5" />
                        <span>UNACKNOWLEDGED</span>
                      </span>
                    )}
                  </td>
                  <td className="p-3 text-right">
                    {!isAck && canAcknowledge && (
                      <button
                        onClick={() => onAcknowledge(alert.id)}
                        className="clinical-btn-secondary text-[11px] py-1 px-2.5"
                      >
                        Acknowledge
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
