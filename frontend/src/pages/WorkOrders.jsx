import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { completeWorkOrder, getWorkOrders } from '../api/api';
import DataTableCard from '../components/DataTableCard';
import FilterTabs from '../components/FilterTabs';
import PageHeader from '../components/PageHeader';
import StatusBadge from '../components/StatusBadge';
import { formatDate } from '../utils/formatters';

const FILTERS = ['Open', 'In Progress', 'Completed', 'All'];

const COLUMNS = [
  { key: 'priority', label: 'Priority' },
  { key: 'equipment', label: 'Equipment' },
  { key: 'description', label: 'Description' },
  { key: 'predictedFailure', label: 'Predicted failure' },
  { key: 'status', label: 'Status' },
  { key: 'action', label: 'Action', align: 'right' },
];

function priorityTone(priority) {
  if (priority === 'CRITICAL') return 'critical';
  if (priority === 'HIGH') return 'warning';
  return 'neutral';
}

export default function WorkOrders() {
  const [filter, setFilter] = React.useState('Open');
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['workOrders', filter],
    queryFn: async () => {
      let status = 'ALL';

      if (filter === 'Open') status = 'open';
      if (filter === 'In Progress') status = 'in_progress';
      if (filter === 'Completed') status = 'completed';

      const { data: response } = await getWorkOrders({ status });
      return response;
    },
    refetchInterval: 15000,
  });

  const completeMutation = useMutation({
    mutationFn: (id) => completeWorkOrder(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workOrders'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardSummary'] });
      queryClient.invalidateQueries({ queryKey: ['logs'] });
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Work orders"
        description="Maintenance work created from high-risk predictions."
        meta={<StatusBadge tone="neutral">{data?.length || 0} total</StatusBadge>}
      />

      <FilterTabs items={FILTERS} value={filter} onChange={setFilter} />

      <DataTableCard
        columns={COLUMNS}
        rows={data || []}
        isLoading={isLoading}
        loadingMessage="Loading work orders..."
        emptyMessage="No work orders are available for this filter."
        renderRow={(item) => (
          <tr key={item.id}>
            <td className="px-4 py-3">
              <StatusBadge tone={priorityTone(item.priority)}>{item.priority}</StatusBadge>
            </td>
            <td className="px-4 py-3 text-slate-900">{item.equipment_name}</td>
            <td className="px-4 py-3 text-slate-700">{item.description}</td>
            <td className="px-4 py-3 text-slate-500">{formatDate(item.predicted_failure_date)}</td>
            <td className="px-4 py-3 text-slate-700">{item.status}</td>
            <td className="px-4 py-3 text-right">
              {item.status === 'open' ? (
                <button
                  type="button"
                  onClick={() => completeMutation.mutate(item.id)}
                  disabled={completeMutation.isPending}
                  className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Mark complete
                </button>
              ) : (
                <span className="text-sm text-slate-500">No action</span>
              )}
            </td>
          </tr>
        )}
      />
    </div>
  );
}
