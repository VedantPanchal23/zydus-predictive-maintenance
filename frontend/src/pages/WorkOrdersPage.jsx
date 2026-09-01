import React, { useState, useEffect } from "react";
import { getWorkOrders, completeWorkOrder } from "../services/api";
import { useAuth } from "../context/AuthContext";
import WorkOrderCard from "../components/incidents/WorkOrderCard";
import ESignatureModal from "../components/common/ESignatureModal";
import { ClipboardList, RefreshCw, CheckCircle2 } from "lucide-react";

export default function WorkOrdersPage() {
  const [workOrders, setWorkOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedWO, setSelectedWO] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { isEngineer } = useAuth();

  const loadWorkOrders = async (manual = false) => {
    if (manual) setIsRefreshing(true);
    try {
      const data = await getWorkOrders();
      const items = Array.isArray(data) ? data : (data?.items || []);
      setWorkOrders(items);
    } catch (err) {
      console.error("Failed to load work orders:", err);
      setWorkOrders([]);
    } finally {
      setLoading(false);
      if (manual) {
        setTimeout(() => setIsRefreshing(false), 500);
      }
    }
  };

  useEffect(() => {
    loadWorkOrders();
    const interval = setInterval(() => loadWorkOrders(false), 5000);
    return () => clearInterval(interval);
  }, []);

  const handleOpenSignModal = (wo) => {
    setSelectedWO(wo);
    setIsModalOpen(true);
  };

  const handleCompleteWorkOrder = async (eSignData) => {
    if (!selectedWO) return;
    await completeWorkOrder(selectedWO.id, eSignData);
    loadWorkOrders(true);
  };

  const safeWorkOrders = Array.isArray(workOrders) ? workOrders : [];
  const openCount = safeWorkOrders.filter((w) => w.status !== "completed" && !w.completed_at).length;
  const completedCount = safeWorkOrders.filter((w) => w.status === "completed" || !!w.completed_at).length;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-neutral-900 dark:text-white flex items-center gap-2 uppercase tracking-wider font-mono">
            <ClipboardList className="w-4 h-4 text-neutral-700 dark:text-neutral-300" />
            <span>GxP Maintenance Work Order Desk</span>
          </h2>
          <p className="text-xs text-neutral-500 mt-0.5">Automated SOP Prescriptions with 21 CFR Part 11 Electronic Dual Sign-off</p>
        </div>

        <button
          onClick={() => loadWorkOrders(true)}
          disabled={isRefreshing}
          className="app-btn-secondary text-xs py-1.5 px-3"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-neutral-900 dark:text-white" : "text-neutral-500"}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Summary Chips */}
      <div className="flex items-center gap-2.5 text-xs font-mono">
        <span className="px-3 py-1.5 rounded-md bg-white dark:bg-[#0d0d0d] border border-neutral-200 dark:border-neutral-800 text-neutral-700 dark:text-neutral-300">
          OPEN: <strong className="text-amber-700 dark:text-amber-400 font-bold">{openCount}</strong>
        </span>
        <span className="px-3 py-1.5 rounded-md bg-white dark:bg-[#0d0d0d] border border-neutral-200 dark:border-neutral-800 text-neutral-700 dark:text-neutral-300">
          COMPLETED: <strong className="text-emerald-700 dark:text-emerald-400 font-bold">{completedCount}</strong>
        </span>
      </div>

      {/* Work Orders Grid */}
      {safeWorkOrders.length === 0 ? (
        <div className="app-card p-12 text-center text-neutral-500">
          <CheckCircle2 className="w-8 h-8 mx-auto mb-3 text-emerald-600 dark:text-emerald-400" />
          <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200">Zero Open Work Orders</p>
          <p className="text-xs text-neutral-500 mt-1">All maintenance orders are closed and cryptographically signed.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {safeWorkOrders.map((wo) => (
            <WorkOrderCard
              key={wo.id}
              workOrder={wo}
              onOpenSignModal={handleOpenSignModal}
              canComplete={isEngineer}
            />
          ))}
        </div>
      )}

      {/* 21 CFR Part 11 Electronic Signature Modal */}
      <ESignatureModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={`Electronic Sign-off: Work Order #${selectedWO?.id}`}
        actionName="Sign & Close Work Order"
        onConfirm={handleCompleteWorkOrder}
      />
    </div>
  );
}
