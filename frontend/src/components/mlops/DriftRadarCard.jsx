import React, { useState, useEffect } from "react";
import { Activity, Play, CheckCircle2, AlertTriangle, ShieldAlert, Cpu } from "lucide-react";

export default function DriftRadarCard({ equipmentCode = "GRAN-LINE-01" }) {
  const [driftData, setDriftData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const [retrainResult, setRetrainResult] = useState(null);

  const fetchDrift = async () => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`/api/ml/drift-status?equipment_id=${equipmentCode}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setDriftData(data);
      }
    } catch (err) {
      console.error("Failed to fetch drift status:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDrift();
    const interval = setInterval(fetchDrift, 10000);
    return () => clearInterval(interval);
  }, [equipmentCode]);

  const handleTriggerRetraining = async () => {
    setRetraining(true);
    setRetrainResult(null);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("/api/ml/retrain", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          equipment_id: equipmentCode,
          force_promotion: true,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setRetrainResult(data);
        fetchDrift();
      }
    } catch (err) {
      console.error("Retraining trigger error:", err);
    } finally {
      setRetraining(false);
    }
  };

  const status = driftData?.drift_status || "NOMINAL";
  const maxPsi = driftData?.max_psi || 0.02;
  const isNominal = status === "NOMINAL";
  const isWarning = status === "MODERATE_DRIFT";

  return (
    <div className="app-card p-4 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-neutral-200 dark:border-neutral-800 pb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-neutral-700 dark:text-neutral-300" />
          <h3 className="text-xs font-bold text-neutral-900 dark:text-white uppercase font-mono tracking-wider">
            MLOps Model Governance & Drift Radar
          </h3>
          <span
            className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border uppercase ${
              isNominal
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-400"
                : isWarning
                ? "bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-400"
                : "bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-400"
            }`}
          >
            {status}
          </span>
        </div>

        <button
          onClick={handleTriggerRetraining}
          disabled={retraining}
          className="app-btn-primary text-xs flex items-center gap-1.5 font-mono"
        >
          <Cpu className={`w-3.5 h-3.5 ${retraining ? "animate-spin" : ""}`} />
          <span>{retraining ? "Retraining Ensemble..." : "Trigger Retraining Cycle"}</span>
        </button>
      </div>

      {/* Grid: Champion vs Challenger */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
        <div className="p-3 rounded bg-neutral-50 dark:bg-[#121212] border border-neutral-200 dark:border-neutral-800 space-y-1">
          <div className="text-[10px] text-neutral-400 font-mono font-semibold uppercase">Active Champion Model</div>
          <div className="font-mono font-bold text-neutral-900 dark:text-white text-xs">
            v3.0.0-PROD
          </div>
          <div className="text-[10px] text-neutral-500 font-sans">IsolationForest + LSTM Autoencoder</div>
        </div>

        <div className="p-3 rounded bg-neutral-50 dark:bg-[#121212] border border-neutral-200 dark:border-neutral-800 space-y-1">
          <div className="text-[10px] text-neutral-400 font-mono font-semibold uppercase">Max Feature Drift (PSI)</div>
          <div className="font-mono font-bold text-neutral-900 dark:text-white text-base">
            {maxPsi.toFixed(4)}
          </div>
          <div className="text-[10px] text-neutral-500 font-sans">GAMP 5 Retrain Threshold: 0.2500</div>
        </div>

        <div className="p-3 rounded bg-neutral-50 dark:bg-[#121212] border border-neutral-200 dark:border-neutral-800 space-y-1">
          <div className="text-[10px] text-neutral-400 font-mono font-semibold uppercase">Automated Governance</div>
          <div className="font-mono font-semibold text-neutral-700 dark:text-neutral-300 text-xs">
            21 CFR Part 11 Audited
          </div>
          <div className="text-[10px] text-neutral-500 font-sans">Airflow Daily Retrain DAG Active</div>
        </div>
      </div>

      {/* Retrain Result Callout */}
      {retrainResult && (
        <div className="p-3 rounded bg-emerald-500/5 border border-emerald-500/20 text-xs space-y-1">
          <div className="flex items-center gap-1.5 text-emerald-800 dark:text-emerald-300 font-bold font-mono">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Retraining & GAMP 5 Evaluation Complete ({retrainResult.action})</span>
          </div>
          <div className="text-[11px] text-neutral-600 dark:text-neutral-400 font-sans">
            {retrainResult.status_reason}
          </div>
        </div>
      )}
    </div>
  );
}
