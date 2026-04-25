/** Keyword badges — matched and missing chips. */

import React from "react";
import { Check, X } from "lucide-react";

interface Props {
  matched: string[];
  missing: string[];
}

const KeywordBadges: React.FC<Props> = ({ matched, missing }) => (
  <div className="space-y-4">
    {matched.length > 0 && (
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-secondary mb-2">
          Matched Keywords
        </p>
        <div className="flex flex-wrap gap-1.5">
          {matched.map((kw) => (
            <span
              key={kw}
              className="inline-flex items-center gap-1 rounded-lg bg-[#34c759]/[0.08] px-2.5 py-1 text-xs font-medium text-label"
            >
              <Check className="h-3 w-3 text-[#34c759]" />
              {kw}
            </span>
          ))}
        </div>
      </div>
    )}

    {missing.length > 0 && (
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-secondary mb-2">
          Missing Keywords
        </p>
        <div className="flex flex-wrap gap-1.5">
          {missing.map((kw) => (
            <span
              key={kw}
              className="inline-flex items-center gap-1 rounded-lg bg-[#ff3b30]/[0.06] px-2.5 py-1 text-xs font-medium text-label"
            >
              <X className="h-3 w-3 text-[#ff3b30]" />
              {kw}
            </span>
          ))}
        </div>
      </div>
    )}
  </div>
);

export default KeywordBadges;
