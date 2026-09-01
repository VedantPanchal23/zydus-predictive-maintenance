import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { ShieldCheck, X, KeyRound, FileSignature, AlertCircle } from "lucide-react";

export default function ESignatureModal({ isOpen, onClose, title, actionName, onConfirm }) {
  const { user } = useAuth();
  const [password, setPassword] = useState("");
  const [reason, setReason] = useState("Corrective Maintenance Completed");
  const [notes, setNotes] = useState("");
  const [certified, setCertified] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!password) {
      setError("Password verification is required per 21 CFR Part 11.");
      return;
    }
    if (!certified) {
      setError("You must acknowledge the legal electronic signature certification.");
      return;
    }

    setIsSubmitting(true);
    setError("");

    try {
      await onConfirm({
        password,
        reason,
        notes,
        signer: user?.username,
        role: user?.role,
        timestamp: new Date().toISOString(),
      });
      setPassword("");
      setNotes("");
      setCertified(false);
      onClose();
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || "Failed to execute electronic signature.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in">
      <div className="app-card w-full max-w-md p-6 bg-white dark:bg-[#0a0a0a] shadow-xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 p-1 rounded"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200">
            <FileSignature className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-neutral-900 dark:text-white">{title || "Electronic Signature Sign-off"}</h3>
            <p className="text-[11px] text-neutral-500">US FDA 21 CFR Part 11 Subpart C Regulatory Verification</p>
          </div>
        </div>

        {error && (
          <div className="mt-3 p-2 rounded bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          {/* User Signer Info */}
          <div className="grid grid-cols-2 gap-2 p-2.5 rounded bg-neutral-50 dark:bg-[#121212] border border-neutral-200 dark:border-neutral-800 text-xs font-mono">
            <div>
              <span className="text-neutral-400">SIGNER ID:</span>
              <span className="ml-1.5 font-bold text-neutral-900 dark:text-white">{user?.username}</span>
            </div>
            <div>
              <span className="text-neutral-400">ROLE:</span>
              <span className="ml-1.5 font-bold uppercase text-neutral-700 dark:text-neutral-300">{user?.role}</span>
            </div>
          </div>

          {/* Reason */}
          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Reason for GxP Action <span className="text-rose-600">*</span>
            </label>
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="app-input w-full"
            >
              <option value="Corrective Maintenance Completed">Corrective Maintenance Completed</option>
              <option value="Emergency Component Replacement">Emergency Component Replacement</option>
              <option value="Calibration & Metrology Sign-off">Calibration & Metrology Sign-off</option>
              <option value="Preventative Line Overhaul">Preventative Line Overhaul</option>
              <option value="Regulatory Audit Acknowledgment">Regulatory Audit Acknowledgment</option>
            </select>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Description & Verification Notes
            </label>
            <textarea
              rows="2"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Replaced mechanical seal on drive motor per SOP-MNT-STER-701..."
              className="app-input w-full resize-none"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Confirm Password <span className="text-rose-600">*</span>
            </label>
            <div className="relative">
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password to sign"
                className="app-input w-full pl-8"
              />
              <KeyRound className="w-3.5 h-3.5 text-neutral-400 absolute left-2.5 top-2.5" />
            </div>
          </div>

          {/* Checkbox */}
          <div className="pt-2 border-t border-neutral-200 dark:border-neutral-800">
            <label className="flex items-start gap-2 cursor-pointer text-xs text-neutral-600 dark:text-neutral-400 leading-snug select-none">
              <input
                type="checkbox"
                checked={certified}
                onChange={(e) => setCertified(e.target.checked)}
                className="mt-0.5 rounded border-neutral-300 text-neutral-900 dark:text-white focus:ring-neutral-900"
              />
              <span>
                I certify under penalty of perjury that this electronic signature is the legally binding equivalent of my handwritten signature per 21 CFR Part 11.
              </span>
            </label>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="app-btn-secondary text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="app-btn-primary text-xs"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>{isSubmitting ? "Signing..." : actionName || "Sign & Submit"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
