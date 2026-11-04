import { describe, expect, it } from "vitest";
import { safeHttpUrl, scoreNote } from "./presentation";

describe("safeHttpUrl", () => {
  it("allows only valid HTTP and HTTPS URLs", () => {
    expect(safeHttpUrl("https://jobs.example.test/opening")).toBe(
      "https://jobs.example.test/opening",
    );
    expect(safeHttpUrl("http://jobs.example.test/opening")).toBe(
      "http://jobs.example.test/opening",
    );
    expect(safeHttpUrl("javascript:alert(1)")).toBeNull();
    expect(safeHttpUrl("data:text/html,unsafe")).toBeNull();
    expect(safeHttpUrl("not a url")).toBeNull();
  });
});

it("uses the required non-predictive score explanation", () => {
  expect(scoreNote).toBe(
    "Skills overlap compares job skills with your approved resume. It is not a chance of being hired.",
  );
});
