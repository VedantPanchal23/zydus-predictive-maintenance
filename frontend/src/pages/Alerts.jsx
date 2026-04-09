import React from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { acknowledgeAlert, getAlerts } from '../api/api';
import DataTableCard from '../components/DataTableCard';
import FilterTabs from '../components/FilterTabs';
import PageHeader from '../components/PageHeader';
import StatusBadge from '../components/StatusBadge';
import { formatDateTime } from '../utils/formatters';

const FILTERS = ['All', 'Critical', 'Warning', 'Acknowledged'];

const COLUMNS = [
  { key: 'severity', label: 'Severity' },
  { key: 'equipment', label: 'Equipment' },
  { key: 'message', label: 'Message' },
  { key: 'time', label: 'Time' },
  { key: 'action', label: 'Action', align: 'right' },
];

function alertTone(alert) {
  if (alert.acknowledged_at) {
    return 'neutral';
  }

  return alert.severity === 'CRITICAL' ? 'critical' : 'warning';
}

export default function Alerts() {
  const [filter, setFilter] = React.useState('All');
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['alerts', filter],
    queryFn: async () => {
      const params = { page: 1, limit: 100, status: 'ALL' };

      if (filter === 'Critical') params.severity = 'CRITICAL';
      if (filter === 'Warning') params.severity = 'WARNING';
      if (filter === 'Acknowledged') params.status = 'acknowledged';
      else if (filter !== 'All') params.status = 'open';

      const response = await getAlerts(params);
      return response.data;
    },
    refetchInterval: 10000,
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (id) => acknowledgeAlert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['recentAlerts'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardSummary'] });
      queryClient.invalidateQueries({ queryKey: ['logs'] });
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Alerts"
        description="Warnings and critical alerts created by the backend."
        meta={<StatusBadge tone="neutral">{data?.total || 0} total</StatusBadge>}
      />

      <FilterTabs items={FILTERS} value={filter} onChange={setFilter} />

      <DataTableCard
        columns={COLUMNS}
        rows={data?.items || []}
        isLoading={isLoading}
        loadingMessage="Loading alerts..."
        emptyMessage="No alerts are available for this filter."
        renderRow={(alert) => (
          <tr key={alert.id}>
            <td className="px-4 py-3">
              <StatusBadge tone={alertTone(alert)}>{alert.severity}</StatusBadge>
            </td>
            <td className="px-4 py-3 text-slate-900">
              {alert.equipment_id ? (
                <Link to={`/equipment/${alert.equipment_id}`} className="font-medium hover:underline">
                  {alert.equipment_name}
                </Link>
              ) : (
                alert.equipment_name
              )}
            </td>
            <td className="px-4 py-3 text-slate-700">{alert.message}</td>
            <td className="px-4 py-3 text-slate-500">{formatDateTime(alert.created_at)}</td>
            <td className="px-4 py-3 text-right">
              {!alert.acknowledged_at ? (
                <button
                  type="button"
                  onClick={() => acknowledgeMutation.mutate(alert.id)}
                  disabled={acknowledgeMutation.isPending}
                  className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Acknowledge
                </button>
              ) : (
                <span className="text-sm text-slate-500">Acknowledged</span>
              )}
            </td>
          </tr>
        )}
      />
    </div>
  );
}
