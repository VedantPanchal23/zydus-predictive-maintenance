import React from 'react';

function getHealthStatus(failureProbability) {
  if (failureProbability > 0.8) return { label: 'Critical', badge: 'bg-red-100 text-red-700' };
  if (failureProbability > 0.4) return { label: 'Warning', badge: 'bg-amber-100 text-amber-700' };
  return { label: 'Healthy', badge: 'bg-emerald-100 text-emerald-700' };
}

export default function PredictionPanel({ prediction }) {
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
        <span className={`rounded-full px-2 py-1 text-xs font-medium ${status.badge}`}>
          {status.label}
        </span>
      </div>

      <div className="mt-4 space-y-3 text-sm text-slate-700">
        <div className="flex justify-between gap-4">
          <span>Failure probability</span>
          <span className="font-medium">{(failureProbability * 100).toFixed(1)}%</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Anomaly score</span>
          <span className="font-medium">{anomalyScore.toFixed(3)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Confidence</span>
          <span className="font-medium">{(confidence * 100).toFixed(0)}%</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Estimated days to failure</span>
          <span className="font-medium">{daysToFailure.toFixed(1)}</span>
        </div>
      </div>

      {prediction.predicted_at && (
        <p className="mt-4 text-xs text-slate-500">
          Updated at {new Date(prediction.predicted_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}
