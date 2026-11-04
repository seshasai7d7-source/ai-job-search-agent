"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ActionButton,
  EmptyState,
  LoadingState,
  Notice,
  PageHeading,
  SafeApplyLink,
  SkillsScore,
} from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { draftNote, errorMessage, formatDate } from "@/lib/presentation";
import {
  ApplicationSchema,
  DraftSchema,
  JobSchema,
  ResumeProfileSchema,
} from "@/lib/schemas";
import type { Draft } from "@/lib/schemas";
import { z } from "zod";

const DraftsSchema = z.array(DraftSchema);

function DraftItem({ draft }: { draft: Draft }) {
  const queryClient = useQueryClient();
  const [body, setBody] = useState(draft.body);
  const edit = useMutation({
    mutationFn: () =>
      api(`/drafts/${draft.id}`, DraftSchema, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body }),
      }),
    onSuccess: async (updated) => {
      setBody(updated.body);
      await queryClient.invalidateQueries({ queryKey: ["drafts", draft.job_id] });
    },
  });
  const approve = useMutation({
    mutationFn: () =>
      api(`/drafts/${draft.id}/approve`, DraftSchema, { method: "POST" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["drafts", draft.job_id] });
    },
  });
  const hasPlaceholders = body.includes("[ADD:");
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState("");

  async function copyDraft() {
    setCopyError("");
    try {
      await navigator.clipboard.writeText(body);
      setCopied(true);
    } catch (error) {
      setCopied(false);
      setCopyError(errorMessage(error));
    }
  }

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-950">
            {draft.kind === "cover_letter" ? "Cover letter" : "Application answer"}
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            {draft.status === "approved_by_user" ? "Approved by you" : "Draft"} ·{" "}
            {formatDate(draft.updated_at)}
          </p>
        </div>
        <ActionButton onClick={() => void copyDraft()} variant="secondary">
          Copy text
        </ActionButton>
      </div>
      <p className="mt-3 text-xs leading-5 text-slate-600">{draftNote}</p>
      {draft.question && (
        <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
          <span className="font-semibold">Question: </span>{draft.question}
        </p>
      )}
      {hasPlaceholders && (
        <div className="mt-3"><Notice kind="info">Replace every [ADD: …] placeholder before using this text.</Notice></div>
      )}
      <label className="mt-4 block text-sm font-medium text-slate-700">
        Draft text
        <textarea
          className="mt-1.5 min-h-48 w-full rounded-lg border border-slate-300 p-3 text-sm leading-6 focus-visible:outline-2 focus-visible:outline-indigo-600"
          disabled={draft.status === "approved_by_user"}
          onChange={(event) => setBody(event.target.value)}
          value={body}
        />
      </label>
      {edit.isError && <div className="mt-3"><Notice>{errorMessage(edit.error)}</Notice></div>}
      {approve.isError && <div className="mt-3"><Notice>{errorMessage(approve.error)}</Notice></div>}
      {copied && <p aria-live="polite" className="mt-2 text-sm text-emerald-700">Copied to clipboard.</p>}
      {copyError && <div className="mt-3"><Notice>{copyError}</Notice></div>}
      {draft.status !== "approved_by_user" && (
        <div className="mt-3 flex flex-wrap gap-2">
          <ActionButton
            disabled={edit.isPending || body.trim().length === 0 || body === draft.body}
            onClick={() => edit.mutate()}
            variant="secondary"
          >
            {edit.isPending ? "Saving" : "Save edits"}
          </ActionButton>
          <ActionButton
            disabled={approve.isPending || hasPlaceholders}
            onClick={() => approve.mutate()}
          >
            {approve.isPending ? "Approving" : "Approve draft"}
          </ActionButton>
        </div>
      )}
    </article>
  );
}

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const queryClient = useQueryClient();
  const [kind, setKind] = useState<"cover_letter" | "answer">("cover_letter");
  const [question, setQuestion] = useState("");
  const job = useQuery({
    queryKey: ["job", id],
    queryFn: () => api(`/jobs/${id}`, JobSchema),
    enabled: Number.isSafeInteger(id) && id > 0,
    retry: false,
  });
  const profile = useQuery({
    queryKey: ["resume"],
    queryFn: () => api("/resume", ResumeProfileSchema),
    retry: false,
  });
  const applications = useQuery({
    queryKey: ["applications"],
    queryFn: () => api("/applications", z.array(ApplicationSchema)),
  });
  const drafts = useQuery({
    queryKey: ["drafts", id],
    queryFn: () => api(`/jobs/${id}/drafts`, DraftsSchema),
    enabled: Number.isSafeInteger(id) && id > 0,
  });
  const existingApplication = applications.data?.find((item) => item.job_id === id);
  const createApplication = useMutation({
    mutationFn: () =>
      api("/applications", ApplicationSchema, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: id }),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
  });
  const createDraft = useMutation({
    mutationFn: () =>
      api(`/jobs/${id}/drafts`, DraftSchema, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind,
          ...(kind === "answer" ? { question } : {}),
        }),
      }),
    onSuccess: async () => {
      setQuestion("");
      await queryClient.invalidateQueries({ queryKey: ["drafts", id] });
    },
  });

  function submitDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createDraft.mutate();
  }

  if (!Number.isSafeInteger(id) || id < 1) {
    return <Notice>That job link is not valid.</Notice>;
  }
  if (job.isPending) return <LoadingState label="Loading job details" />;
  if (job.isError) return <Notice>{errorMessage(job.error)}</Notice>;

  const item = job.data;
  const approved = profile.data?.approved === true;
  const missingProfile = profile.error instanceof ApiError && profile.error.status === 404;

  return (
    <div className="mx-auto max-w-5xl">
      <Link className="mb-5 inline-block text-sm font-semibold text-indigo-700 underline" href="/jobs">
        Back to jobs
      </Link>
      <PageHeading
        eyebrow={item.source}
        title={item.title}
        description={`${item.company} · ${item.location || "Location not listed"} · Posted ${item.posted_date || "date not listed"}`}
        action={<SafeApplyLink value={item.apply_url} />}
      />
      {profile.isError && !missingProfile && (
        <div className="mb-5"><Notice>{errorMessage(profile.error)}</Notice></div>
      )}
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-7">
          <h2 className="text-lg font-semibold">Job description</h2>
          <p className="mt-4 whitespace-pre-line text-sm leading-7 text-slate-700">
            {item.description || "No description was provided by the source."}
          </p>
          <h3 className="mt-6 font-semibold">Skills mentioned by the source</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {item.skills_mentioned || "The source did not provide extracted skills."}
          </p>
        </section>
        <aside className="space-y-4">
          <section className="rounded-2xl border border-slate-200 bg-white p-5">
            {approved ? (
              <>
                <SkillsScore value={item.skills_overlap} />
                <div className="mt-4">
                  <SkillList title="Matched skills" values={item.matched_skills} />
                  <SkillList title="Skills to review" values={item.missing_skills} />
                </div>
              </>
            ) : (
              <Notice kind="info">
                <Link className="font-semibold underline" href="/resume">Approve your resume to unlock this.</Link>
              </Notice>
            )}
          </section>
          <section className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="font-semibold">Application tracker</h2>
            {applications.isError ? (
              <div className="mt-3"><Notice>{errorMessage(applications.error)}</Notice></div>
            ) : existingApplication ? (
              <p className="mt-2 text-sm text-slate-600">
                Current status: <strong>{existingApplication.status}</strong>.{" "}
                <Link className="font-semibold text-indigo-700 underline" href="/applications">Open tracker</Link>
              </p>
            ) : (
              <ActionButton
                disabled={createApplication.isPending || applications.isPending || applications.isError}
                onClick={() => createApplication.mutate()}
              >
                {createApplication.isPending ? "Adding" : "Track this job"}
              </ActionButton>
            )}
            {createApplication.isError && (
              <div className="mt-3"><Notice>{errorMessage(createApplication.error)}</Notice></div>
            )}
          </section>
        </aside>
      </div>

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Application drafts</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{draftNote}</p>
          </div>
        </div>
        {!approved ? (
          <div className="mt-4"><Notice kind="info"><Link className="font-semibold underline" href="/resume">Approve your resume to unlock this.</Link></Notice></div>
        ) : (
          <form className="mt-5 grid gap-3 md:grid-cols-[220px_minmax(0,1fr)_auto]" onSubmit={submitDraft}>
            <label className="text-sm font-medium text-slate-700">
              Draft type
              <select
                className="mt-1.5 min-h-10 w-full rounded-lg border border-slate-300 bg-white px-3"
                onChange={(event) =>
                  setKind(event.target.value === "answer" ? "answer" : "cover_letter")
                }
                value={kind}
              >
                <option value="cover_letter">Cover letter</option>
                <option value="answer">Answer a question</option>
              </select>
            </label>
            {kind === "answer" ? (
              <label className="text-sm font-medium text-slate-700">
                Application question
                <input
                  className="mt-1.5 min-h-10 w-full rounded-lg border border-slate-300 px-3"
                  onChange={(event) => setQuestion(event.target.value)}
                  required
                  value={question}
                />
              </label>
            ) : <div />}
            <div className="self-end">
              <ActionButton disabled={createDraft.isPending || (kind === "answer" && !question.trim())} type="submit">
                {createDraft.isPending ? "Creating" : "Create draft"}
              </ActionButton>
            </div>
          </form>
        )}
        {createDraft.isError && <div className="mt-4"><Notice>{errorMessage(createDraft.error)}</Notice></div>}
        {drafts.isPending ? (
          <div className="mt-4"><LoadingState label="Loading drafts" /></div>
        ) : drafts.isError ? (
          <div className="mt-4"><Notice>{errorMessage(drafts.error)}</Notice></div>
        ) : drafts.data.length === 0 ? (
          <div className="mt-4"><EmptyState title="No drafts yet">Create a draft only after your resume profile is approved.</EmptyState></div>
        ) : (
          <div className="mt-5 space-y-4">
            {drafts.data.map((draft) => <DraftItem draft={draft} key={draft.id} />)}
          </div>
        )}
      </section>
    </div>
  );
}

function SkillList({ title, values }: { title: string; values: string[] }) {
  return (
    <div className="mt-4">
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      {values.length === 0 ? (
        <p className="mt-1 text-sm text-slate-500">None identified.</p>
      ) : (
        <ul className="mt-2 flex flex-wrap gap-2">
          {values.map((skill) => (
            <li className="rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-700" key={skill}>{skill}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
