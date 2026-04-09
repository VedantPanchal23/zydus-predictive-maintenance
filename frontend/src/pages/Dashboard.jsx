import React from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Activity, AlertTriangle, CheckCircle, Wrench } from 'lucide-react';
import { getAlerts, getDashboardSummary, getEquipment } from '../api/api';
import DataTableCard from '../components/DataTableCard';
import EquipmentCard from '../components/EquipmentCard';
import KpiCard from '../components/KpiCard';
import PageHeader from '../components/PageHeader';
import StatusBadge from '../components/StatusBadge';
import { formatDateTime, formatPercent } from '../utils/formatters';

const ALERT_COLUMNS = [
  { key: 'severity', label: 'Severity' },
  { key: 'equipment', label: 'Equipment' },
  { key: 'message', label: 'Message' },
  { key: 'time', label: 'Time' },
];

const SENSOR_COLUMNS = [
  { key: 'equipment', label: 'Equipment' },
  { key: 'sensor', label: 'Sensor' },
  { key: 'value', label: 'Value' },
  { key: 'time', label: 'Time' },
];

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

  const { data: equipmentData, isLoading: equipmentLoading } = useQuery({
    queryKey: ['equipmentList'],
    queryFn: async () => {
      const { data } = await getEquipment();
      return data;
    },
  });

  const { data: recentAlerts, isLoading: alertsLoading } = useQuery({
    queryKey: ['recentAlerts'],
    queryFn: async () => {
      const { data } = await getAlerts({ limit: 10, page: 1 });
      return data.items;
    },
    refetchInterval: 10000,
  });

  const mergedEquipment =
    equipmentData?.map((equipment) => {
      const liveData = ws.summary?.find((item) => item.equipment_id === equipment.name);
      return liveData ? { ...equipment, ...liveData } : equipment;
    }) || [];

  const liveSensorRows = ws.sensorData?.slice(0, 10) || [];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        description="Current equipment status and recent activity."
        meta={
          <StatusBadge tone={ws.connected ? 'success' : 'critical'}>
            {ws.connected ? 'Live feed connected' : 'Live feed disconnected'}
          </StatusBadge>
        }
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard title="Equipment" value={summary?.total_equipment ?? 0} icon={Activity} colorClass="bg-slate-900" />
        <KpiCard title="Critical" value={summary?.critical_count ?? 0} icon={AlertTriangle} colorClass="bg-red-500" />
        <KpiCard
          title="Health score"
          value={formatPercent(summary?.avg_health_score ?? 0, 0, '0%')}
          icon={CheckCircle}
          colorClass="bg-emerald-500"
        />
        <KpiCard title="Open work orders" value={summary?.open_workorders ?? 0} icon={Wrench} colorClass="bg-amber-500" />
      </div>

      <section>
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Equipment</h2>
            <p className="text-sm text-slate-600">Live data is merged with the saved equipment list.</p>
          </div>
          <StatusBadge tone="neutral">{mergedEquipment.length} items</StatusBadge>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {mergedEquipment.map((equipment) => (
            <EquipmentCard key={equipment.id} eq={equipment} />
          ))}
          {!equipmentLoading && mergedEquipment.length === 0 && (
            <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-500">
              No equipment data is available.
            </div>
          )}
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <DataTableCard
          title="Recent alerts"
          description="Latest alerts from the backend."
          action={
            <Link to="/alerts" className="text-sm font-medium text-slate-700 hover:text-slate-900">
              Open alerts
            </Link>
          }
          columns={ALERT_COLUMNS}
          rows={recentAlerts || []}
          isLoading={alertsLoading}
          loadingMessage="Loading alerts..."
          emptyMessage="No alerts are available."
          renderRow={(alert) => (
            <tr key={alert.id}>
              <td className="px-4 py-3">
                <StatusBadge tone={alert.severity === 'CRITICAL' ? 'critical' : 'warning'}>
                  {alert.severity}
                </StatusBadge>
              </td>
              <td className="px-4 py-3 text-slate-900">{alert.equipment_name}</td>
              <td className="px-4 py-3 text-slate-700">{alert.message}</td>
              <td className="px-4 py-3 text-slate-500">{formatDateTime(alert.created_at)}</td>
            </tr>
          )}
        />

        <DataTableCard
          title="Live sensor updates"
          description="Recent values from the WebSocket feed."
          action={
            <Link to="/logs" className="text-sm font-medium text-slate-700 hover:text-slate-900">
              Open logs
            </Link>
          }
          columns={SENSOR_COLUMNS}
          rows={liveSensorRows}
          emptyMessage="No live sensor data has arrived yet."
          renderRow={(row, index) => (
            <tr key={`${row.equipment_id}-${row.sensor_name}-${row.timestamp}-${index}`}>
              <td className="px-4 py-3 text-slate-900">{row.equipment_id}</td>
              <td className="px-4 py-3 text-slate-700">{row.sensor_name}</td>
              <td className="px-4 py-3 text-slate-700">
                {row.value} {row.unit}
              </td>
              <td className="px-4 py-3 text-slate-500">{formatDateTime(row.timestamp)}</td>
            </tr>
          )}
        />
      </section>
    </div>
  );
}
