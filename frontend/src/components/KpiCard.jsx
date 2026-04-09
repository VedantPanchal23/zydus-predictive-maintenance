import React from 'react';

export default function KpiCard({ title, value, icon, trend, trendLabel, colorClass }) {
  const IconComponent = icon;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-3">
        <div className={`rounded-md p-3 ${colorClass}`}>
          <IconComponent className="h-5 w-5 text-white" />
        </div>
        <div>
          <h4 className="text-sm font-medium text-slate-600">
            {title}
          </h4>
          <p className="mt-1 text-2xl font-semibold text-slate-900">
            {value}
          </p>
        </div>
      </div>
      {trend && trendLabel && (
        <p className="mt-3 text-xs text-slate-500">
          {trend} {trendLabel}
        </p>
      )}
    </div>
  );
}
