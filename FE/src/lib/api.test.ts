import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { z } from "zod";
import { api, ApiError } from "./api";

const server = setupServer(
  http.get("http://localhost/api/health", () =>
    HttpResponse.json({ status: "ok" }),
  ),
);
const HealthSchema = z.object({ status: z.string() });

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  vi.unstubAllGlobals();
});
afterAll(() => server.close());

beforeEach(() => {
  const interceptedFetch = globalThis.fetch.bind(globalThis);
  vi.stubGlobal("fetch", (input: RequestInfo | URL, init?: RequestInit) =>
    interceptedFetch(new URL(String(input), "http://localhost"), init),
  );
});

describe("api response handling", () => {
  it("validates and returns successful API data", async () => {
    await expect(api("/health", HealthSchema)).resolves.toEqual({ status: "ok" });
  });

  it("rejects malformed response data", async () => {
    server.use(
      http.get("http://localhost/api/health", () =>
        HttpResponse.json({ status: 12 }),
      ),
    );
    await expect(api("/health", HealthSchema)).rejects.toBeInstanceOf(z.ZodError);
  });

  it("shows backend detail for a conflict", async () => {
    server.use(
      http.get("http://localhost/api/health", () =>
        HttpResponse.json({ detail: "Approve a resume first." }, { status: 409 }),
      ),
    );
    await expect(api("/health", HealthSchema)).rejects.toMatchObject({
      status: 409,
      message: "Approve a resume first.",
    } satisfies Partial<ApiError>);
  });

  it("uses safe retry copy for server errors", async () => {
    server.use(
      http.get("http://localhost/api/health", () =>
        HttpResponse.json({ detail: "Private backend detail." }, { status: 500 }),
      ),
    );
    await expect(api("/health", HealthSchema)).rejects.toMatchObject({
      status: 500,
      message: "Couldn't reach the server. Retry.",
    } satisfies Partial<ApiError>);
  });
});
