/** Score gauge — circular progress ring with color thresholds. */

import React from "react";

interface Props {
  score: number | null;
}

const ScoreGauge: React.FC<Props> = ({ score }) => {
  if (score === null) {
    return <span className="text-lg text-gray-400">Score unavailable</span>;
  }
  const radius = 60;
  const stroke = 8;
  const normalized = Math.max(0, Math.min(100, score));
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (normalized / 100) * circumference;

  const color =
    normalized >= 70
      ? "text-green-500"
      : normalized >= 40
        ? "text-amber-500"
        : "text-red-500";

  const strokeColor =
    normalized >= 70
      ? "stroke-green-500"
      : normalized >= 40
        ? "stroke-amber-500"
        : "stroke-red-500";

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="140" height="140" className="-rotate-90">
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={stroke}
          className="text-gray-200"
        />
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={`${strokeColor} transition-all duration-700`}
        />
      </svg>
      <span className={`text-3xl font-bold ${color}`}>{score}</span>
      <span className="text-xs text-gray-400">out of 100</span>
    </div>
  );
};

export default ScoreGauge;
