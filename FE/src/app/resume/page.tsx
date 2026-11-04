"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ActionButton, EmptyState, LoadingState, Notice, PageHeading } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { errorMessage, formatDate } from "@/lib/presentation";
import { ResumeProfileSchema } from "@/lib/schemas";
import type { ResumeProfile } from "@/lib/schemas";
import { z } from "zod";

const RecomputeSchema = z.object({
  profile_id: z.number(),
  computed_jobs: z.number(),
  label: z.string(),
  note: z.string(),
});

type EditableProfile = Pick<
  ResumeProfile,
  | "summary"
  | "skills"
  | "projects"
  | "education_lines"
  | "degrees_detected"
  | "experience_lines"
  | "experience_date_ranges"
>;

const editableFields: { key: keyof EditableProfile; label: string; multiline?: boolean }[] = [
  { key: "summary", label: "Summary", multiline: true },
  { key: "skills", label: "Skills", multiline: true },
  { key: "projects", label: "Projects", multiline: true },
  { key: "education_lines", label: "Education", multiline: true },
  { key: "degrees_detected", label: "Detected degrees", multiline: true },
  { key: "experience_lines", label: "Experience", multiline: true },
  { key: "experience_date_ranges", label: "Experience dates", multiline: true },
];

function toEditable(profile: ResumeProfile): EditableProfile {
  return {
    summary: profile.summary,
    skills: profile.skills,
    projects: profile.projects,
    education_lines: profile.education_lines,
    degrees_detected: profile.degrees_detected,
    experience_lines: profile.experience_lines,
    experience_date_ranges: profile.experience_date_ranges,
  };
}

function toText(value: string | string[]): string {
  return Array.isArray(value) ? value.join("\n") : value;
}

function toPayload(value: EditableProfile) {
  return Object.fromEntries(
    Object.entries(value).map(([key, field]) => [
      key,
      Array.isArray(field)
        ? field.map((line) => line.trim()).filter(Boolean)
        : field.trim(),
    ]),
  );
}

export default function ResumePage() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [form, setForm] = useState<EditableProfile | null>(null);
  const [loadedProfileId, setLoadedProfileId] = useState<number | null>(null);
  const [formError, setFormError] = useState("");
  const profile = useQuery({
    queryKey: ["resume"],
    queryFn: () => api("/resume", ResumeProfileSchema),
    retry: false,
  });
  if (profile.data && profile.data.id !== loadedProfileId) {
    setLoadedProfileId(profile.data.id);
    setForm(toEditable(profile.data));
  }

  const upload = useMutation({
    mutationFn: (selectedFile: File) => {
      const body = new FormData();
      body.append("resume", selectedFile);
      return api("/resume/upload", ResumeProfileSchema, { method: "POST", body });
    },
    onSuccess: async (data) => {
      setFile(null);
      setForm(toEditable(data));
      await queryClient.invalidateQueries({ queryKey: ["resume"] });
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
  const edit = useMutation({
    mutationFn: (changes: EditableProfile) =>
      api("/resume", ResumeProfileSchema, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(changes)),
      }),
    onSuccess: async (data) => {
      setForm(toEditable(data));
      await queryClient.invalidateQueries({ queryKey: ["resume"] });
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
  const approve = useMutation({
    mutationFn: () => api("/resume/approve", ResumeProfileSchema, { method: "POST" }),
    onSuccess: async (data) => {
      setForm(toEditable(data));
      await queryClient.invalidateQueries({ queryKey: ["resume"] });
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
  const recompute = useMutation({
    mutationFn: () =>
      api("/matches/recompute", RecomputeSchema, { method: "POST" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      await queryClient.invalidateQueries({ queryKey: ["job"] });
    },
  });

  function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    if (!file) return setFormError("Select a PDF file to upload.");
    if (file.type !== "application/pdf" || !file.name.toLowerCase().endsWith(".pdf")) {
      return setFormError("Choose a PDF file.");
    }
    if (file.size > 5 * 1024 * 1024) {
      return setFormError("The PDF must be 5 MB or smaller.");
    }
    upload.mutate(file);
  }

  function updateField(key: keyof EditableProfile, text: string) {
    setForm((current) => {
      if (!current) return current;
      return {
        ...current,
        [key]: key === "summary"
          ? text
          : text.split(/\r?\n/),
      };
    });
  }

  function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (form) edit.mutate(form);
  }

  const noProfile = profile.error instanceof ApiError && profile.error.status === 404;

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeading
        eyebrow="Profile review"
        title="Resume"
        description="Upload a PDF and review every extracted fact before approving it. Your resume content stays in this app's in-memory state and local API."
      />
      <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
        <h2 className="text-lg font-semibold">Upload a resume PDF</h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          Maximum file size: 5 MB. Uploading a new file creates a profile that must be reviewed and approved.
        </p>
        <form className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={submitUpload}>
          <label className="block flex-1 text-sm font-medium text-slate-700">
            PDF file
            <input
              accept="application/pdf,.pdf"
              className="mt-1.5 block min-h-11 w-full rounded-lg border border-slate-300 p-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-indigo-50 file:px-3 file:py-1.5 file:font-semibold file:text-indigo-700 focus-visible:outline-2 focus-visible:outline-indigo-600"
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null);
                setFormError("");
              }}
              type="file"
            />
          </label>
          <ActionButton disabled={upload.isPending} type="submit">
            {upload.isPending ? "Uploading and parsing" : "Upload PDF"}
          </ActionButton>
        </form>
        {formError && <p className="mt-3 text-sm text-rose-700" role="alert">{formError}</p>}
        {upload.isError && <div className="mt-3"><Notice>{errorMessage(upload.error)}</Notice></div>}
      </section>

      {profile.isPending ? (
        <LoadingState label="Loading resume profile" />
      ) : noProfile ? (
        <EmptyState title="No resume profile yet">
          Upload your PDF to review the extracted information. Matching and drafts remain locked until you approve the profile.
        </EmptyState>
      ) : profile.isError ? (
        <Notice>{errorMessage(profile.error)}</Notice>
      ) : profile.data && form ? (
        <>
          <section className="mb-5 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Current profile</h2>
                <p className="mt-1 text-sm text-slate-600">
                  {profile.data.source_file || "Uploaded PDF"} · Extracted {formatDate(profile.data.created_at)}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Extraction method: {profile.data.extraction_method || "Not specified"}
                </p>
              </div>
              <span className={`rounded-full px-3 py-1.5 text-sm font-semibold ${
                profile.data.approved
                  ? "bg-emerald-50 text-emerald-800"
                  : "bg-amber-50 text-amber-800"
              }`}>
                {profile.data.approved ? "Approved" : "Review required"}
              </span>
            </div>
            {profile.data.warnings.length > 0 && (
              <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
                <h3 className="text-sm font-semibold text-amber-900">Parser warnings</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">
                  {profile.data.warnings.map((warning, index) => <li key={`${warning}-${index}`}>{warning}</li>)}
                </ul>
              </div>
            )}
            {profile.data.skills_not_in_vocabulary.length > 0 && (
              <p className="mt-3 text-sm text-slate-700">
                Skills to verify: {profile.data.skills_not_in_vocabulary.join(", ")}
              </p>
            )}
          </section>

          <form className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6" onSubmit={saveProfile}>
            <h2 className="text-lg font-semibold">Review and edit extracted facts</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Use one item per line for list fields. Saving edits revokes any existing approval.
            </p>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {editableFields.map(({ key, label }) => (
                <label className={`block text-sm font-medium text-slate-700 ${key === "summary" ? "md:col-span-2" : ""}`} key={key}>
                  {label}
                  <textarea
                    className="mt-1.5 min-h-28 w-full rounded-lg border border-slate-300 p-3 text-sm leading-6 focus-visible:outline-2 focus-visible:outline-indigo-600"
                    onChange={(event) => updateField(key, event.target.value)}
                    value={toText(form[key])}
                  />
                </label>
              ))}
            </div>
            {edit.isError && <div className="mt-4"><Notice>{errorMessage(edit.error)}</Notice></div>}
            {approve.isError && <div className="mt-4"><Notice>{errorMessage(approve.error)}</Notice></div>}
            {recompute.isError && <div className="mt-4"><Notice>{errorMessage(recompute.error)}</Notice></div>}
            {edit.isSuccess && !profile.data.approved && (
              <p aria-live="polite" className="mt-3 text-sm text-amber-800">
                Profile changes saved. Review them and approve to enable matching and drafts.
              </p>
            )}
            <div className="mt-5 flex flex-wrap gap-3">
              <ActionButton disabled={edit.isPending} type="submit">
                {edit.isPending ? "Saving profile" : "Save profile edits"}
              </ActionButton>
              {!profile.data.approved && (
                <ActionButton disabled={approve.isPending} onClick={() => approve.mutate()}>
                  {approve.isPending ? "Approving" : "Approve profile"}
                </ActionButton>
              )}
              {profile.data.approved && (
                <ActionButton disabled={recompute.isPending} onClick={() => recompute.mutate()} variant="secondary">
                  {recompute.isPending ? "Comparing skills" : "Recompute skills overlap"}
                </ActionButton>
              )}
            </div>
            {recompute.isSuccess && (
              <p aria-live="polite" className="mt-3 text-sm text-slate-600">
                Skills overlap computed for {recompute.data.computed_jobs} active jobs.{" "}
                <Link className="font-semibold text-indigo-700 underline" href="/jobs">View jobs</Link>
              </p>
            )}
          </form>
        </>
      ) : null}
    </div>
  );
}
