import React from 'react';
import StatusBadge from './StatusBadge';
import { formatDateTime, formatDecimal, formatPercent } from '../utils/formatters';

function getHealthStatus(failureProbability) {
  if (failureProbability > 0.8) return { label: 'Critical', tone: 'critical' };
  if (failureProbability > 0.4) return { label: 'Warning', tone: 'warning' };
  return { label: 'Healthy', tone: 'success' };
}

export default function PredictionPanel({ prediction, isLoading = false }) {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <h3 className="text-base font-semibold text-slate-900">Prediction</h3>
        <p className="mt-3 text-sm text-slate-600">Loading prediction...</p>
      </div>
    );
  }

  if (!prediction) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <h3 className="text-base font-semibold text-slate-900">Prediction</h3>
        <p className="mt-3 text-sm text-slate-600">No prediction is available for this equipment yet.</p>
      </div>
    );
  }

  const failureProbability = prediction.failure_probability || 0;
  const anomalyScore = prediction.anomaly_score || 0;
  const confidence = prediction.confidence || 0;
  const daysToFailure = prediction.days_to_failure || 0;
  const status = getHealthStatus(failureProbability);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-base font-semibold text-slate-900">Prediction</h3>
        <StatusBadge tone={status.tone}>{status.label}</StatusBadge>
      </div>

      <div className="mt-4 space-y-3 text-sm text-slate-700">
        <div className="flex justify-between gap-4">
          <span>Failure probability</span>
          <span className="font-medium">{formatPercent(failureProbability)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Anomaly score</span>
          <span className="font-medium">{formatDecimal(anomalyScore, 3)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Confidence</span>
          <span className="font-medium">{formatPercent(confidence, 0)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Estimated days to failure</span>
          <span className="font-medium">{formatDecimal(daysToFailure, 1)}</span>
        </div>
      </div>

      {prediction.predicted_at && (
        <p className="mt-4 text-xs text-slate-500">
          Updated at {formatDateTime(prediction.predicted_at)}
        </p>
      )}
    </div>
  );
}
