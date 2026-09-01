import React, { useState, useEffect } from "react";
import { getAuditLogs, exportGxPCertificate } from "../services/api";
import AuditChainViewer from "../components/audit/AuditChainViewer";
import CertificateModal from "../components/audit/CertificateModal";
import { ShieldCheck, RefreshCw } from "lucide-react";

export default function AuditTrailPage() {
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [certModalOpen, setCertModalOpen] = useState(false);
  const [certificateData, setCertificateData] = useState(null);

  const loadAuditLogs = async (manual = false) => {
    if (manual) setIsRefreshing(true);
    try {
      const data = await getAuditLogs({ limit: 150 });
      const items = data?.items || (Array.isArray(data) ? data : []);
      setAuditLogs(items);
    } catch (err) {
      console.error("Failed to load audit logs:", err);
      setAuditLogs([]);
    } finally {
      setLoading(false);
      if (manual) {
        setTimeout(() => setIsRefreshing(false), 500);
      }
    }
  };

  useEffect(() => {
    loadAuditLogs();
  }, []);

  const handleOpenCertificate = async () => {
    try {
      const cert = await exportGxPCertificate();
      setCertificateData(cert);
    } catch {
      setCertificateData(null);
    }
    setCertModalOpen(true);
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-neutral-900 dark:text-white flex items-center gap-2 uppercase tracking-wider font-mono">
            <ShieldCheck className="w-4 h-4 text-neutral-700 dark:text-neutral-300" />
            <span>US FDA 21 CFR Part 11 Regulatory Center</span>
          </h2>
          <p className="text-xs text-neutral-500 mt-0.5">Cryptographically Chained Immutable Audit Trail & Digital Certificate Export</p>
        </div>

        <button
          onClick={() => loadAuditLogs(true)}
          disabled={isRefreshing}
          className="app-btn-secondary text-xs py-1.5 px-3"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-neutral-900 dark:text-white" : "text-neutral-500"}`} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {/* Main Audit Viewer */}
      <AuditChainViewer
        auditLogs={auditLogs}
        onOpenCertModal={handleOpenCertificate}
      />

      {/* Formal GxP Compliance Certificate Modal */}
      <CertificateModal
        isOpen={certModalOpen}
        onClose={() => setCertModalOpen(false)}
        certificate={certificateData}
      />
    </div>
  );
}
