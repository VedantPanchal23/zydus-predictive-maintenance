import React from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ShieldCheck, Activity } from 'lucide-react';

const STATUS_CONFIG = {
  healthy: { icon: ShieldCheck, badge: 'bg-emerald-100 text-emerald-700', label: 'Healthy' },
  warning: { icon: Activity, badge: 'bg-amber-100 text-amber-700', label: 'Warning' },
  critical: { icon: AlertTriangle, badge: 'bg-red-100 text-red-700', label: 'Critical' },
  unknown: { icon: Activity, badge: 'bg-slate-100 text-slate-700', label: 'Unknown' },
};

export default function EquipmentCard({ eq }) {
  const status = STATUS_CONFIG[eq.current_health] || STATUS_CONFIG.unknown;
  const Icon = status.icon;
  const failureRisk = typeof eq.failure_probability === 'number'
    ? `${(eq.failure_probability * 100).toFixed(1)}%`
    : 'Not available';
  const daysToFailure = typeof eq.days_to_failure === 'number'
    ? `${eq.days_to_failure.toFixed(1)} days`
    : 'Not available';

  return (
    <Link
      to={`/equipment/${eq.id}`}
      className="block rounded-lg border border-slate-200 bg-white p-4 hover:border-slate-300 hover:shadow-sm"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-900">{eq.name}</h3>
          <p className="mt-1 text-sm text-slate-600">{eq.type.replaceAll('_', ' ')}</p>
          <p className="mt-1 text-sm text-slate-500">{eq.location}</p>
        </div>
        <Icon className="h-5 w-5 text-slate-500" />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <span className={`rounded-full px-2 py-1 text-xs font-medium ${status.badge}`}>
          {status.label}
        </span>
        <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">
          Status: {eq.status}
        </span>
      </div>

      <div className="mt-4 space-y-2 text-sm text-slate-700">
        <div className="flex justify-between gap-4">
          <span>Failure risk</span>
          <span className="font-medium">{failureRisk}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Days to failure</span>
          <span className="font-medium">{daysToFailure}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Last maintenance</span>
          <span className="font-medium">
            {eq.last_maintenance_date ? new Date(eq.last_maintenance_date).toLocaleDateString() : 'Not available'}
          </span>
        </div>
      </div>
    </Link>
  );
}
