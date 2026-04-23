/** Shared type definitions for the ATS frontend. */

// ── Job lifecycle state machine (Section 6.1) ──────────────────

export type JobState =
  | "idle"
  | "uploading"
  | "queued"
  | "agent_running"
  | "completed"
  | "completed_with_review"
  | "failed_review_required"
  | "error";

export const isTerminalState = (s: JobState): boolean =>
  s === "completed" ||
  s === "completed_with_review" ||
  s === "failed_review_required" ||
  s === "error";

// ── API types ───────────────────────────────────────────────────

export interface UploadResponse {
  job_id: string;
  status: "queued";
}

export interface ScorePayload {
  job_id: string;
  status: string;
  score_data: ScoreData | null;
}

export interface ScoreData {
  score: number | null;
  breakdown: {
    keyword_match: number;
    experience_alignment: number;
    skills_coverage: number;
  } | null;
  matched_keywords: string[];
  missing_keywords: string[];
  semantic_similarity: number | null;
  fit_summary: string | null;
  human_review_required: boolean;
  human_review_reason: string | null;
  similar_candidates: SimilarCandidate[];
}

export interface SimilarCandidate {
  candidate_id: string;
  job_id: string;
  score: number;
  similarity: number;
}

// ── SSE event types (Section 5.2) ──────────────────────────────

export type SSEEvent =
  | ToolCallEvent
  | ToolResultEvent
  | CompleteEvent
  | ErrorEvent;

export interface ToolCallEvent {
  event_type: "tool_call";
  job_id: string;
  iteration: number;
  tool_name: string;
  arguments_summary: string;
  timestamp: string;
}

export interface ToolResultEvent {
  event_type: "tool_result";
  job_id: string;
  iteration: number;
  tool_name: string;
  result_summary: string;
  duration_ms: number;
  timestamp: string;
}

export interface CompleteEvent {
  event_type: "complete";
  job_id: string;
  result: ScoreData;
  timestamp: string;
}

export interface ErrorEvent {
  event_type: "error";
  job_id: string;
  message: string;
  retryable: boolean;
  timestamp: string;
}
