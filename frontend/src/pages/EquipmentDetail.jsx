import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { getEquipmentById, getEquipmentSensors, getEquipmentPrediction, getEquipmentHistory } from '../api/api';
import SensorChart from '../components/SensorChart';
import PredictionPanel from '../components/PredictionPanel';

function HealthBadge({ health }) {
  const styles = {
    healthy: 'bg-emerald-100 text-emerald-700',
    warning: 'bg-amber-100 text-amber-700',
    critical: 'bg-red-100 text-red-700',
    unknown: 'bg-slate-100 text-slate-700',
  };

  return (
    <span className={`rounded-full px-2 py-1 text-xs font-medium ${styles[health] || styles.unknown}`}>
      {health || 'unknown'}
    </span>
  );
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

  const { data: prediction } = useQuery({
    queryKey: ['equipmentPrediction', id],
    queryFn: async () => {
      const { data } = await getEquipmentPrediction(id);
      return data;
    },
    refetchInterval: 10000,
  });

  const { data: history } = useQuery({
    queryKey: ['equipmentHistory', id],
    queryFn: async () => {
      const { data } = await getEquipmentHistory(id);
      return data;
    },
  });

  if (equipmentLoading || !equipment) {
    return <div className="text-sm text-slate-600">Loading equipment data...</div>;
  }

  const sensorNames = Object.keys(sensors || {});

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/dashboard" className="rounded-md border border-slate-200 bg-white p-2 text-slate-600 hover:bg-slate-50 hover:text-slate-900">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-slate-900">{equipment.name}</h1>
            <HealthBadge health={equipment.current_health} />
          </div>
          <p className="mt-1 text-sm text-slate-600">{equipment.type.replaceAll('_', ' ')} • {equipment.location}</p>
        </div>
      </div>

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
              <div className="mt-1 font-medium text-slate-900">
                {equipment.install_date ? new Date(equipment.install_date).toLocaleDateString() : 'Not available'}
              </div>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-slate-500">Last maintenance</div>
              <div className="mt-1 font-medium text-slate-900">
                {equipment.last_maintenance_date ? new Date(equipment.last_maintenance_date).toLocaleDateString() : 'Not available'}
              </div>
            </div>
          </div>
        </div>

        <PredictionPanel prediction={prediction || history?.[0] || null} />
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
                  <h3 className="text-sm font-medium text-slate-900">{sensorName.replaceAll('_', ' ')}</h3>
                  <span className="text-xs text-slate-500">{sensors[sensorName][0]?.unit || ''}</span>
                </div>
                <SensorChart data={sensors[sensorName]} name={sensorName} />
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-slate-900">Prediction history</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Time</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Failure probability</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Anomaly score</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Days to failure</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Confidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {(history || []).map((item, index) => (
                <tr key={`${item.predicted_at}-${index}`}>
                  <td className="px-4 py-3 text-slate-700">{item.predicted_at ? new Date(item.predicted_at).toLocaleString() : 'Not available'}</td>
                  <td className="px-4 py-3 text-slate-700">{(item.failure_probability * 100).toFixed(1)}%</td>
                  <td className="px-4 py-3 text-slate-700">{item.anomaly_score.toFixed(3)}</td>
                  <td className="px-4 py-3 text-slate-700">{item.days_to_failure.toFixed(1)}</td>
                  <td className="px-4 py-3 text-slate-700">{(item.confidence * 100).toFixed(0)}%</td>
                </tr>
              ))}
              {history?.length === 0 && (
                <tr>
                  <td colSpan="5" className="px-4 py-6 text-center text-slate-500">No prediction history is available.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
