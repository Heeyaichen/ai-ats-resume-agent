import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import AgentTracePanel from "../components/AgentTracePanel";
import { SSEEvent } from "../types";

describe("AgentTracePanel", () => {
  it("shows waiting message when no events", () => {
    render(<AgentTracePanel events={[]} />);
    expect(screen.getByText(/Waiting for agent events/)).toBeInTheDocument();
  });

  it("renders tool_call events", () => {
    const events: SSEEvent[] = [
      {
        event_type: "tool_call",
        job_id: "j1",
        iteration: 1,
        tool_name: "extract_resume_text",
        arguments_summary: "blob_path=resumes-raw/j1/resume.pdf",
        timestamp: "2026-04-10T00:00:00Z",
      },
    ];
    render(<AgentTracePanel events={events} />);
    expect(screen.getByText("Extract Resume Text")).toBeInTheDocument();
  });

  it("renders tool_result events", () => {
    const events: SSEEvent[] = [
      {
        event_type: "tool_result",
        job_id: "j1",
        iteration: 1,
        tool_name: "score_resume",
        result_summary: "Score: 75/100",
        duration_ms: 1200,
        timestamp: "2026-04-10T00:00:00Z",
      },
    ];
    render(<AgentTracePanel events={events} />);
    expect(screen.getByText("Score Resume")).toBeInTheDocument();
    expect(screen.getByText("1200ms")).toBeInTheDocument();
  });

  it("renders error events", () => {
    const events: SSEEvent[] = [
      {
        event_type: "error",
        job_id: "j1",
        message: "Agent failed after 12 iterations.",
        retryable: false,
        timestamp: "2026-04-10T00:00:00Z",
      },
    ];
    render(<AgentTracePanel events={events} />);
    expect(screen.getByText("Agent failed after 12 iterations.")).toBeInTheDocument();
  });
});
