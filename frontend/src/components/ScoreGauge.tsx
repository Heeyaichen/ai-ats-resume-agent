/** Score gauge — circular progress ring with color thresholds. */

import React from "react";

interface Props {
  score: number | null;
}

const ScoreGauge: React.FC<Props> = ({ score }) => {
  if (score === null) {
    return <span className="text-sm text-tertiary">Score unavailable</span>;
  }

  const radius = 54;
  const stroke = 6;
  const normalized = Math.max(0, Math.min(100, score));
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (normalized / 100) * circumference;

  const strokeColor =
    normalized >= 70
      ? "stroke-success"
      : normalized >= 40
        ? "stroke-warning"
        : "stroke-danger";

  const textColor =
    normalized >= 70
      ? "text-success"
      : normalized >= 40
        ? "text-warning"
        : "text-danger";

  return (
    <div className="flex flex-col items-center gap-0.5">
      <svg width="128" height="128" className="-rotate-90">
        <circle
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={stroke}
          className="text-separator"
        />
        <circle
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={`${strokeColor} transition-all duration-700`}
        />
      </svg>
      <span className={`text-4xl font-semibold tracking-tight ${textColor}`}>
        {score}
      </span>
      <span className="text-xs text-secondary">out of 100</span>
    </div>
  );
};

export default ScoreGauge;
