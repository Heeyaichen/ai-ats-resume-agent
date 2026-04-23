import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ScoreBreakdown from "../components/ScoreBreakdown";

describe("ScoreBreakdown", () => {
  const breakdown = {
    keyword_match: 30,
    experience_alignment: 20,
    skills_coverage: 25,
  };

  it("renders all breakdown labels", () => {
    render(<ScoreBreakdown breakdown={breakdown} semanticSimilarity={0.85} />);
    expect(screen.getByText("Keyword Match")).toBeInTheDocument();
    expect(screen.getByText("Experience Alignment")).toBeInTheDocument();
    expect(screen.getByText("Skills Coverage")).toBeInTheDocument();
    expect(screen.getByText("Semantic Similarity")).toBeInTheDocument();
  });

  it("renders score values as fraction of max", () => {
    render(<ScoreBreakdown breakdown={breakdown} semanticSimilarity={0.5} />);
    expect(screen.getByText("30/40")).toBeInTheDocument();
    expect(screen.getByText("20/30")).toBeInTheDocument();
    expect(screen.getByText("25/30")).toBeInTheDocument();
  });
});
