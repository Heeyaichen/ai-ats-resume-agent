import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PrivacyBadges from "../components/PrivacyBadges";

describe("PrivacyBadges", () => {
  it("renders language badge when detected", () => {
    render(<PrivacyBadges languageDetected="French" wasTranslated={true} />);
    expect(screen.getByText(/French/)).toBeInTheDocument();
    expect(screen.getByText(/translated/)).toBeInTheDocument();
  });

  it("renders PII badge when redacted", () => {
    render(<PrivacyBadges piiRedacted={true} />);
    expect(screen.getByText("PII Redacted")).toBeInTheDocument();
  });

  it("renders nothing when no flags set", () => {
    const { container } = render(<PrivacyBadges />);
    expect(container.querySelectorAll("span").length).toBe(0);
  });
});
