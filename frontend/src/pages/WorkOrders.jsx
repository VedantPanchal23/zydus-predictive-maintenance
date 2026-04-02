import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { completeWorkOrder, getWorkOrders } from '../api/api';

const FILTERS = ['Open', 'In Progress', 'Completed', 'All'];

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

      const { data } = await getWorkOrders({ status });
      return data;
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
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Work orders</h1>
        <p className="mt-1 text-sm text-slate-600">Maintenance work created from high-risk predictions.</p>
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
          Total work orders: {data?.length || 0}
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Priority</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Equipment</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Description</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Predicted failure</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Status</th>
                <th className="px-4 py-3 text-right font-medium text-slate-600">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {isLoading ? (
                <tr>
                  <td colSpan="6" className="px-4 py-6 text-center text-slate-500">Loading work orders...</td>
                </tr>
              ) : data?.length ? (
                data.map((item) => (
                  <tr key={item.id}>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-1 text-xs font-medium ${
                        item.priority === 'CRITICAL'
                          ? 'bg-red-100 text-red-700'
                          : item.priority === 'HIGH'
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-slate-100 text-slate-700'
                      }`}>
                        {item.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-900">{item.equipment_name}</td>
                    <td className="px-4 py-3 text-slate-700">{item.description}</td>
                    <td className="px-4 py-3 text-slate-500">
                      {item.predicted_failure_date ? new Date(item.predicted_failure_date).toLocaleDateString() : 'Not available'}
                    </td>
                    <td className="px-4 py-3 text-slate-700">{item.status}</td>
                    <td className="px-4 py-3 text-right">
                      {item.status === 'open' ? (
                        <button
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
                ))
              ) : (
                <tr>
                  <td colSpan="6" className="px-4 py-6 text-center text-slate-500">No work orders are available for this filter.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
