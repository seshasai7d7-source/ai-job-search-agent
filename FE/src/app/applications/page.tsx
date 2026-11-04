"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ActionButton,
  EmptyState,
  LoadingState,
  Notice,
  PageHeading,
  SafeApplyLink,
} from "@/components/ui";
import { api } from "@/lib/api";
import { createStatusUpdate } from "@/lib/application-status";
import { errorMessage, formatDate } from "@/lib/presentation";
import {
  ApplicationEventSchema,
  ApplicationSchema,
  ApplicationStatusSchema,
} from "@/lib/schemas";
import type { Application, ApplicationStatus } from "@/lib/schemas";
import { z } from "zod";

const ApplicationsSchema = z.array(ApplicationSchema);
const EventsSchema = z.array(ApplicationEventSchema);
const statusChoices = ApplicationStatusSchema.options;

function ApplicationCard({ application }: { application: Application }) {
  const queryClient = useQueryClient();
  const [note, setNote] = useState(application.notes);
  const [nextStatus, setNextStatus] = useState<ApplicationStatus>(application.status);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [confirmedByUser, setConfirmedByUser] = useState(false);
  const [showEvents, setShowEvents] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const update = useMutation({
    mutationFn: (body: { status?: ApplicationStatus; note?: string; confirmed_by_user?: true }) =>
      api(`/applications/${application.id}`, ApplicationSchema, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: async (updated) => {
      setNote(updated.notes);
      setNextStatus(updated.status);
      setShowConfirmation(false);
      setConfirmedByUser(false);
      await queryClient.invalidateQueries({ queryKey: ["applications"] });
      await queryClient.invalidateQueries({ queryKey: ["application-events", application.id] });
    },
  });
  const events = useQuery({
    queryKey: ["application-events", application.id],
    queryFn: () => api(`/applications/${application.id}/events`, EventsSchema),
    enabled: showEvents,
  });
  useEffect(() => {
    const dialog = dialogRef.current;
    if (showConfirmation && dialog && !dialog.open) dialog.showModal();
  }, [showConfirmation]);

  function requestStatusChange() {
    if (nextStatus === "Applied") {
      setConfirmedByUser(false);
      setShowConfirmation(true);
      return;
    }
    const body = createStatusUpdate(application.status, nextStatus, false);
    if (body) update.mutate(body);
  }

  function confirmApplied() {
    if (!confirmedByUser) return;
    const body = createStatusUpdate(application.status, "Applied", confirmedByUser);
    if (body) update.mutate(body);
  }

  function saveNote() {
    update.mutate({ note });
  }

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">
            <Link className="hover:text-indigo-700" href={`/jobs/${application.job_id}`}>
              {application.job.title}
            </Link>
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {application.job.company} · {application.job.location || "Location not listed"}
          </p>
        </div>
        <span className="rounded-full bg-indigo-50 px-3 py-1.5 text-sm font-semibold text-indigo-800">
          {application.status}
        </span>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-4">
        <SafeApplyLink value={application.job.apply_url} />
        <span className="text-xs text-slate-500">Updated {formatDate(application.updated_at)}</span>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-end">
        <label className="text-sm font-medium text-slate-700">
          Update status
          <select
            className="mt-1.5 min-h-10 w-full rounded-lg border border-slate-300 bg-white px-3"
            onChange={(event) =>
              setNextStatus(ApplicationStatusSchema.parse(event.target.value))
            }
            value={nextStatus}
          >
            {statusChoices.map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
        </label>
        <ActionButton
          disabled={update.isPending || nextStatus === application.status}
          onClick={requestStatusChange}
        >
          {update.isPending ? "Updating" : "Update status"}
        </ActionButton>
        <ActionButton onClick={() => setShowEvents((visible) => !visible)} variant="secondary">
          {showEvents ? "Hide history" : "View history"}
        </ActionButton>
      </div>
      <label className="mt-4 block text-sm font-medium text-slate-700">
        Private notes
        <textarea
          className="mt-1.5 min-h-24 w-full rounded-lg border border-slate-300 p-3 text-sm leading-6"
          onChange={(event) => setNote(event.target.value)}
          value={note}
        />
      </label>
      <div className="mt-2 flex items-center gap-3">
        <ActionButton
          disabled={update.isPending || note === application.notes}
          onClick={saveNote}
          variant="secondary"
        >
          {update.isPending ? "Saving" : "Save notes"}
        </ActionButton>
      </div>
      {update.isError && <div className="mt-3"><Notice>{errorMessage(update.error)}</Notice></div>}
      {update.isSuccess && (
        <p aria-live="polite" className="mt-2 text-sm text-emerald-700">Changes saved.</p>
      )}

      {showConfirmation && (
        <dialog
          ref={dialogRef}
          aria-labelledby={`applied-title-${application.id}`}
          aria-modal="true"
          className="fixed inset-0 z-50 m-auto w-[min(92vw,480px)] rounded-2xl border border-slate-200 bg-white p-0 text-left shadow-2xl backdrop:bg-slate-950/40"
          onCancel={(event) => {
            event.preventDefault();
            setShowConfirmation(false);
          }}
        >
          <div className="p-6">
            <h2 className="text-lg font-semibold" id={`applied-title-${application.id}`}>
              Confirm application submission
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              This tracker does not submit applications. Open the employer&apos;s official site and submit there first.
            </p>
            <SafeApplyLink value={application.job.apply_url} />
            <label className="mt-5 flex items-start gap-3 text-sm leading-6 text-slate-800">
              <input
                autoFocus
                checked={confirmedByUser}
                className="mt-1 size-4 accent-indigo-700"
                onChange={(event) => setConfirmedByUser(event.target.checked)}
                type="checkbox"
              />
              <span>I submitted this myself on the employer site</span>
            </label>
            <div className="mt-6 flex justify-end gap-2">
              <ActionButton onClick={() => setShowConfirmation(false)} variant="secondary">
                Cancel
              </ActionButton>
              <ActionButton disabled={!confirmedByUser || update.isPending} onClick={confirmApplied}>
                Confirm submitted
              </ActionButton>
            </div>
          </div>
        </dialog>
      )}

      {showEvents && (
        <section aria-label={`Application history for ${application.job.title}`} className="mt-5 border-t border-slate-100 pt-4">
          <h3 className="font-semibold text-slate-900">Status history</h3>
          {events.isPending ? (
            <p className="mt-2 text-sm text-slate-500">Loading event history…</p>
          ) : events.isError ? (
            <p className="mt-2 text-sm text-rose-700">{errorMessage(events.error)}</p>
          ) : events.data.length === 0 ? (
            <p className="mt-2 text-sm text-slate-600">No status changes recorded yet.</p>
          ) : (
            <ol className="mt-3 space-y-3">
              {events.data.map((event) => (
                <li className="border-l-2 border-indigo-200 pl-3 text-sm" key={event.id}>
                  <p className="font-medium text-slate-800">{event.from_status || "Created"} → {event.to_status}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {formatDate(event.created_at)}
                    {event.confirmed_by_user ? " · Confirmed by you" : ""}
                  </p>
                  {event.note && <p className="mt-1 text-slate-600">{event.note}</p>}
                </li>
              ))}
            </ol>
          )}
        </section>
      )}
    </article>
  );
}

function ApplicationsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const status = searchParams.get("status") ?? "";
  const applications = useQuery({
    queryKey: ["applications", status],
    queryFn: () =>
      api(
        `/applications${status ? `?status=${encodeURIComponent(status)}` : ""}`,
        ApplicationsSchema,
      ),
  });

  function updateFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const selected = String(formData.get("status") ?? "");
    router.replace(`/applications${selected ? `?status=${encodeURIComponent(selected)}` : ""}`);
  }

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeading
        eyebrow="Your decisions"
        title="Applications"
        description="Track application status, notes, and history. The agent never submits applications."
      />
      <form className="mb-5 flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4" onSubmit={updateFilter}>
        <label className="text-sm font-medium text-slate-700">
          Filter by status
          <select
            className="mt-1.5 block min-h-10 rounded-lg border border-slate-300 bg-white px-3"
            defaultValue={status}
            name="status"
          >
            <option value="">All statuses</option>
            {statusChoices.map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </label>
        <ActionButton type="submit" variant="secondary">Apply filter</ActionButton>
      </form>
      {applications.isPending ? (
        <LoadingState label="Loading applications" />
      ) : applications.isError ? (
        <Notice>{errorMessage(applications.error)}</Notice>
      ) : applications.data.length === 0 ? (
        <EmptyState title="No tracked applications">
          Add a job to the tracker from its details page. Tracker entries are created as Interested.
        </EmptyState>
      ) : (
        <div className="space-y-4">
          {applications.data.map((application) => (
            <ApplicationCard application={application} key={application.id} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function ApplicationsPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading application filters" />}>
      <ApplicationsContent />
    </Suspense>
  );
}
