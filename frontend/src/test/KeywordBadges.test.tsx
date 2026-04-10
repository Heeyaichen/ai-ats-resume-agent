import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import KeywordBadges from "../components/KeywordBadges";

describe("KeywordBadges", () => {
  it("renders matched and missing keywords", () => {
    render(
      <KeywordBadges matched={["python", "react"]} missing={["azure", "terraform"]} />,
    );
    expect(screen.getByText("python")).toBeInTheDocument();
    expect(screen.getByText("react")).toBeInTheDocument();
    expect(screen.getByText("azure")).toBeInTheDocument();
    expect(screen.getByText("terraform")).toBeInTheDocument();
  });

  it("renders Matched Keywords header when matched keywords exist", () => {
    render(<KeywordBadges matched={["python"]} missing={[]} />);
    expect(screen.getByText("Matched Keywords")).toBeInTheDocument();
  });

  it("renders Missing Keywords header when missing keywords exist", () => {
    render(<KeywordBadges matched={[]} missing={["docker"]} />);
    expect(screen.getByText("Missing Keywords")).toBeInTheDocument();
  });

  it("renders nothing when both arrays empty", () => {
    const { container } = render(<KeywordBadges matched={[]} missing={[]} />);
    expect(container.querySelectorAll("span").length).toBe(0);
  });
});
