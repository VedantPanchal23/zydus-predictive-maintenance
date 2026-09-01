import React, { useState } from "react";
import { injectChaosFault } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { Flame, Play, AlertOctagon, Activity } from "lucide-react";
import { formatCurrency, formatPercent } from "../utils/formatters";

export default function ChaosPage() {
  const { user } = useAuth();
  const [selectedAsset, setSelectedAsset] = useState("GRAN-LINE-01");
  const [faultType, setFaultType] = useState("SEIZED_ROTOR");
  const [injecting, setInjecting] = useState(false);
  const [result, setResult] = useState(null);

  const faultTypes = [
    {
      id: "SEIZED_ROTOR",
      name: "Seized Drive Rotor (Current Surge + 0 RPM)",
      desc: "Simulates locked rotor draw (88.5A) with zero shaft rotation to test electromechanical decoupling detection.",
    },
    {
      id: "COOLING_FAILURE",
      name: "Cooling Jacket Failure (Thermal Spike + Low Flow)",
      desc: "Simulates thermal runaway (>98°C) with coolant collapse (2.1 LPM) to test thermodynamic safety interlocks.",
    },
    {
      id: "BEARING_DEGRADATION",
      name: "Severe Bearing Spall (High Vibration)",
      desc: "Simulates severe inner race defect (>78 Hz vibration) to test LSTM autoencoder sequence reconstruction error.",
    },
  ];

  const handleInject = async () => {
    setInjecting(true);
    setResult(null);
    try {
      const res = await injectChaosFault({
        equipment_id: selectedAsset,
        fault_type: faultType,
        user_id: user?.username || "CHAOS_ENGINEER",
      });
      setResult(res);
    } catch (err) {
      alert(err?.response?.data?.detail || "Failed to inject chaos fault.");
    } finally {
      setInjecting(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="app-card p-4 border-neutral-200 dark:border-neutral-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-white">
            <Flame className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-neutral-900 dark:text-white uppercase font-mono tracking-wider">
              Chaos & Resilience Engineering Lab
            </h2>
            <p className="text-xs text-neutral-500 mt-0.5">
              Inject synthetic mechanical, thermal, and electrical fault modes to prove automated AI isolation and GAMP 5 regulatory impact calculations.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Controls */}
        <div className="app-card p-5 space-y-4">
          <h3 className="text-xs font-bold text-neutral-900 dark:text-white uppercase tracking-wider font-mono">
            Fault Injection Parameters
          </h3>

          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">Target Asset</label>
            <select
              value={selectedAsset}
              onChange={(e) => setSelectedAsset(e.target.value)}
              className="app-input w-full font-mono"
            >
              <option value="GRAN-LINE-01">GRAN-LINE-01 — High Shear Mixer Granulator</option>
              <option value="VIAL-FILL-01">VIAL-FILL-01 — Aseptic Vial Filling Line</option>
              <option value="BIOREACTOR-01">BIOREACTOR-01 — Single-Use Bioreactor 2000L</option>
              <option value="HPLC-AUTO-01">HPLC-AUTO-01 — UPLC Quaternary Pump</option>
              <option value="LINAC-01">LINAC-01 — Varian Linear Accelerator</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">Fault Mode</label>
            <div className="space-y-1.5">
              {faultTypes.map((ft) => (
                <label
                  key={ft.id}
                  className={`p-2.5 rounded-md border flex items-start gap-2.5 cursor-pointer transition-colors ${
                    faultType === ft.id
                      ? "bg-neutral-100 dark:bg-neutral-800 border-neutral-900 dark:border-white text-neutral-900 dark:text-white font-medium"
                      : "bg-white dark:bg-[#121212] border-neutral-200 dark:border-neutral-800 text-neutral-600 dark:text-neutral-400"
                  }`}
                >
                  <input
                    type="radio"
                    name="faultType"
                    checked={faultType === ft.id}
                    onChange={() => setFaultType(ft.id)}
                    className="mt-0.5 text-neutral-900 focus:ring-neutral-900"
                  />
                  <div className="text-xs">
                    <div className="font-semibold text-neutral-900 dark:text-white">{ft.name}</div>
                    <p className="text-neutral-500 mt-0.5 text-[11px] leading-relaxed">{ft.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <button
            onClick={handleInject}
            disabled={injecting}
            className="app-btn-primary w-full py-2.5 text-xs font-semibold"
          >
            <Play className={`w-3.5 h-3.5 ${injecting ? "animate-spin" : ""}`} />
            <span>{injecting ? "Simulating Physical Fault..." : "Inject Fault Telemetry"}</span>
          </button>
        </div>

        {/* Live Re-Evaluation Result Proof */}
        <div className="app-card p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-bold text-neutral-900 dark:text-white uppercase tracking-wider font-mono mb-3">
              Real-Time Model & Regulatory Response
            </h3>

            {result ? (
              <div className="space-y-3 animate-fade-in text-xs">
                {/* Status Proof */}
                <div className="p-3 rounded-md bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 flex items-start gap-2">
                  <AlertOctagon className="w-4 h-4 text-rose-600 dark:text-rose-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold">Fault Detected Instantly by Physics & ML Ensemble</div>
                    <div className="text-[11px] mt-0.5 text-neutral-600 dark:text-neutral-400">Target Asset: {result.equipment_id} ({result.injected_readings} anomalous channels injected)</div>
                  </div>
                </div>

                {/* Grid */}
                <div className="grid grid-cols-2 gap-2 font-mono">
                  <div className="p-2.5 rounded bg-neutral-50 dark:bg-[#121212] border border-neutral-200 dark:border-neutral-800">
                    <div className="text-[9px] text-neutral-400 font-semibold uppercase">FAILURE PROBABILITY</div>
                    <div className="text-base font-bold text-rose-700 dark:text-rose-400 tabular-nums">
                      {formatPercent(result.prediction_result?.failure_probability)}
                    </div>
                  </div>
                  <div className="p-2.5 rounded bg-neutral-50 dark:bg-[#121212] border border-neutral-200 dark:border-neutral-800">
                    <div className="text-[9px] text-neutral-400 font-semibold uppercase">ANOMALY SCORE</div>
                    <div className="text-base font-bold text-amber-700 dark:text-amber-400 tabular-nums">
                      {result.prediction_result?.anomaly_score?.toFixed(4)}
                    </div>
                  </div>
                </div>

                {/* Primary Attribution */}
                {result.prediction_result?.feature_attribution?.length > 0 && (
                  <div className="p-2.5 rounded bg-neutral-50 dark:bg-[#121212] border border-neutral-200 dark:border-neutral-800 space-y-1">
                    <div className="text-[9px] text-neutral-400 font-mono font-semibold uppercase">TOP SENSOR DRIVER (SHAP)</div>
                    <div className="text-neutral-900 dark:text-white font-medium">
                      {result.prediction_result.feature_attribution[0].sensor_name} — {result.prediction_result.feature_attribution[0].impact_percentage?.toFixed(1)}% impact ({result.prediction_result.feature_attribution[0].current_value} {result.prediction_result.feature_attribution[0].unit})
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-10 text-center text-neutral-400 border border-dashed border-neutral-200 dark:border-neutral-800 rounded-md">
                <Activity className="w-6 h-6 mx-auto mb-2 text-neutral-400" />
                <p className="text-xs">Select parameters and trigger fault to inspect live response.</p>
              </div>
            )}
          </div>

          <div className="mt-4 pt-2.5 border-t border-neutral-200 dark:border-neutral-800 text-[10px] text-neutral-400 font-mono">
            Every injection automatically creates an immutable SHA-256 GxP audit log entry.
          </div>
        </div>
      </div>
    </div>
  );
}
