/** Score breakdown bars for keyword, experience, skills, and similarity. */

import React from "react";

interface Props {
  breakdown: {
    keyword_match: number;
    experience_alignment: number;
    skills_coverage: number;
  } | null;
  semanticSimilarity: number | null;
}

const Bar: React.FC<{ label: string; value: number; max: number }> = ({
  label,
  value,
  max,
}) => {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-sm">
        <span className="text-label">{label}</span>
        <span className="text-secondary tabular-nums">
          {value}/{max}
        </span>
      </div>
      <div className="mt-1.5 h-1.5 w-full rounded-full bg-white/[0.06]">
        <div
          className="h-1.5 rounded-full bg-accent transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

const ScoreBreakdown: React.FC<Props> = ({ breakdown, semanticSimilarity }) => {
  if (!breakdown && semanticSimilarity === null) {
    return <span className="text-sm text-tertiary">Breakdown unavailable</span>;
  }
  return (
    <div className="space-y-4">
      {breakdown && (
        <>
          <Bar label="Keyword Match" value={breakdown.keyword_match} max={40} />
          <Bar
            label="Experience Alignment"
            value={breakdown.experience_alignment}
            max={30}
          />
          <Bar label="Skills Coverage" value={breakdown.skills_coverage} max={30} />
        </>
      )}
      {semanticSimilarity !== null && (
        <Bar
          label="Semantic Similarity"
          value={Math.round(semanticSimilarity * 100)}
          max={100}
        />
      )}
    </div>
  );
};

export default ScoreBreakdown;
