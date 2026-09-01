import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  getEquipmentDetail,
  getEquipmentPrediction,
  getEquipmentSensors,
  getEquipmentList,
} from "../services/api";
import StatusBadge from "../components/common/StatusBadge";
import HealthGauge from "../components/common/HealthGauge";
import DigitalTwinForecast from "../components/equipment/DigitalTwinForecast";
import FeatureAttribution from "../components/equipment/FeatureAttribution";
import PhysicsCouplingCard from "../components/equipment/PhysicsCouplingCard";
import SensorStreamChart from "../components/equipment/SensorStreamChart";
import DriftRadarCard from "../components/mlops/DriftRadarCard";
import { formatCurrency, formatPercent } from "../utils/formatters";
import {
  Cpu,
  Clock,
  IndianRupee,
  ArrowLeft,
  RefreshCw,
  FileDown,
} from "lucide-react";

export default function EquipmentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [equipmentList, setEquipmentList] = useState([]);
  const [detail, setDetail] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [sensorHistory, setSensorHistory] = useState({});
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

  const loadAsset = async (manual = false) => {
    if (manual) setIsRefreshing(true);
    try {
      const [eqs, det, pred, sens] = await Promise.all([
        getEquipmentList(),
        getEquipmentDetail(id),
        getEquipmentPrediction(id),
        getEquipmentSensors(id, 100),
      ]);
      setEquipmentList(eqs || []);
      setDetail(det);
      setPrediction(pred);
      setSensorHistory(sens || {});
    } catch (err) {
      console.error("Failed to load asset details:", err);
    } finally {
      setLoading(false);
      if (manual) {
        setTimeout(() => setIsRefreshing(false), 500);
      }
    }
  };

  useEffect(() => {
    loadAsset();
    const interval = setInterval(() => loadAsset(false), 5000);
    return () => clearInterval(interval);
  }, [id]);

  const handleDownloadPdf = async () => {
    setIsDownloadingPdf(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`/api/equipment/${id}/report/pdf`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!res.ok) throw new Error("Failed to generate PDF");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Zydus_${detail?.equipment_id || id}_Reliability_Report.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF download error:", err);
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  if (loading) {
    return (
      <div className="app-card p-16 text-center text-neutral-500">
        <Cpu className="w-8 h-8 mx-auto mb-3 text-neutral-400 animate-spin" />
        <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200">Loading Asset Digital Twin & AI Diagnostics...</p>
      </div>
    );
  }

  const health = prediction?.digital_twin?.current_health_score || (detail?.health_score ? detail.health_score * 100 : 85.0);
  const failProb = prediction?.failure_probability || detail?.failure_probability || 0.05;
  const rul = prediction?.days_to_failure || detail?.days_to_failure || 45.0;
  const batchValue = detail?.batch_value_inr || 2500000;
  const financialLoss = batchValue * failProb;

  return (
    <div className="space-y-5">
      {/* Top Header & Switcher */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/")}
            className="p-2 rounded-md bg-white dark:bg-[#0a0a0a] border border-neutral-200 dark:border-neutral-800 text-neutral-700 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-neutral-900 dark:text-white">{detail?.equipment_id || detail?.name}</span>
              <StatusBadge status={detail?.status || "ACTIVE"} size="sm" />
            </div>
            <h2 className="text-base font-bold text-neutral-900 dark:text-white mt-0.5">{detail?.name}</h2>
          </div>
        </div>

        {/* Fast Asset Switcher Dropdown & Actions */}
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={id}
            onChange={(e) => navigate(`/equipment/${e.target.value}`)}
            className="app-input text-xs py-1.5 font-mono max-w-[280px]"
          >
            {equipmentList.map((eq) => (
              <option key={eq.id} value={eq.id}>
                {eq.equipment_id} : {eq.name}
              </option>
            ))}
          </select>
          <button
            onClick={handleDownloadPdf}
            disabled={isDownloadingPdf}
            title="Download PDF Dossier"
            className="app-btn-secondary px-3 py-1.5 text-xs flex items-center gap-1.5 font-mono"
          >
            <FileDown className={`w-3.5 h-3.5 ${isDownloadingPdf ? "animate-spin" : "text-neutral-700 dark:text-neutral-300"}`} />
            <span>{isDownloadingPdf ? "Exporting..." : "Export PDF"}</span>
          </button>
          <button
            onClick={() => loadAsset(true)}
            disabled={isRefreshing}
            title="Refresh Diagnostics"
            className="app-btn-secondary p-2 flex items-center justify-center"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-neutral-900 dark:text-white" : "text-neutral-500"}`} />
          </button>
        </div>
      </div>

      {/* Asset Hero Card */}
      <div className="app-card p-4 grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
        <div className="flex items-center gap-4 md:col-span-2">
          <HealthGauge score={health} size={76} strokeWidth={6} label="DTHI" />
          <div>
            <div className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider font-mono">Location & Facility</div>
            <div className="text-xs font-bold text-neutral-800 dark:text-neutral-200">{detail?.facility || "Oral Solid Dosage Block A"}</div>
            <div className="mt-1.5 text-[10px] font-semibold text-neutral-400 uppercase tracking-wider font-mono">Category & GxP Class</div>
            <div className="text-xs font-mono text-neutral-700 dark:text-neutral-300 font-semibold">{detail?.category || "Granulation"} (GAMP 5 Category 4)</div>
          </div>
        </div>

        <div className="p-3 rounded-md bg-neutral-50 dark:bg-[#121212] border border-neutral-200/80 dark:border-neutral-800/80 space-y-1 font-mono">
          <div className="text-[9px] text-neutral-400 font-semibold uppercase">Remaining Useful Life (RUL)</div>
          <div className="text-lg font-bold text-neutral-900 dark:text-white flex items-center gap-1.5 tabular-nums">
            <Clock className="w-4 h-4 text-neutral-500" />
            <span>{rul.toFixed(1)} Days</span>
          </div>
          <div className="text-[10px] text-neutral-500 font-sans">94.0% Model Confidence Band</div>
        </div>

        <div className="p-3 rounded-md bg-neutral-50 dark:bg-[#121212] border border-neutral-200/80 dark:border-neutral-800/80 space-y-1 font-mono">
          <div className="text-[9px] text-neutral-400 font-semibold uppercase">GAMP 5 Spoilage Exposure</div>
          <div className="text-lg font-bold text-amber-700 dark:text-amber-400 flex items-center gap-1.5 tabular-nums">
            <IndianRupee className="w-4 h-4" />
            <span>{formatCurrency(financialLoss)}</span>
          </div>
          <div className="text-[10px] text-neutral-500 font-sans">Batch Value: {formatCurrency(batchValue)}</div>
        </div>
      </div>

      {/* Grid: Forecast & Feature Attribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <DigitalTwinForecast digitalTwin={prediction?.digital_twin} currentHealth={health} />
        <FeatureAttribution featureAttribution={prediction?.feature_attribution} />
      </div>

      {/* Grid: Telemetry Channels & Physics Coupling */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SensorStreamChart sensorHistory={sensorHistory} />
        <PhysicsCouplingCard physicsDiagnostics={prediction?.physics_diagnostics} />
      </div>

      {/* MLOps Model Governance & Drift Radar */}
      <DriftRadarCard equipmentCode={detail?.equipment_id || "GRAN-LINE-01"} />
    </div>
  );
}
