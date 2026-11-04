"use client";

import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { ApiError, api } from "@/lib/api";
import { HealthSchema } from "@/lib/schemas";

function getErrorMessage(error: Error): string {
  if (error instanceof ApiError) {
    return error.message || "Couldn't reach the server.";
  }
  if (error instanceof z.ZodError) {
    return "The backend returned an invalid health response.";
  }
  return "Couldn't reach the server. Retry.";
}

export default function Home() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api("/health", HealthSchema),
    retry: false,
  });

  return (
    <div className="mx-auto w-full max-w-5xl">
      <header className="mb-9">
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-indigo-600">
          Workspace overview
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          Your job search, in one place.
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">
          A local-first workspace for discovering opportunities and keeping every
          application decision in your hands.
        </p>
      </header>

      <section
        aria-labelledby="backend-heading"
        className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
      >
        <div className="flex flex-col gap-5 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
          <div className="flex items-start gap-4">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700">
              <svg
                aria-hidden="true"
                className="size-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4.75 6.75h14.5v4.5H4.75zM4.75 12.75h14.5v4.5H4.75z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M8 9h.01M8 15h.01M11 9h5M11 15h5"
                />
              </svg>
            </div>
            <div>
              <h2
                id="backend-heading"
                className="text-lg font-semibold text-slate-950"
              >
                Backend connection
              </h2>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                The interface connects to your local FastAPI service. Your data
                stays on your machine.
              </p>
            </div>
          </div>

          <div
            aria-live="polite"
            className="flex min-h-10 items-center gap-2 self-start rounded-full border border-slate-200 bg-slate-50 px-3 text-sm font-medium text-slate-700 sm:self-auto"
          >
            {health.isPending ? (
              <>
                <span className="size-2 animate-pulse rounded-full bg-amber-500" />
                Checking connection
              </>
            ) : health.isError ? (
              <>
                <span className="size-2 rounded-full bg-rose-500" />
                Not connected
              </>
            ) : health.data.status === "ok" ? (
              <>
                <span className="size-2 rounded-full bg-emerald-500" />
                Backend is online
              </>
            ) : (
              <>
                <span className="size-2 rounded-full bg-amber-500" />
                Backend responded
              </>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-4 border-t border-slate-100 bg-slate-50/70 px-6 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <p className="text-sm text-slate-600">
            {health.isError
              ? getErrorMessage(health.error)
              : health.isSuccess
                ? `Health check: ${health.data.status}`
                : "Checking the health endpoint at /api/health."}
          </p>
          <button
            className="inline-flex min-h-10 items-center justify-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={health.isFetching}
            onClick={() => void health.refetch()}
            type="button"
          >
            {health.isFetching ? "Checking" : "Check again"}
          </button>
        </div>
      </section>

      <section className="mt-8 grid gap-4 md:grid-cols-3">
        {[
          {
            number: "01",
            title: "Review before you approve",
            description:
              "Resume facts stay under your review. Matching and drafts require your approval.",
          },
          {
            number: "02",
            title: "You stay in control",
            description:
              "The app helps organize your search; it never submits applications for you.",
          },
          {
            number: "03",
            title: "Clear, honest matching",
            description:
              "Skills overlap is a comparison, not a prediction of hiring outcomes.",
          },
        ].map((item) => (
          <article
            className="rounded-2xl border border-slate-200 bg-white p-5"
            key={item.number}
          >
            <p className="text-xs font-bold tracking-[0.12em] text-indigo-600">
              {item.number}
            </p>
            <h2 className="mt-3 font-semibold text-slate-900">{item.title}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              {item.description}
            </p>
          </article>
        ))}
      </section>
    </div>
  );
}
