import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getLogs } from '../api/api';

const FILTERS = [
  { label: 'All', value: 'ALL' },
  { label: 'Sensors', value: 'sensor' },
  { label: 'Predictions', value: 'prediction' },
  { label: 'Alerts', value: 'alert' },
  { label: 'Work orders', value: 'workorder' },
];

function levelClass(level) {
  if (level === 'CRITICAL') return 'bg-red-100 text-red-700';
  if (level === 'WARNING') return 'bg-amber-100 text-amber-700';
  if (level === 'INFO') return 'bg-slate-100 text-slate-700';
  return 'bg-blue-100 text-blue-700';
}

export default function Logs() {
  const [eventType, setEventType] = React.useState('ALL');

  const { data, isLoading } = useQuery({
    queryKey: ['logs', eventType],
    queryFn: async () => {
      const { data } = await getLogs({ event_type: eventType, limit: 100 });
      return data;
    },
    refetchInterval: 10000,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Logs</h1>
        <p className="mt-1 text-sm text-slate-600">Recent sensor, prediction, alert, and work order events.</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((filter) => (
          <button
            key={filter.value}
            onClick={() => setEventType(filter.value)}
            className={`rounded-md px-3 py-2 text-sm font-medium ${
              eventType === filter.value
                ? 'bg-slate-900 text-white'
                : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3 text-sm text-slate-600">
          Showing {data?.items?.length || 0} records
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Time</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Type</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Level</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Equipment</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Title</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Message</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {isLoading ? (
                <tr>
                  <td colSpan="6" className="px-4 py-6 text-center text-slate-500">Loading logs...</td>
                </tr>
              ) : data?.items?.length ? (
                data.items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-4 py-3 text-slate-500">{item.timestamp ? new Date(item.timestamp).toLocaleString() : 'Not available'}</td>
                    <td className="px-4 py-3 text-slate-700">{item.type}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-1 text-xs font-medium ${levelClass(item.level)}`}>
                        {item.level}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-900">{item.equipment_name}</td>
                    <td className="px-4 py-3 text-slate-700">{item.title}</td>
                    <td className="px-4 py-3 text-slate-700">{item.message}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="6" className="px-4 py-6 text-center text-slate-500">No logs are available.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
