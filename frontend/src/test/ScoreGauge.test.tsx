import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ScoreGauge from "../components/ScoreGauge";

describe("ScoreGauge", () => {
  it("renders the score number", () => {
    render(<ScoreGauge score={85} />);
    expect(screen.getByText("85")).toBeInTheDocument();
  });

  it("renders 0 score", () => {
    render(<ScoreGauge score={0} />);
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("renders out of 100 label", () => {
    render(<ScoreGauge score={50} />);
    expect(screen.getByText("out of 100")).toBeInTheDocument();
  });
});
