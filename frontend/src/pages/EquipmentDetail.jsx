import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import {
  getEquipmentById,
  getEquipmentHistory,
  getEquipmentPrediction,
  getEquipmentSensors,
} from '../api/api';
import DataTableCard from '../components/DataTableCard';
import PageHeader from '../components/PageHeader';
import PredictionPanel from '../components/PredictionPanel';
import SensorChart from '../components/SensorChart';
import StatusBadge from '../components/StatusBadge';
import {
  formatDate,
  formatDateTime,
  formatDecimal,
  formatPercent,
  humanizeKey,
} from '../utils/formatters';

const HISTORY_COLUMNS = [
  { key: 'time', label: 'Time' },
  { key: 'failureProbability', label: 'Failure probability' },
  { key: 'anomalyScore', label: 'Anomaly score' },
  { key: 'daysToFailure', label: 'Days to failure' },
  { key: 'confidence', label: 'Confidence' },
];

function healthTone(health) {
  if (health === 'healthy') return 'success';
  if (health === 'warning') return 'warning';
  if (health === 'critical') return 'critical';
  return 'neutral';
}

export default function EquipmentDetail() {
  const { id } = useParams();

  const { data: equipment, isLoading: equipmentLoading } = useQuery({
    queryKey: ['equipment', id],
    queryFn: async () => {
      const { data } = await getEquipmentById(id);
      return data;
    },
  });

  const { data: sensors, isLoading: sensorsLoading } = useQuery({
    queryKey: ['equipmentSensors', id],
    queryFn: async () => {
      const { data } = await getEquipmentSensors(id);
      return data;
    },
    refetchInterval: 30000,
  });

  const { data: prediction, isLoading: predictionLoading } = useQuery({
    queryKey: ['equipmentPrediction', id],
    queryFn: async () => {
      const { data } = await getEquipmentPrediction(id);
      return data;
    },
    refetchInterval: 10000,
  });

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['equipmentHistory', id],
    queryFn: async () => {
      const { data } = await getEquipmentHistory(id);
      return data;
    },
  });

  if (equipmentLoading || !equipment) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">
        Loading equipment data...
      </div>
    );
  }

  const sensorNames = Object.keys(sensors || {});

  return (
    <div className="space-y-6">
      <PageHeader
        title={equipment.name}
        description={`${humanizeKey(equipment.type)} - ${equipment.location}`}
        meta={
          <div className="flex items-center gap-3">
            <StatusBadge tone={healthTone(equipment.current_health)}>
              {humanizeKey(equipment.current_health, 'unknown')}
            </StatusBadge>
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 hover:text-slate-900"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Link>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold text-slate-900">Equipment details</h2>
          <div className="mt-4 grid grid-cols-1 gap-3 text-sm text-slate-700 md:grid-cols-2">
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-slate-500">Status</div>
              <div className="mt-1 font-medium text-slate-900">{equipment.status}</div>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-slate-500">Open alerts</div>
              <div className="mt-1 font-medium text-slate-900">{equipment.open_alerts_count}</div>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-slate-500">Install date</div>
              <div className="mt-1 font-medium text-slate-900">{formatDate(equipment.install_date)}</div>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-slate-500">Last maintenance</div>
              <div className="mt-1 font-medium text-slate-900">{formatDate(equipment.last_maintenance_date)}</div>
            </div>
          </div>
        </div>

        <PredictionPanel
          prediction={prediction || history?.[0] || null}
          isLoading={predictionLoading && !prediction && !history?.length}
        />
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-slate-900">Sensor data</h2>
        <p className="mt-1 text-sm text-slate-600">The last 24 hours of readings grouped by sensor.</p>

        {sensorsLoading ? (
          <p className="mt-4 text-sm text-slate-600">Loading sensor data...</p>
        ) : sensorNames.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">No sensor data is available for this equipment.</p>
        ) : (
          <div className="mt-6 space-y-6">
            {sensorNames.map((sensorName) => (
              <div key={sensorName} className="rounded-lg border border-slate-200 p-4">
                <div className="mb-4 flex items-center justify-between gap-4">
                  <h3 className="text-sm font-medium text-slate-900">{humanizeKey(sensorName)}</h3>
                  <span className="text-xs text-slate-500">{sensors[sensorName][0]?.unit || ''}</span>
                </div>
                <SensorChart data={sensors[sensorName]} />
              </div>
            ))}
          </div>
        )}
      </section>

      <DataTableCard
        title="Prediction history"
        columns={HISTORY_COLUMNS}
        rows={history || []}
        isLoading={historyLoading}
        loadingMessage="Loading prediction history..."
        emptyMessage="No prediction history is available."
        renderRow={(item, index) => (
          <tr key={`${item.predicted_at}-${index}`}>
            <td className="px-4 py-3 text-slate-700">{formatDateTime(item.predicted_at)}</td>
            <td className="px-4 py-3 text-slate-700">{formatPercent(item.failure_probability)}</td>
            <td className="px-4 py-3 text-slate-700">{formatDecimal(item.anomaly_score, 3)}</td>
            <td className="px-4 py-3 text-slate-700">{formatDecimal(item.days_to_failure, 1)}</td>
            <td className="px-4 py-3 text-slate-700">{formatPercent(item.confidence, 0)}</td>
          </tr>
        )}
      />
    </div>
  );
}
