import { describe, expect, it } from "vitest";
import { createStatusUpdate } from "./application-status";

describe("createStatusUpdate", () => {
  it("does not produce a status change without user confirmation for Applied", () => {
    expect(createStatusUpdate("Interested", "Applied", false)).toBeNull();
  });

  it("includes confirmation only after the user confirms Applied", () => {
    expect(createStatusUpdate("Interested", "Applied", true)).toEqual({
      status: "Applied",
      confirmed_by_user: true,
    });
  });

  it("does not send an unnecessary confirmation for other transitions", () => {
    expect(createStatusUpdate("Interested", "Application Prepared", false)).toEqual({
      status: "Application Prepared",
    });
  });

  it("omits a no-op transition", () => {
    expect(createStatusUpdate("Applied", "Applied", true)).toBeNull();
  });
});
