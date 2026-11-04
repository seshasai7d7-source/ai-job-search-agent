import Link from "next/link";
import type { ReactNode } from "react";
import type { Job } from "@/lib/schemas";
import { scoreNote, safeHttpUrl } from "@/lib/presentation";

export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <header className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.14em] text-indigo-600">
          {eyebrow}
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
          {title}
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          {description}
        </p>
      </div>
      {action}
    </header>
  );
}

export function Notice({
  children,
  kind = "error",
}: {
  children: ReactNode;
  kind?: "error" | "info";
}) {
  return (
    <div
      aria-live="polite"
      className={`rounded-xl border p-4 text-sm leading-6 ${
        kind === "error"
          ? "border-rose-200 bg-rose-50 text-rose-800"
          : "border-indigo-200 bg-indigo-50 text-indigo-800"
      }`}
      role={kind === "error" ? "alert" : "status"}
    >
      {children}
    </div>
  );
}

export function EmptyState({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
      <h2 className="font-semibold text-slate-900">{title}</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-600">
        {children}
      </p>
    </div>
  );
}

export function LoadingState({ label = "Loading data" }: { label?: string }) {
  return (
    <div
      aria-busy="true"
      aria-live="polite"
      className="space-y-3 rounded-xl border border-slate-200 bg-white p-5"
      role="status"
    >
      <span className="sr-only">{label}…</span>
      <div className="h-3 w-1/3 animate-pulse rounded bg-slate-200" />
      <div className="h-3 w-full animate-pulse rounded bg-slate-100" />
      <div className="h-3 w-2/3 animate-pulse rounded bg-slate-100" />
    </div>
  );
}

export function ActionButton({
  children,
  disabled,
  onClick,
  type = "button",
  variant = "primary",
}: {
  children: ReactNode;
  disabled?: boolean;
  onClick?: () => void;
  type?: "button" | "submit";
  variant?: "primary" | "secondary";
}) {
  const color =
    variant === "primary"
      ? "border-indigo-700 bg-indigo-700 text-white hover:bg-indigo-800"
      : "border-slate-300 bg-white text-slate-800 hover:bg-slate-50";
  return (
    <button
      className={`inline-flex min-h-10 items-center justify-center rounded-lg border px-4 py-2 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:cursor-not-allowed disabled:opacity-60 ${color}`}
      disabled={disabled}
      onClick={onClick}
      type={type}
    >
      {children}
    </button>
  );
}

export function SafeApplyLink({ value }: { value: string }) {
  const href = safeHttpUrl(value);
  if (!href) {
    return <span className="text-xs text-slate-500">Apply link unavailable</span>;
  }
  return (
    <a
      className="text-sm font-semibold text-indigo-700 underline decoration-indigo-300 underline-offset-4 hover:text-indigo-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
      href={href}
      rel="noopener noreferrer"
      target="_blank"
    >
      View official posting
    </a>
  );
}

export function SkillsScore({ value }: { value: number | null }) {
  return (
    <div className="rounded-xl bg-indigo-50 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
        Skills overlap
      </p>
      <p className="mt-1 text-xl font-semibold text-slate-950">
        {value === null ? "Not enough data" : `${Math.round(value)}%`}
      </p>
      <p className="mt-1 text-xs leading-5 text-slate-600">{scoreNote}</p>
    </div>
  );
}

export function JobCard({
  job,
  matchingEnabled = true,
}: {
  job: Job;
  matchingEnabled?: boolean;
}) {
  const matched = new Set(job.matched_skills);
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_230px]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            {!job.is_active && (
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                Inactive
              </span>
            )}
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
              {job.source}
            </span>
          </div>
          <h2 className="mt-3 text-lg font-semibold text-slate-950">
            <Link className="hover:text-indigo-700" href={`/jobs/${job.id}`}>
              {job.title}
            </Link>
          </h2>
          <p className="mt-1 text-sm font-medium text-slate-700">
            {job.company} <span className="text-slate-400">·</span>{" "}
            {job.location || "Location not listed"}
          </p>
          <p className="mt-3 line-clamp-3 whitespace-pre-line text-sm leading-6 text-slate-600">
            {job.description || "No description was provided by the source."}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {[...job.matched_skills, ...job.missing_skills].map((skill) => (
              <span
                className={`rounded-full border px-2.5 py-1 text-xs ${
                  matched.has(skill)
                    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                    : "border-slate-200 bg-slate-50 text-slate-600"
                }`}
                key={skill}
              >
                {skill}
              </span>
            ))}
            {job.matched_skills.length + job.missing_skills.length === 0 && (
              <span className="text-xs text-slate-500">
                Skills have not been compared yet.
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-col gap-3">
          {matchingEnabled ? (
            <SkillsScore value={job.skills_overlap} />
          ) : (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <p className="text-sm font-semibold text-slate-800">
                <Link className="underline" href="/resume">
                  Approve your resume to unlock this.
                </Link>
              </p>
            </div>
          )}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Link
              className="text-sm font-semibold text-indigo-700 underline decoration-indigo-300 underline-offset-4"
              href={`/jobs/${job.id}`}
            >
              View details
            </Link>
            <SafeApplyLink value={job.apply_url} />
          </div>
        </div>
      </div>
    </article>
  );
}
