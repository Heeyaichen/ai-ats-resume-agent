/** Agent trace panel — live tool call/result cards from SSE. */

import React from "react";
import { Wrench, CheckCircle, AlertTriangle } from "lucide-react";
import { SSEEvent } from "../types";

interface Props {
  events: SSEEvent[];
}

const AgentTracePanel: React.FC<Props> = ({ events }) => {
  if (events.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-tertiary">
        Waiting for agent events...
      </p>
    );
  }

  return (
    <div className="space-y-1.5 max-h-96 overflow-y-auto">
      {events.map((evt, i) => (
        <TraceCard key={i} event={evt} />
      ))}
    </div>
  );
};

const toolDisplayName: Record<string, string> = {
  extract_resume_text: "Extract Resume Text",
  detect_language: "Detect Language",
  translate_text: "Translate Text",
  check_pii_and_safety: "PII & Safety Check",
  score_resume: "Score Resume",
  compute_semantic_similarity: "Semantic Similarity",
  search_similar_candidates: "Search Similar Candidates",
  flag_for_human_review: "Flag for Review",
  generate_fit_summary: "Generate Fit Summary",
};

const TraceCard: React.FC<{ event: SSEEvent }> = ({ event }) => {
  if (event.event_type === "tool_call") {
    return (
      <div className="flex items-start gap-3 rounded-lg bg-accent-muted px-3.5 py-2.5 text-sm">
        <Wrench className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-accent" />
        <div className="min-w-0 flex-1">
          <p className="font-medium text-label">
            {toolDisplayName[event.tool_name] ?? event.tool_name}
          </p>
          <p className="text-xs text-secondary mt-0.5 truncate">
            {event.arguments_summary}
          </p>
        </div>
        <span className="text-xs text-tertiary shrink-0">
          iter {event.iteration}
        </span>
      </div>
    );
  }

  if (event.event_type === "tool_result") {
    return (
      <div className="flex items-start gap-3 rounded-lg bg-success/[0.06] px-3.5 py-2.5 text-sm">
        <CheckCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-success" />
        <div className="min-w-0 flex-1">
          <p className="font-medium text-label">
            {toolDisplayName[event.tool_name] ?? event.tool_name}
          </p>
          <p className="text-xs text-secondary mt-0.5 truncate">
            {event.result_summary}
          </p>
        </div>
        <span className="text-xs text-tertiary shrink-0">
          {event.duration_ms}ms
        </span>
      </div>
    );
  }

  if (event.event_type === "error") {
    return (
      <div className="flex items-start gap-3 rounded-lg bg-danger/[0.06] px-3.5 py-2.5 text-sm">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-danger" />
        <p className="text-danger">{event.message}</p>
      </div>
    );
  }

  return null;
};

export default AgentTracePanel;
