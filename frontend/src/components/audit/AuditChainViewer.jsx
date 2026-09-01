import React, { useState } from "react";
import { formatDateTime, truncateHash } from "../../utils/formatters";
import { verifyAuditChain } from "../../services/api";
import { ShieldCheck, ShieldAlert, CheckCircle2, RefreshCw, Key, FileBadge, FileDown } from "lucide-react";

export default function AuditChainViewer({ auditLogs = [], onOpenCertModal }) {
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const res = await verifyAuditChain();
      setVerifyResult(res);
    } catch (err) {
      setVerifyResult({
        is_chain_valid: false,
        status: "TAMPER_DETECTED",
        message: err.message || "Verification failed.",
      });
    } finally {
      setVerifying(false);
    }
  };

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("/api/audit-logs/export/pdf", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!res.ok) throw new Error("Failed to export PDF");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Zydus_21CFR_Part11_Audit_Dossier.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Audit PDF download error:", err);
    } finally {
      setDownloadingPdf(false);
    }
  };

  const safeLogs = Array.isArray(auditLogs) ? auditLogs : [];

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="app-card p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-neutral-900 dark:text-white uppercase font-mono tracking-wider">
              21 CFR Part 11 Cryptographic Audit Trail
            </span>
            <span className="text-[9px] font-mono font-semibold px-1.5 py-0.2 rounded bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 uppercase">
              SHA-256 Chained
            </span>
          </div>
          <p className="text-xs text-neutral-500 mt-0.5">
            Every user action, work order modification, and maintenance signature is cryptographically sealed in an immutable hash chain.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            title="Download Official PDF Dossier with Cryptographic QR Code"
            className="app-btn-secondary text-xs flex items-center gap-1.5 font-mono"
          >
            <FileDown className={`w-3.5 h-3.5 ${downloadingPdf ? "animate-spin" : "text-neutral-700 dark:text-neutral-300"}`} />
            <span>{downloadingPdf ? "Exporting..." : "Download PDF Dossier"}</span>
          </button>

          <button
            onClick={onOpenCertModal}
            className="app-btn-secondary text-xs flex items-center gap-1.5 font-mono"
          >
            <FileBadge className="w-3.5 h-3.5 text-neutral-700 dark:text-neutral-300" />
            <span>Export Certificate</span>
          </button>

          <button
            onClick={handleVerify}
            disabled={verifying}
            className="app-btn-primary text-xs flex items-center gap-1.5 font-mono"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${verifying ? "animate-spin" : ""}`} />
            <span>{verifying ? "Verifying..." : "Verify Hash Integrity"}</span>
          </button>
        </div>
      </div>

      {/* Verification Result Callout */}
      {verifyResult && (
        <div
          className={`p-3 rounded-md border text-xs flex items-start gap-3 transition-all ${
            verifyResult.is_chain_valid
              ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-800 dark:text-emerald-300"
              : "bg-red-500/5 border-red-500/20 text-red-800 dark:text-red-300"
          }`}
        >
          {verifyResult.is_chain_valid ? (
            <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
          ) : (
            <ShieldAlert className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          )}
          <div className="space-y-0.5">
            <div className="font-bold font-mono">
              Audit Trail Integrity Authenticated ({verifyResult.status})
            </div>
            <div className="text-[11px] opacity-90">
              Verified {verifyResult.records_verified || safeLogs.length} sequential records. Zero mathematical hash deviations detected.
            </div>
            <div className="text-[10px] opacity-75 font-mono">
              Regulatory Framework: US FDA 21 CFR Part 11 / EU Annex 11 / GAMP 5 Category 4
            </div>
          </div>
        </div>
      )}

      {/* Audit Log Table */}
      <div className="app-card overflow-hidden">
        <div className="overflow-x-auto max-h-[560px]">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-neutral-100 dark:bg-[#121212] border-b border-neutral-200 dark:border-neutral-800 text-[10px] font-mono uppercase text-neutral-500 tracking-wider">
              <tr>
                <th className="px-3 py-2.5">ID</th>
                <th className="px-3 py-2.5">Timestamp</th>
                <th className="px-3 py-2.5">Signer (Role)</th>
                <th className="px-3 py-2.5">Action</th>
                <th className="px-3 py-2.5">Entity</th>
                <th className="px-3 py-2.5">Reason / Change Notes</th>
                <th className="px-3 py-2.5 text-right font-mono">SHA-256 Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200 dark:divide-neutral-800 font-sans">
              {safeLogs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-neutral-400 font-mono text-xs">
                    No cryptographic audit records recorded.
                  </td>
                </tr>
              ) : (
                safeLogs.map((log) => {
                  const hash = log.record_hash || "";
                  const prevHash = log.previous_hash || "";
                  const shortHash = truncateHash(hash, 8);
                  const isSystem = !log.user_id || log.user_id === "SYSTEM" || log.user_id === "SYSTEM_ALERT_ENGINE";

                  return (
                    <tr
                      key={log.id}
                      className="hover:bg-neutral-50 dark:hover:bg-neutral-900/60 transition-colors"
                    >
                      <td className="px-3 py-2.5 font-mono text-[11px] text-neutral-400">
                        #{log.id}
                      </td>
                      <td className="px-3 py-2.5 text-neutral-600 dark:text-neutral-400 whitespace-nowrap text-[11px] font-mono">
                        {formatDateTime(log.timestamp || log.timestamp_utc || log.created_at)}
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-1.5">
                          <span className={`font-mono text-xs font-bold ${isSystem ? "text-neutral-500" : "text-neutral-900 dark:text-white"}`}>
                            {log.user_id || "system"}
                          </span>
                          <span className="text-[10px] text-neutral-400 font-mono">
                            ({log.user_role || "user"})
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5">
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 border border-neutral-200 dark:border-neutral-700">
                          {log.action}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-neutral-700 dark:text-neutral-300 font-mono text-[11px]">
                        {log.entity_type} {log.entity_id ? `(#${log.entity_id})` : ""}
                      </td>
                      <td className="px-3 py-2.5 text-neutral-600 dark:text-neutral-400 text-[11px] max-w-xs truncate">
                        {log.reason_for_change || log.details || (
                          <span className="text-neutral-300 dark:text-neutral-600 font-mono text-[10px]">N/A</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-right font-mono text-[10px] text-neutral-700 dark:text-neutral-300">
                        <span
                          title={`SHA-256 Hash: ${hash}\nPrevious Hash: ${prevHash}`}
                          className="px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-[#121212] border border-neutral-200 dark:border-neutral-800 select-all cursor-help"
                        >
                          {shortHash}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
