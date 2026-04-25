/** Human review banner — visible when review is required. */

import React from "react";
import { ShieldAlert } from "lucide-react";

interface Props {
  reason: string | null;
}

const HumanReviewBanner: React.FC<Props> = ({ reason }) => (
  <div className="flex items-start gap-3 rounded-lg border border-[#ff9500]/20 bg-[#ff9500]/[0.06] px-4 py-3.5">
    <ShieldAlert className="mt-0.5 h-4 w-4 flex-shrink-0 text-[#ff9500]" />
    <div>
      <p className="text-sm font-semibold text-label">Flagged for Human Review</p>
      <p className="text-sm text-secondary mt-0.5">{reason}</p>
    </div>
  </div>
);

export default HumanReviewBanner;
