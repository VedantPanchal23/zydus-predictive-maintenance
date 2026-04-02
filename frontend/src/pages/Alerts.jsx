import React from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { acknowledgeAlert, getAlerts } from '../api/api';

const FILTERS = ['All', 'Critical', 'Warning', 'Acknowledged'];

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
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Alerts</h1>
        <p className="mt-1 text-sm text-slate-600">Warnings and critical alerts created by the backend.</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((item) => (
          <button
            key={item}
            onClick={() => setFilter(item)}
            className={`rounded-md px-3 py-2 text-sm font-medium ${
              filter === item
                ? 'bg-slate-900 text-white'
                : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            {item}
          </button>
        ))}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3 text-sm text-slate-600">
          Total alerts: {data?.total || 0}
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Severity</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Equipment</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Message</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Time</th>
                <th className="px-4 py-3 text-right font-medium text-slate-600">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {isLoading ? (
                <tr>
                  <td colSpan="5" className="px-4 py-6 text-center text-slate-500">Loading alerts...</td>
                </tr>
              ) : data?.items?.length ? (
                data.items.map((alert) => (
                  <tr key={alert.id}>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-1 text-xs font-medium ${
                        alert.acknowledged_at
                          ? 'bg-slate-100 text-slate-700'
                          : alert.severity === 'CRITICAL'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-amber-100 text-amber-700'
                      }`}>
                        {alert.severity}
                      </span>
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
                    <td className="px-4 py-3 text-slate-500">{new Date(alert.created_at).toLocaleString()}</td>
                    <td className="px-4 py-3 text-right">
                      {!alert.acknowledged_at ? (
                        <button
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
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="px-4 py-6 text-center text-slate-500">No alerts are available for this filter.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
