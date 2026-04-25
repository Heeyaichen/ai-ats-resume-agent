/** Job description textarea with character count. */

import React from "react";
import { AlertCircle } from "lucide-react";

const MAX_CHARS = 50_000;

interface Props {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

const JobDescriptionPanel: React.FC<Props> = ({ value, onChange, disabled }) => {
  const overLimit = value.length > MAX_CHARS;

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-label">
        Job Description
      </label>

      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        rows={6}
        placeholder="Paste the job description here..."
        className="w-full rounded-lg border border-separator bg-white px-3.5 py-2.5 text-sm leading-relaxed text-label placeholder:text-tertiary focus:border-accent focus:ring-1 focus:ring-accent disabled:pointer-events-none disabled:opacity-40 resize-y"
      />

      <div className="flex justify-between text-xs">
        <span className={overLimit ? "text-[#ff3b30]" : "text-tertiary"}>
          {value.length.toLocaleString()} / {MAX_CHARS.toLocaleString()}
        </span>
        {overLimit && (
          <span className="flex items-center gap-1 text-[#ff3b30]">
            <AlertCircle className="h-3 w-3" />
            Exceeds limit
          </span>
        )}
      </div>
    </div>
  );
};

export default JobDescriptionPanel;
