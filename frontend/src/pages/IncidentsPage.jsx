import React, { useState, useEffect } from "react";
import { getAlerts, acknowledgeAlert } from "../services/api";
import { useAuth } from "../context/AuthContext";
import AlertsTable from "../components/incidents/AlertsTable";
import KpiCard from "../components/common/KpiCard";
import { AlertOctagon, ShieldAlert, CheckCircle2, RefreshCw } from "lucide-react";

export default function IncidentsPage() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const { isEngineer } = useAuth();

  const loadAlerts = async (manual = false) => {
    if (manual) setIsRefreshing(true);
    try {
      const data = await getAlerts();
      const items = data?.items || (Array.isArray(data) ? data : []);
      setAlerts(items);
    } catch (err) {
      console.error("Failed to load alerts:", err);
      setAlerts([]);
    } finally {
      setLoading(false);
      if (manual) {
        setTimeout(() => setIsRefreshing(false), 500);
      }
    }
  };

  useEffect(() => {
    loadAlerts();
    const interval = setInterval(() => loadAlerts(false), 5000);
    return () => clearInterval(interval);
  }, []);

  const handleAcknowledge = async (alertId) => {
    try {
      await acknowledgeAlert(alertId);
      loadAlerts();
    } catch (err) {
      alert(err?.response?.data?.detail || "Failed to acknowledge alert.");
    }
  };

  const safeAlerts = Array.isArray(alerts) ? alerts : [];
  const activeCount = safeAlerts.filter((a) => !a.acknowledged_at).length;
  const criticalCount = safeAlerts.filter((a) => a.severity === "CRITICAL" && !a.acknowledged_at).length;
  const warningCount = safeAlerts.filter((a) => a.severity === "WARNING" && !a.acknowledged_at).length;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-neutral-900 dark:text-white flex items-center gap-2 uppercase tracking-wider font-mono">
            <AlertOctagon className="w-4 h-4 text-rose-600 dark:text-rose-400" />
            <span>GxP Incident Management Desk</span>
          </h2>
          <p className="text-xs text-neutral-500 mt-0.5">Anti-Flapping Hysteresis State Machine & Cooldown Deduplication</p>
        </div>

        <button
          onClick={() => loadAlerts(true)}
          disabled={isRefreshing}
          className="app-btn-secondary text-xs py-1.5 px-3"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-neutral-900 dark:text-white" : "text-neutral-500"}`} />
          <span>Refresh Incidents</span>
        </button>
      </div>

      {/* KPI Counters */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
        <KpiCard
          title="Active Unacknowledged"
          value={String(activeCount)}
          subtitle="Pending Engineering Action"
          icon={AlertOctagon}
          color={activeCount > 0 ? "rose" : "emerald"}
        />
        <KpiCard
          title="Critical Severity"
          value={String(criticalCount)}
          subtitle="Immediate Intervention Needed"
          icon={ShieldAlert}
          color="rose"
        />
        <KpiCard
          title="Warning Severity"
          value={String(warningCount)}
          subtitle="Pre-Emptive Maintenance Needed"
          icon={CheckCircle2}
          color="amber"
        />
      </div>

      {/* Alerts Table */}
      <AlertsTable
        alerts={safeAlerts}
        onAcknowledge={handleAcknowledge}
        canAcknowledge={isEngineer}
      />
    </div>
  );
}
