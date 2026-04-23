/** Human review banner — visible when review is required. */

import React from "react";
import { ShieldAlert } from "lucide-react";

interface Props {
  reason: string | null;
}

const HumanReviewBanner: React.FC<Props> = ({ reason }) => (
  <div className="flex items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4">
    <ShieldAlert className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
    <div>
      <p className="font-semibold text-amber-800">Flagged for Human Review</p>
      <p className="text-sm text-amber-700 mt-0.5">{reason}</p>
    </div>
  </div>
);

export default HumanReviewBanner;
