import React from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Activity, AlertTriangle, CheckCircle, Wrench } from 'lucide-react';
import { getDashboardSummary, getAlerts, getEquipment } from '../api/api';
import KpiCard from '../components/KpiCard';
import EquipmentCard from '../components/EquipmentCard';

export default function Dashboard() {
  const { ws } = useOutletContext();

  const { data: summary } = useQuery({
    queryKey: ['dashboardSummary'],
    queryFn: async () => {
      const { data } = await getDashboardSummary();
      return data;
    },
    refetchInterval: 10000,
  });

  const { data: equipmentData } = useQuery({
    queryKey: ['equipmentList'],
    queryFn: async () => {
      const { data } = await getEquipment();
      return data;
    },
  });

  const { data: recentAlerts } = useQuery({
    queryKey: ['recentAlerts'],
    queryFn: async () => {
      const { data } = await getAlerts({ limit: 10, page: 1 });
      return data.items;
    },
    refetchInterval: 10000,
  });

  const mergedEquipment = equipmentData?.map((eq) => {
    const liveData = ws.summary?.find((item) => item.equipment_id === eq.name);
    return liveData ? { ...eq, ...liveData } : eq;
  }) || [];

  const liveSensorRows = ws.sensorData?.slice(0, 10) || [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-600">Current equipment status and recent activity.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard title="Equipment" value={summary?.total_equipment ?? 0} icon={Activity} colorClass="bg-slate-900" />
        <KpiCard title="Critical" value={summary?.critical_count ?? 0} icon={AlertTriangle} colorClass="bg-red-500" />
        <KpiCard title="Health score" value={summary?.avg_health_score ? `${(summary.avg_health_score * 100).toFixed(0)}%` : '0%'} icon={CheckCircle} colorClass="bg-emerald-500" />
        <KpiCard title="Open work orders" value={summary?.open_workorders ?? 0} icon={Wrench} colorClass="bg-amber-500" />
      </div>

      <section>
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Equipment</h2>
            <p className="text-sm text-slate-600">Live data is merged with the saved equipment list.</p>
          </div>
          <span className="rounded-md bg-slate-100 px-3 py-1 text-sm text-slate-700">
            {mergedEquipment.length} items
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {mergedEquipment.map((eq) => (
            <EquipmentCard key={eq.id} eq={eq} />
          ))}
          {mergedEquipment.length === 0 && (
            <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-500">
              No equipment data is available.
            </div>
          )}
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Recent alerts</h2>
              <p className="text-sm text-slate-600">Latest alerts from the backend.</p>
            </div>
            <Link to="/alerts" className="text-sm font-medium text-slate-700 hover:text-slate-900">
              Open alerts
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Severity</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Equipment</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Message</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {(recentAlerts || []).map((alert) => (
                  <tr key={alert.id}>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-1 text-xs font-medium ${alert.severity === 'CRITICAL' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                        {alert.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-900">{alert.equipment_name}</td>
                    <td className="px-4 py-3 text-slate-700">{alert.message}</td>
                    <td className="px-4 py-3 text-slate-500">{new Date(alert.created_at).toLocaleString()}</td>
                  </tr>
                ))}
                {recentAlerts?.length === 0 && (
                  <tr>
                    <td colSpan="4" className="px-4 py-6 text-center text-slate-500">No alerts available.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Live sensor updates</h2>
              <p className="text-sm text-slate-600">Recent values from the WebSocket feed.</p>
            </div>
            <Link to="/logs" className="text-sm font-medium text-slate-700 hover:text-slate-900">
              Open logs
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Equipment</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Sensor</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Value</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {liveSensorRows.map((row, index) => (
                  <tr key={`${row.equipment_id}-${row.sensor_name}-${row.timestamp}-${index}`}>
                    <td className="px-4 py-3 text-slate-900">{row.equipment_id}</td>
                    <td className="px-4 py-3 text-slate-700">{row.sensor_name}</td>
                    <td className="px-4 py-3 text-slate-700">{row.value} {row.unit}</td>
                    <td className="px-4 py-3 text-slate-500">{new Date(row.timestamp).toLocaleString()}</td>
                  </tr>
                ))}
                {liveSensorRows.length === 0 && (
                  <tr>
                    <td colSpan="4" className="px-4 py-6 text-center text-slate-500">No live sensor data has arrived yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
