import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { useTelemetry } from "./context/TelemetryContext";
import Navbar from "./components/common/Navbar";
import Sidebar from "./components/common/Sidebar";

import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import EquipmentDetailPage from "./pages/EquipmentDetailPage";
import IncidentsPage from "./pages/IncidentsPage";
import WorkOrdersPage from "./pages/WorkOrdersPage";
import AuditTrailPage from "./pages/AuditTrailPage";
import DlqInspectorPage from "./pages/DlqInspectorPage";
import ChaosPage from "./pages/ChaosPage";

import { AlertOctagon, X } from "lucide-react";

function ProtectedLayout({ children }) {
  const { user, loading } = useAuth();
  const { toastAlert, clearToast } = useTelemetry();

  if (loading) {
    return (
      <div className="min-h-screen bg-white dark:bg-black flex items-center justify-center text-neutral-900 dark:text-white font-mono text-xs">
        Initializing Zydus Lifesciences GxP Session...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-white dark:bg-black text-neutral-900 dark:text-neutral-100 transition-colors">
      <Navbar />

      {/* Global Real-Time Alert Toast */}
      {toastAlert && (
        <div className="fixed bottom-5 right-5 z-50 p-4 rounded-lg bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900 shadow-xl text-xs max-w-sm border border-neutral-700 dark:border-neutral-300">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-1.5 font-bold">
              <AlertOctagon className="w-4 h-4 text-rose-500" />
              <span>GxP INCIDENT ALERT</span>
            </div>
            <button onClick={clearToast} className="text-neutral-400 hover:text-neutral-200 dark:hover:text-neutral-800">
              <X className="w-4 h-4" />
            </button>
          </div>
          <p className="mt-1 text-neutral-300 dark:text-neutral-700">{toastAlert.message || "Critical telemetry threshold breach detected."}</p>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-5 bg-neutral-50/50 dark:bg-black">
          <div className="max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}

function RoleGuard({ allowedRoles, children }) {
  const { role } = useAuth();
  if (!allowedRoles.includes(role)) {
    return <Navigate to="/" replace />;
  }
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/"
        element={
          <ProtectedLayout>
            <DashboardPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/equipment/:id"
        element={
          <ProtectedLayout>
            <EquipmentDetailPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/incidents"
        element={
          <ProtectedLayout>
            <IncidentsPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/workorders"
        element={
          <ProtectedLayout>
            <WorkOrdersPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/audit-trail"
        element={
          <ProtectedLayout>
            <RoleGuard allowedRoles={["admin", "auditor"]}>
              <AuditTrailPage />
            </RoleGuard>
          </ProtectedLayout>
        }
      />

      <Route
        path="/telemetry-dlq"
        element={
          <ProtectedLayout>
            <RoleGuard allowedRoles={["admin", "engineer", "auditor"]}>
              <DlqInspectorPage />
            </RoleGuard>
          </ProtectedLayout>
        }
      />

      <Route
        path="/chaos"
        element={
          <ProtectedLayout>
            <RoleGuard allowedRoles={["admin", "engineer"]}>
              <ChaosPage />
            </RoleGuard>
          </ProtectedLayout>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
