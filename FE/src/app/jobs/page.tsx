"use client";

import Link from "next/link";
import { Suspense, useMemo, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ActionButton,
  EmptyState,
  JobCard,
  LoadingState,
  Notice,
  PageHeading,
} from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { ApplicationSchema, JobSchema, ResumeProfileSchema } from "@/lib/schemas";
import { errorMessage } from "@/lib/presentation";
import { z } from "zod";

const JobsSchema = z.array(JobSchema);
const ApplicationsSchema = z.array(ApplicationSchema);
const RecomputeSchema = z.object({
  profile_id: z.number(),
  computed_jobs: z.number(),
  label: z.string(),
  note: z.string(),
});

function JobsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const queryString = searchParams.toString();
  const jobs = useQuery({
    queryKey: ["jobs", queryString],
    queryFn: () => api(`/jobs${queryString ? `?${queryString}` : ""}`, JobsSchema),
  });
  const applications = useQuery({
    queryKey: ["applications"],
    queryFn: () => api("/applications", ApplicationsSchema),
  });
  const profile = useQuery({
    queryKey: ["resume"],
    queryFn: () => api("/resume", ResumeProfileSchema),
    retry: false,
  });
  const recompute = useMutation({
    mutationFn: () =>
      api("/matches/recompute", RecomputeSchema, { method: "POST" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
  const applicationByJob = useMemo(
    () => new Map(applications.data?.map((item) => [item.job_id, item.status])),
    [applications.data],
  );
  const canMatch = profile.data?.approved === true;

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const params = new URLSearchParams();
    for (const key of ["q", "role", "company", "location", "min_overlap", "sort"]) {
      const value = String(formData.get(key) ?? "").trim();
      if (value) params.set(key, value);
    }
    const active = String(formData.get("active") ?? "true");
    if (active !== "all") params.set("is_active", active);
    router.replace(`/jobs${params.size ? `?${params.toString()}` : ""}`);
  }

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeading
        eyebrow="Opportunities"
        title="Jobs"
        description="Review public listings saved by your search configuration. Nothing is submitted from this workspace."
        action={
          <Link
            className="inline-flex min-h-10 items-center justify-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-800 hover:bg-slate-50"
            href="/search-runs"
          >
            View search runs
          </Link>
        }
      />

      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        {[
          ["Listings shown", jobs.data?.length],
          ["Active listings", jobs.data?.filter((job) => job.is_active).length],
          ["Tracked applications", applications.data?.length],
        ].map(([label, count]) => (
          <div className="rounded-xl border border-slate-200 bg-white p-4" key={label}>
            <p className="text-xs font-medium text-slate-500">{label}</p>
            <p className="mt-1 text-2xl font-semibold text-slate-950">
              {count ?? "—"}
            </p>
          </div>
        ))}
      </div>

      <form
        className="mb-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4"
        onSubmit={applyFilters}
      >
        {[
          { key: "q", label: "Search jobs", placeholder: "Title, company, description" },
          { key: "role", label: "Role", placeholder: "Role title" },
          { key: "company", label: "Company", placeholder: "Company name" },
          { key: "location", label: "Location", placeholder: "Location" },
        ].map((field) => (
          <label className="text-xs font-semibold text-slate-700" key={field.key}>
            {field.label}
            <input
              className="mt-1.5 min-h-10 w-full rounded-lg border border-slate-300 px-3 text-sm font-normal focus-visible:outline-2 focus-visible:outline-indigo-600"
              defaultValue={searchParams.get(field.key) ?? ""}
              name={field.key}
              placeholder={field.placeholder}
            />
          </label>
        ))}
        <label className="text-xs font-semibold text-slate-700">
          Minimum skills overlap
          <input
            className="mt-1.5 min-h-10 w-full rounded-lg border border-slate-300 px-3 text-sm font-normal focus-visible:outline-2 focus-visible:outline-indigo-600"
            defaultValue={searchParams.get("min_overlap") ?? ""}
            max="100"
            min="0"
            name="min_overlap"
            placeholder="0–100"
            type="number"
          />
        </label>
        <label className="text-xs font-semibold text-slate-700">
          Listing status
          <select
            className="mt-1.5 min-h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal focus-visible:outline-2 focus-visible:outline-indigo-600"
            defaultValue={searchParams.get("is_active") ?? "true"}
            name="active"
          >
            <option value="true">Active only</option>
            <option value="false">Inactive only</option>
            <option value="all">All listings</option>
          </select>
        </label>
        <label className="text-xs font-semibold text-slate-700">
          Sort by
          <select
            className="mt-1.5 min-h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal focus-visible:outline-2 focus-visible:outline-indigo-600"
            defaultValue={searchParams.get("sort") ?? "last_seen_at"}
            name="sort"
          >
            <option value="last_seen_at">Recently seen</option>
            <option value="first_seen_at">First seen</option>
            <option value="company">Company</option>
            <option value="title">Title</option>
          </select>
        </label>
        <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-4">
          <ActionButton type="submit">Apply filters</ActionButton>
          <ActionButton
            onClick={() => router.replace("/jobs")}
            variant="secondary"
          >
            Clear filters
          </ActionButton>
        </div>
      </form>

      {!canMatch && (
        <Notice kind="info">
          <Link className="font-semibold underline" href="/resume">
            Approve your resume to unlock this.
          </Link>{" "}
          Matching is unavailable until your current resume profile is approved.
        </Notice>
      )}
      {applications.isError && (
        <div className="mt-4"><Notice>{errorMessage(applications.error)}</Notice></div>
      )}
      {profile.isError && !(profile.error instanceof ApiError && profile.error.status === 404) && (
        <div className="mt-4"><Notice>{errorMessage(profile.error)}</Notice></div>
      )}
      {recompute.isError && (
        <div className="mt-4"><Notice>{errorMessage(recompute.error)}</Notice></div>
      )}
      {canMatch && (
        <div className="my-4 flex flex-wrap items-center gap-3">
          <ActionButton
            disabled={recompute.isPending}
            onClick={() => recompute.mutate()}
          >
            {recompute.isPending ? "Comparing skills" : "Recompute skills overlap"}
          </ActionButton>
          {recompute.isSuccess && (
            <p aria-live="polite" className="text-sm text-slate-600">
              Compared {recompute.data.computed_jobs} active listings.
            </p>
          )}
        </div>
      )}

      <div className="mt-5 space-y-4">
        {jobs.isPending ? (
          <LoadingState label="Loading jobs" />
        ) : jobs.isError ? (
          <Notice>{errorMessage(jobs.error)}</Notice>
        ) : jobs.data.length === 0 ? (
          <EmptyState title="No jobs match these filters">
            Run a search using your configured sources, or adjust the filters above.
            The app will not create sample listings.
          </EmptyState>
        ) : (
          jobs.data.map((job) => (
            <div key={job.id}>
              <JobCard job={job} matchingEnabled={canMatch} />
              {applicationByJob.has(job.id) && (
                <p className="px-5 pt-2 text-xs text-slate-600">
                  Tracker status: {applicationByJob.get(job.id)}
                </p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default function JobsPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading job filters" />}>
      <JobsContent />
    </Suspense>
  );
}
