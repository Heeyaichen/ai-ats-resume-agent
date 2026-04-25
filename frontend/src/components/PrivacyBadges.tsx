/** Privacy badges — language detected/translated and PII redacted indicators. */

import React from "react";
import { Globe, ShieldCheck } from "lucide-react";

interface Props {
  languageDetected?: string;
  wasTranslated?: boolean;
  piiRedacted?: boolean;
}

const PrivacyBadges: React.FC<Props> = ({
  languageDetected,
  wasTranslated,
  piiRedacted,
}) => (
  <div className="flex flex-wrap gap-2">
    {languageDetected && (
      <span className="inline-flex items-center gap-1.5 rounded-lg bg-accent-muted px-3 py-1 text-xs font-medium text-label">
        <Globe className="h-3.5 w-3.5 text-accent" />
        {languageDetected}
        {wasTranslated && " (translated)"}
      </span>
    )}
    {piiRedacted && (
      <span className="inline-flex items-center gap-1.5 rounded-lg bg-success/[0.06] px-3 py-1 text-xs font-medium text-label">
        <ShieldCheck className="h-3.5 w-3.5 text-success" />
        PII Redacted
      </span>
    )}
  </div>
);

export default PrivacyBadges;
