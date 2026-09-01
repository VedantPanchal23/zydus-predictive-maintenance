import React, { useState, useEffect } from "react";
import { getEquipmentList, getDashboardSummary } from "../services/api";
import { useTelemetry } from "../context/TelemetryContext";
import KpiCard from "../components/common/KpiCard";
import FleetGrid from "../components/dashboard/FleetGrid";
import FacilityFilter, { FACILITIES } from "../components/dashboard/FacilityFilter";
import LiveTelemetryTicker from "../components/dashboard/LiveTelemetryTicker";
import { formatCurrency, formatPercent } from "../utils/formatters";
import {
  Activity,
  ShieldAlert,
  ClipboardList,
  IndianRupee,
  Search,
  RefreshCw,
  Cpu,
} from "lucide-react";

export default function DashboardPage() {
  const [equipmentList, setEquipmentList] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFacility, setActiveFacility] = useState("All Facilities");
  const { liveReadings } = useTelemetry();

  const loadData = async (manual = false) => {
    if (manual) setIsRefreshing(true);
    try {
      const [eqData, sumData] = await Promise.all([
        getEquipmentList(),
        getDashboardSummary(),
      ]);
      setEquipmentList(eqData || []);
      setSummary(sumData);
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    } finally {
      setLoading(false);
      if (manual) {
        setTimeout(() => setIsRefreshing(false), 500);
      }
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(() => loadData(false), 5000); // 5s synchronized with Kafka stream
    return () => clearInterval(interval);
  }, []);

  // Compute facility counts dynamically
  const facilityCounts = { "All Facilities": equipmentList.length };
  FACILITIES.forEach((fac) => {
    if (fac !== "All Facilities") {
      facilityCounts[fac] = equipmentList.filter((e) => e.facility === fac).length;
    }
  });

  const filteredEquipment = equipmentList.filter((eq) => {
    if (activeFacility === "All Facilities") return true;
    return eq.facility === activeFacility;
  });

  const totalLossExposure = equipmentList.reduce((acc, eq) => {
    const val = eq.batch_value_inr || 2500000;
    const prob = eq.failure_probability || 0.05;
    return acc + val * prob;
  }, 0);

  return (
    <div className="space-y-5">
      {/* Real-time Streaming Ticker */}
      <LiveTelemetryTicker />

      {/* Top Executive KPI Ribbon */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <KpiCard
          title="Fleet Average Health"
          value={formatPercent(summary?.avg_health_score || 0.85)}
          subtitle="20 Monitored Digital Twins"
          icon={Activity}
          trend="up"
          trendValue="+1.2%"
        />
        <KpiCard
          title="GAMP 5 Loss Exposure"
          value={formatCurrency(totalLossExposure)}
          subtitle="Batch Risk Weighted (INR)"
          icon={IndianRupee}
        />
        <KpiCard
          title="Active GxP Incidents"
          value={String(summary?.open_alerts || 0)}
          subtitle={`${summary?.critical_alerts || 0} Critical / ${summary?.warning_count || 0} Warning`}
          icon={ShieldAlert}
        />
        <KpiCard
          title="Open Maintenance WOs"
          value={String(summary?.open_workorders || 0)}
          subtitle="Pending 21 CFR e-Signature"
          icon={ClipboardList}
        />
      </div>

      {/* Facility Filter Tabs & Search Bar */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 pt-1">
        <FacilityFilter
          activeFacility={activeFacility}
          onSelect={setActiveFacility}
          counts={facilityCounts}
        />

        <div className="flex items-center gap-2 w-full md:w-auto">
          <div className="relative flex-1 md:w-60">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search tag, name, facility..."
              className="app-input w-full pl-8 py-1.5 text-xs"
            />
            <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-2.5 top-2.5" />
          </div>

          <button
            onClick={() => loadData(true)}
            disabled={isRefreshing}
            title="Refresh Fleet Data"
            className="app-btn-secondary p-2 flex items-center justify-center"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-neutral-900 dark:text-white" : "text-neutral-500"}`} />
          </button>
        </div>
      </div>

      {/* 20-Asset Matrix Grid */}
      {loading ? (
        <div className="app-card p-16 text-center text-neutral-500">
          <Cpu className="w-8 h-8 mx-auto mb-3 text-neutral-400 animate-spin" />
          <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200">Synchronizing 20 Digital Twin Pipelines...</p>
        </div>
      ) : (
        <FleetGrid
          equipmentList={filteredEquipment}
          liveReadings={liveReadings}
          searchQuery={searchQuery}
        />
      )}
    </div>
  );
}
