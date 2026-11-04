"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ActionButton, EmptyState, LoadingState, Notice, PageHeading } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage, formatDate } from "@/lib/presentation";
import { SearchRunCreatedSchema, SearchRunSchema } from "@/lib/schemas";
import type { SearchRun } from "@/lib/schemas";
import { z } from "zod";

const SearchRunsSchema = z.array(SearchRunSchema);

function SearchRunCard({ run }: { run: SearchRun }) {
  const detail = useQuery({
    queryKey: ["search-run", run.id],
    queryFn: () => api(`/search-runs/${run.id}`, SearchRunSchema),
    refetchInterval: run.status === "running" ? 3000 : false,
  });
  const info = detail.data ?? run;
  const sources = info.per_source_results
    ? Object.entries(info.per_source_results)
    : [];
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-slate-950">
            Search run #{run.id}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Started {formatDate(run.started_at)}
            {info.finished_at ? ` · Finished ${formatDate(info.finished_at)}` : ""}
          </p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
          run.status === "running"
            ? "bg-amber-50 text-amber-800"
            : run.status === "failed"
              ? "bg-rose-50 text-rose-800"
              : "bg-emerald-50 text-emerald-800"
        }`}>{run.status}</span>
      </div>
      {detail.isError && <div className="mt-3"><Notice>{errorMessage(detail.error)}</Notice></div>}
      {detail.isPending ? (
        <p className="mt-4 text-sm text-slate-500">Loading source details…</p>
      ) : (
        <>
          <p className="mt-4 text-sm text-slate-700">
            New jobs saved: <strong>{info.new_jobs}</strong>
          </p>
          {sources.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">
              {run.status === "running" ? "Waiting for configured sources…" : "No source details were returned."}
            </p>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="py-2 pr-3 font-semibold">Source</th>
                    <th className="py-2 pr-3 font-semibold">Fetched</th>
                    <th className="py-2 pr-3 font-semibold">Kept</th>
                    <th className="py-2 pr-3 font-semibold">New</th>
                    <th className="py-2 font-semibold">Error</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {sources.map(([source, result]) => (
                    <tr key={source}>
                      <td className="py-3 pr-3 font-medium text-slate-800">{source}</td>
                      <td className="py-3 pr-3">{result.fetched}</td>
                      <td className="py-3 pr-3">{result.kept}</td>
                      <td className="py-3 pr-3">{result.new_jobs}</td>
                      <td className="max-w-64 py-3 text-rose-700">{result.error || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </article>
  );
}

export default function SearchRunsPage() {
  const queryClient = useQueryClient();
  const runs = useQuery({
    queryKey: ["search-runs"],
    queryFn: () => api("/search-runs?limit=50", SearchRunsSchema),
    refetchInterval: (query) =>
      query.state.data?.some((run) => run.status === "running") ? 3000 : false,
  });
  const start = useMutation({
    mutationFn: () =>
      api("/search-runs", SearchRunCreatedSchema, { method: "POST" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["search-runs"] });
    },
  });

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeading
        eyebrow="Discovery"
        title="Search runs"
        description="Review each source's fetched, kept, new, and error counts. Active runs refresh every three seconds."
        action={
          <ActionButton disabled={start.isPending} onClick={() => start.mutate()}>
            {start.isPending ? "Starting search" : "Run job search"}
          </ActionButton>
        }
      />
      <p className="mb-5 text-sm text-slate-600">
        Search requests public job-board listings using your local configuration.{" "}
        <Link className="font-semibold text-indigo-700 underline" href="/jobs">Browse saved jobs</Link>
      </p>
      {start.isError && <div className="mb-4"><Notice>{errorMessage(start.error)}</Notice></div>}
      {runs.isPending ? (
        <LoadingState label="Loading search history" />
      ) : runs.isError ? (
        <Notice>{errorMessage(runs.error)}</Notice>
      ) : runs.data.length === 0 ? (
        <EmptyState title="No search runs yet">
          Start a search to query the sources configured in your local settings.
        </EmptyState>
      ) : (
        <div className="space-y-4">
          {runs.data.map((run) => <SearchRunCard key={run.id} run={run} />)}
        </div>
      )}
    </div>
  );
}
