import { describe, it, expect } from "vitest";
import { isTerminalState } from "../types";

describe("types", () => {
  it("completed is terminal", () => {
    expect(isTerminalState("completed")).toBe(true);
  });

  it("completed_with_review is terminal", () => {
    expect(isTerminalState("completed_with_review")).toBe(true);
  });

  it("error is terminal", () => {
    expect(isTerminalState("error")).toBe(true);
  });

  it("idle is not terminal", () => {
    expect(isTerminalState("idle")).toBe(false);
  });

  it("agent_running is not terminal", () => {
    expect(isTerminalState("agent_running")).toBe(false);
  });
});
