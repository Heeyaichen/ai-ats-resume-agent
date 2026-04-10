/** Score breakdown bars for keyword, experience, skills, and similarity. */

import React from "react";

interface Props {
  breakdown: {
    keyword_match: number;
    experience_alignment: number;
    skills_coverage: number;
  };
  semanticSimilarity: number;
}

const Bar: React.FC<{ label: string; value: number; max: number; color: string }> = ({
  label,
  value,
  max,
  color,
}) => {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-sm">
        <span>{label}</span>
        <span className="text-gray-500">
          {value}/{max}
        </span>
      </div>
      <div className="mt-1 h-2 w-full rounded-full bg-gray-200">
        <div
          className={`h-2 rounded-full ${color} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

const ScoreBreakdown: React.FC<Props> = ({ breakdown, semanticSimilarity }) => (
  <div className="space-y-3">
    <Bar label="Keyword Match" value={breakdown.keyword_match} max={40} color="bg-blue-500" />
    <Bar
      label="Experience Alignment"
      value={breakdown.experience_alignment}
      max={30}
      color="bg-purple-500"
    />
    <Bar label="Skills Coverage" value={breakdown.skills_coverage} max={30} color="bg-teal-500" />
    <Bar
      label="Semantic Similarity"
      value={Math.round(semanticSimilarity * 100)}
      max={100}
      color="bg-indigo-500"
    />
  </div>
);

export default ScoreBreakdown;
