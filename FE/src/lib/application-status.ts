import type { ApplicationStatus } from "./schemas";

export type ApplicationStatusUpdate = {
  status: ApplicationStatus;
  confirmed_by_user?: true;
};

export function createStatusUpdate(
  current: ApplicationStatus,
  next: ApplicationStatus,
  confirmedByUser: boolean,
): ApplicationStatusUpdate | null {
  if (current === next) return null;
  if (next === "Applied") {
    return confirmedByUser
      ? { status: next, confirmed_by_user: true }
      : null;
  }
  return { status: next };
}
