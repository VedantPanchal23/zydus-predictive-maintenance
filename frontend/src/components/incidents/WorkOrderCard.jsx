import React from "react";
import { formatDateTime } from "../../utils/formatters";
import { Wrench, Shield, CheckCircle2, FileText, Lock } from "lucide-react";

export default function WorkOrderCard({ workOrder, onOpenSignModal, canComplete }) {
  const isCompleted = workOrder.status === "completed" || !!workOrder.completed_at;

  const priorityColors = {
    critical: "bg-rose-500/15 text-rose-300 border-rose-500/30",
    high: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    medium: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
    low: "bg-slate-500/15 text-slate-300 border-slate-500/30",
  };

  return (
    <div className="clinical-card p-4 flex flex-col justify-between border-surface-border">
      {/* Top Accent Strip */}
      <div className={`absolute top-0 left-0 right-0 h-[2px] ${isCompleted ? "bg-emerald-500" : "bg-gradient-to-r from-amber-500 to-rose-500"}`} />

      <div>
        {/* Header: Priority & WO ID */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold text-cyan-400">WO #{workOrder.id}</span>
            <span className={`text-[9px] font-mono font-bold uppercase px-2 py-0.2 rounded border ${priorityColors[workOrder.priority?.toLowerCase()] || priorityColors.medium}`}>
              {workOrder.priority || "MEDIUM"}
            </span>
          </div>
          <span className={`text-[10px] font-mono font-bold uppercase ${isCompleted ? "text-emerald-400" : "text-amber-400 animate-pulse"}`}>
            {isCompleted ? "COMPLETED" : "OPEN"}
          </span>
        </div>

        {/* Asset & Description */}
        <h4 className="mt-2 text-xs font-bold text-slate-100">
          {workOrder.equipment_name || `Asset #${workOrder.equipment_id}`}
        </h4>
        <p className="mt-1 text-[11px] text-slate-300 leading-relaxed">
          {workOrder.description}
        </p>

        {/* GxP SOP & Tooling Box */}
        <div className="mt-3 p-2.5 rounded-lg bg-surface-base border border-surface-border space-y-1.5 text-[11px]">
          <div className="flex items-center gap-1.5 font-mono text-cyan-400 font-bold text-[10px]">
            <FileText className="w-3.5 h-3.5 flex-shrink-0" />
            <span>SOP: {workOrder.sop_code || "SOP-MNT-STER-701"}</span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-400 text-[10px]">
            <Wrench className="w-3 h-3 text-slate-500 flex-shrink-0" />
            <span>Calibrated Torque Wrench & Laser Alignment</span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-400 text-[10px]">
            <Shield className="w-3 h-3 text-slate-500 flex-shrink-0" />
            <span>ISO Class 5 Tyvek Suit & Double Nitrile</span>
          </div>
        </div>
      </div>

      {/* Footer / e-Sign Action */}
      <div className="mt-4 pt-2.5 border-t border-surface-border flex items-center justify-between text-xs">
        <span className="text-slate-500 font-mono text-[10px]">
          {formatDateTime(workOrder.created_at)}
        </span>

        {isCompleted ? (
          <span className="inline-flex items-center gap-1 text-emerald-400 font-bold font-mono text-[10px]">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>21 CFR SIGNED</span>
          </span>
        ) : canComplete ? (
          <button
            onClick={() => onOpenSignModal(workOrder)}
            className="clinical-btn-primary py-1 px-2.5 text-[11px]"
          >
            <Lock className="w-3 h-3" />
            <span>e-Sign & Close</span>
          </button>
        ) : (
          <span className="text-slate-500 italic text-[10px]">Sign: Engineer/Admin</span>
        )}
      </div>
    </div>
  );
}
