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
      <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800">
        <Globe className="h-3.5 w-3.5" />
        {languageDetected}
        {wasTranslated && " (translated)"}
      </span>
    )}
    {piiRedacted && (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-800">
        <ShieldCheck className="h-3.5 w-3.5" />
        PII Redacted
      </span>
    )}
  </div>
);

export default PrivacyBadges;
