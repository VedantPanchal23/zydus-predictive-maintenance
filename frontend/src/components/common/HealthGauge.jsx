import React from "react";

export default function HealthGauge({ score = 1.0, size = 80, strokeWidth = 6, label = "Health" }) {
  const normalized = Math.max(0, Math.min(100, score > 1.0 ? score : score * 100.0));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (normalized / 100) * circumference;

  let strokeColor = "#15803d"; // emerald-700
  let textColor = "text-emerald-700 dark:text-emerald-400";

  if (normalized < 40) {
    strokeColor = "#b91c1c"; // red-700
    textColor = "text-rose-700 dark:text-rose-400";
  } else if (normalized < 70) {
    strokeColor = "#b45309"; // amber-700
    textColor = "text-amber-700 dark:text-amber-400";
  } else if (normalized < 85) {
    strokeColor = "#0369a1"; // sky-700
    textColor = "text-blue-700 dark:text-blue-400";
  }

  return (
    <div className="flex flex-col items-center justify-center relative select-none" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          className="text-neutral-200 dark:text-neutral-800"
          strokeWidth={strokeWidth}
          fill="transparent"
        />
        {/* Progress Arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="transparent"
          style={{
            transition: "stroke-dashoffset 0.6s ease, stroke 0.3s ease",
          }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className={`text-xs font-bold font-mono tracking-tight tabular-nums ${textColor}`}>
          {normalized.toFixed(1)}%
        </span>
        {size >= 68 && (
          <span className="text-[9px] text-neutral-500 font-medium uppercase mt-0.5">
            {label}
          </span>
        )}
      </div>
    </div>
  );
}
