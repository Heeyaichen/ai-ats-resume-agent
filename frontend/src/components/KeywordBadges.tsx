/** Keyword badges — matched (green) and missing (red) chips. */

import React from "react";
import { CheckCircle, XCircle } from "lucide-react";

interface Props {
  matched: string[];
  missing: string[];
}

const KeywordBadges: React.FC<Props> = ({ matched, missing }) => (
  <div className="space-y-3">
    {matched.length > 0 && (
      <div>
        <p className="text-sm font-medium text-gray-600 mb-1">Matched Keywords</p>
        <div className="flex flex-wrap gap-1.5">
          {matched.map((kw) => (
            <span
              key={kw}
              className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800"
            >
              <CheckCircle className="h-3 w-3" />
              {kw}
            </span>
          ))}
        </div>
      </div>
    )}

    {missing.length > 0 && (
      <div>
        <p className="text-sm font-medium text-gray-600 mb-1">Missing Keywords</p>
        <div className="flex flex-wrap gap-1.5">
          {missing.map((kw) => (
            <span
              key={kw}
              className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800"
            >
              <XCircle className="h-3 w-3" />
              {kw}
            </span>
          ))}
        </div>
      </div>
    )}
  </div>
);

export default KeywordBadges;
