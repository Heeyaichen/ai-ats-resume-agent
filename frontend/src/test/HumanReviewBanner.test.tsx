import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import HumanReviewBanner from "../components/HumanReviewBanner";

describe("HumanReviewBanner", () => {
  it("renders the banner with reason", () => {
    render(<HumanReviewBanner reason="Low score detected." />);
    expect(screen.getByText("Flagged for Human Review")).toBeInTheDocument();
    expect(screen.getByText("Low score detected.")).toBeInTheDocument();
  });
});
