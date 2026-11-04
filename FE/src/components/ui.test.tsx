// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SkillsScore } from "./ui";
import { scoreNote } from "@/lib/presentation";

describe("SkillsScore", () => {
  it("shows the required explanation and honest empty score", () => {
    render(<SkillsScore value={null} />);
    expect(screen.getByText("Not enough data")).toBeInTheDocument();
    expect(screen.getByText(scoreNote)).toBeInTheDocument();
  });
});
