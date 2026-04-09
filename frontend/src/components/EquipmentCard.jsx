import React from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ShieldCheck, Activity } from 'lucide-react';
import StatusBadge from './StatusBadge';
import { formatDate, formatPercent, humanizeKey } from '../utils/formatters';

const STATUS_CONFIG = {
  healthy: { icon: ShieldCheck, tone: 'success', label: 'Healthy' },
  warning: { icon: Activity, tone: 'warning', label: 'Warning' },
  critical: { icon: AlertTriangle, tone: 'critical', label: 'Critical' },
  unknown: { icon: Activity, tone: 'neutral', label: 'Unknown' },
};

export default function EquipmentCard({ eq }) {
  const status = STATUS_CONFIG[eq.current_health] || STATUS_CONFIG.unknown;
  const Icon = status.icon;
  const failureRisk = formatPercent(eq.failure_probability);
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
          <p className="mt-1 text-sm text-slate-600">{humanizeKey(eq.type)}</p>
          <p className="mt-1 text-sm text-slate-500">{eq.location}</p>
        </div>
        <Icon className="h-5 w-5 text-slate-500" />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <StatusBadge tone={status.tone}>{status.label}</StatusBadge>
        <StatusBadge tone="neutral">Status: {eq.status}</StatusBadge>
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
          <span className="font-medium">{formatDate(eq.last_maintenance_date)}</span>
        </div>
      </div>
    </Link>
  );
}
