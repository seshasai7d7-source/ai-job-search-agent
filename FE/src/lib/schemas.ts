import { z } from "zod";

export const HealthSchema = z.object({ status: z.string() });
export type Health = z.infer<typeof HealthSchema>;

export const JobSchema = z.object({
  id: z.number(),
  title: z.string(),
  company: z.string(),
  location: z.string(),
  description: z.string(),
  skills_mentioned: z.string(),
  posted_date: z.string(),
  apply_url: z.string(),
  source: z.string(),
  first_seen_at: z.string(),
  last_seen_at: z.string(),
  is_active: z.boolean(),
  skills_overlap: z.number().nullable(),
  matched_skills: z.array(z.string()),
  missing_skills: z.array(z.string()),
});
export type Job = z.infer<typeof JobSchema>;

export const ApplicationStatusSchema = z.enum([
  "Interested",
  "Application Prepared",
  "Applied",
  "Interview",
  "Offer",
  "Rejected",
]);
export type ApplicationStatus = z.infer<typeof ApplicationStatusSchema>;

export const ApplicationSchema = z.object({
  id: z.number(),
  job_id: z.number(),
  status: ApplicationStatusSchema,
  notes: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  job: z.object({
    title: z.string(),
    company: z.string(),
    location: z.string(),
    apply_url: z.string(),
    source: z.string(),
  }),
});
export type Application = z.infer<typeof ApplicationSchema>;

export const ApplicationEventSchema = z.object({
  id: z.number(),
  from_status: z.string(),
  to_status: z.string(),
  confirmed_by_user: z.boolean(),
  note: z.string(),
  created_at: z.string(),
});

export const ResumeProfileSchema = z.object({
  id: z.number(),
  source_file: z.string(),
  extraction_method: z.string(),
  summary: z.string(),
  approved: z.boolean(),
  approved_at: z.string().nullable(),
  is_current: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
  skills: z.array(z.string()),
  skills_not_in_vocabulary: z.array(z.string()),
  projects: z.array(z.string()),
  education_lines: z.array(z.string()),
  degrees_detected: z.array(z.string()),
  experience_lines: z.array(z.string()),
  experience_date_ranges: z.array(z.string()),
  warnings: z.array(z.string()),
});
export type ResumeProfile = z.infer<typeof ResumeProfileSchema>;

export const SearchRunSchema = z.object({
  id: z.number(),
  started_at: z.string(),
  finished_at: z.string().nullable(),
  status: z.string(),
  new_jobs: z.number(),
  per_source_results: z.record(
    z.string(),
    z.object({
      fetched: z.number(),
      kept: z.number(),
      new_jobs: z.number(),
      error: z.string().nullable(),
    }),
  ).optional(),
});
export type SearchRun = z.infer<typeof SearchRunSchema>;

export const SearchRunCreatedSchema = z.object({
  id: z.number(),
  status: z.string(),
});

export const DraftSchema = z.object({
  id: z.number(),
  job_id: z.number(),
  kind: z.enum(["cover_letter", "answer"]),
  question: z.string().nullable(),
  body: z.string(),
  status: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type Draft = z.infer<typeof DraftSchema>;
