import React from 'react';
import { AlertCircle, X } from 'lucide-react';

export default function AlertBanner({ latestAlert, onClose }) {
  if (!latestAlert) return null;

  const isCritical = latestAlert.severity === 'CRITICAL';

  return (
    <div className={`fixed top-16 left-0 right-0 z-40 border-b ${isCritical ? 'border-red-200 bg-red-50' : 'border-amber-200 bg-amber-50'}`}>
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center">
          <span className={`rounded-md p-2 ${isCritical ? 'bg-red-100 text-red-600' : 'bg-amber-100 text-amber-600'}`}>
            <AlertCircle className="h-5 w-5" />
          </span>
          <p className="ml-3 truncate text-sm text-slate-900">
            {latestAlert.severity} alert for {latestAlert.equipment_id || 'equipment'}: {latestAlert.message}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="shrink-0 rounded-md p-2 text-slate-500 hover:bg-white hover:text-slate-900"
        >
          <span className="sr-only">Dismiss</span>
          <X className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}
