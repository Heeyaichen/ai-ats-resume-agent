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
      <div className="rounded-lg border border-gray-200 bg-white p-4 text-center text-sm text-gray-400">
        Waiting for agent events...
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-96 overflow-y-auto">
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
      <div className="flex items-start gap-2 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm">
        <Wrench className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-500" />
        <div>
          <p className="font-medium text-blue-800">
            {toolDisplayName[event.tool_name] ?? event.tool_name}
          </p>
          <p className="text-blue-600 text-xs mt-0.5">{event.arguments_summary}</p>
        </div>
        <span className="ml-auto text-xs text-blue-400">iter {event.iteration}</span>
      </div>
    );
  }

  if (event.event_type === "tool_result") {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-sm">
        <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-green-500" />
        <div className="min-w-0 flex-1">
          <p className="font-medium text-green-800">
            {toolDisplayName[event.tool_name] ?? event.tool_name}
          </p>
          <p className="text-green-600 text-xs mt-0.5 truncate">{event.result_summary}</p>
        </div>
        <span className="text-xs text-green-400">{event.duration_ms}ms</span>
      </div>
    );
  }

  if (event.event_type === "error") {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm">
        <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-500" />
        <p className="text-red-700">{event.message}</p>
      </div>
    );
  }

  // complete event — no card needed here (handled by report).
  return null;
};

export default AgentTracePanel;
