import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const screenshotDirectory = resolve(process.cwd(), "../docs/screenshots");
mkdirSync(screenshotDirectory, { recursive: true });

const syntheticJob = {
  id: 9001,
  title: "Synthetic Backend Engineer",
  company: "Example Test Company",
  location: "Remote",
  description: "Synthetic test fixture. This is not a real job listing.",
  skills_mentioned: "Python, SQL",
  posted_date: "2026-01-15",
  apply_url: "https://jobs.example.test/roles/9001",
  source: "Example test board",
  first_seen_at: "2026-01-15T12:00:00Z",
  last_seen_at: "2026-01-15T12:00:00Z",
  is_active: true,
  skills_overlap: 75,
  matched_skills: ["Python"],
  missing_skills: ["SQL"],
};

const initialApplication = {
  id: 2001,
  job_id: 9001,
  status: "Interested",
  notes: "",
  created_at: "2026-01-15T12:00:00Z",
  updated_at: "2026-01-15T12:00:00Z",
  job: {
    title: syntheticJob.title,
    company: syntheticJob.company,
    location: syntheticJob.location,
    apply_url: syntheticJob.apply_url,
    source: syntheticJob.source,
  },
};

type ApplicationFixture = Omit<typeof initialApplication, "status"> & {
  status: string;
};

async function mockApi(page: Page) {
  let application: ApplicationFixture = { ...initialApplication };
  let statusUpdate: Record<string, unknown> | null = null;
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace(/^\/api/, "");
    if (path === "/health") {
      return route.fulfill({ json: { status: "ok" } });
    }
    if (path === "/jobs" && request.method() === "GET") {
      return route.fulfill({ json: [syntheticJob] });
    }
    if (path === "/applications" && request.method() === "GET") {
      return route.fulfill({ json: [application] });
    }
    if (path === "/applications/2001/events") {
      return route.fulfill({ json: [] });
    }
    if (path === "/applications/2001" && request.method() === "PATCH") {
      statusUpdate = request.postDataJSON() as Record<string, unknown>;
      application = {
        ...application,
        status: String(statusUpdate.status ?? application.status),
        notes: String(statusUpdate.note ?? application.notes),
      };
      return route.fulfill({ json: application });
    }
    if (path === "/resume") {
      return route.fulfill({
        json: {
          id: 505,
          source_file: "synthetic-test-fixture.pdf",
          extraction_method: "test fixture",
          summary: "",
          approved: true,
          approved_at: "2026-01-15T12:00:00Z",
          is_current: true,
          created_at: "2026-01-15T12:00:00Z",
          updated_at: "2026-01-15T12:00:00Z",
          skills: ["Python"],
          skills_not_in_vocabulary: [],
          projects: [],
          education_lines: [],
          degrees_detected: [],
          experience_lines: [],
          experience_date_ranges: [],
          warnings: [],
        },
      });
    }
    return route.fulfill({ status: 404, json: { detail: "Not found." } });
  });
  return {
    getStatusUpdate: () => statusUpdate,
  };
}

test("overview and jobs show the synthetic fixture and safe score explanation", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Your job search, in one place." })).toBeVisible();
  await page.screenshot({
    path: resolve(screenshotDirectory, "dashboard.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Use dark theme" }).click();
  await expect(page.locator('[data-theme="dark"]')).toHaveCSS(
    "background-color",
    "rgb(11, 18, 32)",
  );
  await page.getByRole("button", { name: "Use light theme" }).click();

  await page.getByRole("link", { name: "Jobs", exact: true }).click();
  await expect(page.getByRole("heading", { name: syntheticJob.title })).toBeVisible();
  await expect(
    page.getByText(
      "Skills overlap compares job skills with your approved resume. It is not a chance of being hired.",
    ).first(),
  ).toBeVisible();
  const posting = page.getByRole("link", { name: "View official posting" }).first();
  await expect(posting).toHaveAttribute("target", "_blank");
  await expect(posting).toHaveAttribute("rel", "noopener noreferrer");
  await page.screenshot({
    path: resolve(screenshotDirectory, "jobs-safety.png"),
    fullPage: true,
  });
});

test("Applied requires explicit employer-site confirmation", async ({ page }) => {
  const api = await mockApi(page);
  await page.goto("/applications");
  await expect(page.getByRole("heading", { name: syntheticJob.title })).toBeVisible();
  await page.getByLabel("Update status").selectOption("Applied");
  await page.getByRole("button", { name: "Update status" }).click();

  const dialog = page.getByRole("dialog", { name: "Confirm application submission" });
  await expect(dialog).toBeVisible();
  await page.screenshot({
    path: resolve(screenshotDirectory, "applied-confirmation.png"),
    fullPage: true,
  });
  expect(api.getStatusUpdate()).toBeNull();

  await dialog.getByLabel("I submitted this myself on the employer site").check();
  await dialog.getByRole("button", { name: "Confirm submitted" }).click();
  await expect.poll(api.getStatusUpdate).toEqual({
    status: "Applied",
    confirmed_by_user: true,
  });
  await expect(
    page.locator("article").getByText("Applied", { exact: true }).first(),
  ).toBeVisible();
});

test("mobile navigation opens and closes after selecting a page", async ({ page }) => {
  await mockApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Open navigation" }).click();
  const navigation = page.getByRole("navigation", { name: "Mobile navigation" });
  await expect(navigation.getByRole("link", { name: "Jobs", exact: true })).toBeVisible();
  await navigation.getByRole("link", { name: "Jobs", exact: true }).click();
  await expect(page).toHaveURL(/\/jobs$/);
  await expect(page.getByRole("button", { name: "Open navigation" })).toBeVisible();
});
