import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getLogs } from '../api/api';
import DataTableCard from '../components/DataTableCard';
import FilterTabs from '../components/FilterTabs';
import PageHeader from '../components/PageHeader';
import StatusBadge from '../components/StatusBadge';
import { formatDateTime } from '../utils/formatters';

const FILTERS = [
  { label: 'All', value: 'ALL' },
  { label: 'Sensors', value: 'sensor' },
  { label: 'Predictions', value: 'prediction' },
  { label: 'Alerts', value: 'alert' },
  { label: 'Work orders', value: 'workorder' },
];

const COLUMNS = [
  { key: 'time', label: 'Time' },
  { key: 'type', label: 'Type' },
  { key: 'level', label: 'Level' },
  { key: 'equipment', label: 'Equipment' },
  { key: 'title', label: 'Title' },
  { key: 'message', label: 'Message' },
];

function levelTone(level) {
  if (level === 'CRITICAL') return 'critical';
  if (level === 'WARNING') return 'warning';
  if (level === 'INFO') return 'neutral';
  return 'info';
}

export default function Logs() {
  const [eventType, setEventType] = React.useState('ALL');

  const { data, isLoading } = useQuery({
    queryKey: ['logs', eventType],
    queryFn: async () => {
      const { data: response } = await getLogs({ event_type: eventType, limit: 100 });
      return response;
    },
    refetchInterval: 10000,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Logs"
        description="Recent sensor, prediction, alert, and work order events."
        meta={<StatusBadge tone="neutral">{data?.items?.length || 0} records</StatusBadge>}
      />

      <FilterTabs items={FILTERS} value={eventType} onChange={setEventType} />

      <DataTableCard
        columns={COLUMNS}
        rows={data?.items || []}
        isLoading={isLoading}
        loadingMessage="Loading logs..."
        emptyMessage="No logs are available."
        renderRow={(item) => (
          <tr key={item.id}>
            <td className="px-4 py-3 text-slate-500">{formatDateTime(item.timestamp)}</td>
            <td className="px-4 py-3 text-slate-700">{item.type}</td>
            <td className="px-4 py-3">
              <StatusBadge tone={levelTone(item.level)}>{item.level}</StatusBadge>
            </td>
            <td className="px-4 py-3 text-slate-900">{item.equipment_name}</td>
            <td className="px-4 py-3 text-slate-700">{item.title}</td>
            <td className="px-4 py-3 text-slate-700">{item.message}</td>
          </tr>
        )}
      />
    </div>
  );
}
