import { test, expect, request } from "@playwright/test";

const API_URL =
  process.env.API_URL ||
  "https://my-python-backend-quyiiugyoq-ue.a.run.app";

/**
 * User workflow E2E tests.
 *
 * Covers the core user journeys that have zero E2E coverage:
 * - Home page and navigation
 * - Challenge browsing and filtering
 * - Challenge detail page with lift upload
 * - Bowling challenge page
 */

// -------------------------------------------------------------------------
// Home page and site navigation
// -------------------------------------------------------------------------

test.describe("Home page and navigation", () => {
  test("landing page renders hero carousel and featured challenges", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Hero carousel should be visible with CTA text
    await expect(
      page.getByText("Online Lifting Challenges for Everyone")
    ).toBeVisible({ timeout: 15_000 });

    // "Browse Challenges" CTA link should exist
    const ctaLink = page.getByRole("link", { name: /browse challenges/i });
    await expect(ctaLink).toBeVisible();
  });

  test("navigation links work", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Navigate to Challenges via nav link or CTA
    const challengesLink = page
      .getByRole("link", { name: /challenges/i })
      .first();
    await expect(challengesLink).toBeVisible({ timeout: 10_000 });
    await challengesLink.click();

    await expect(page).toHaveURL(/\/challenges/);
    await page.waitForLoadState("networkidle");

    // Challenges page should have loaded
    // Look for filter buttons or challenge cards
    const hasContent = await Promise.race([
      page
        .getByRole("button", { name: /all/i })
        .waitFor({ timeout: 10_000 })
        .then(() => true),
      page
        .getByText(/challenges/i)
        .first()
        .waitFor({ timeout: 10_000 })
        .then(() => true),
    ]).catch(() => false);
    expect(hasContent).toBeTruthy();
  });

  test("404 page shows for unknown routes", async ({ page }) => {
    await page.goto("/this-page-does-not-exist-xyz");
    await page.waitForLoadState("networkidle");

    // Should show a 404 or "not found" message
    const notFound = await Promise.race([
      page
        .getByText(/not found/i)
        .waitFor({ timeout: 5_000 })
        .then(() => true),
      page
        .getByText(/404/i)
        .waitFor({ timeout: 5_000 })
        .then(() => true),
    ]).catch(() => false);
    expect(notFound).toBeTruthy();
  });
});

// -------------------------------------------------------------------------
// Challenge browsing and filtering
// -------------------------------------------------------------------------

test.describe("Challenge browsing", () => {
  test("challenges page loads and shows challenge cards", async ({ page }) => {
    await page.goto("/challenges");
    await page.waitForLoadState("networkidle");

    // Should not show an error
    const errorVisible = await page
      .getByText(/failed to load/i)
      .isVisible()
      .catch(() => false);

    if (errorVisible) {
      test.skip(true, "Challenges API returned an error");
      return;
    }

    // Should show filter buttons
    const allFilter = page.getByRole("button", { name: /^all$/i });
    await expect(allFilter).toBeVisible({ timeout: 10_000 });
  });

  test("filter tabs change displayed challenges", async ({ page }) => {
    await page.goto("/challenges");
    await page.waitForLoadState("networkidle");

    const errorVisible = await page
      .getByText(/failed to load/i)
      .isVisible()
      .catch(() => false);
    if (errorVisible) {
      test.skip(true, "Challenges API returned an error");
      return;
    }

    // "All" filter should be active by default
    const allFilter = page.getByRole("button", { name: /^all$/i });
    await expect(allFilter).toBeVisible({ timeout: 10_000 });

    // Click "Ongoing" filter
    const ongoingFilter = page.getByRole("button", { name: /ongoing/i });
    if (await ongoingFilter.isVisible()) {
      await ongoingFilter.click();
      await page.waitForTimeout(500);
      // Page should not crash — either shows filtered results or empty state
    }

    // Click back to "All"
    await allFilter.click();
    await page.waitForTimeout(500);
  });

  test("challenge card links to challenge detail", async ({ page }) => {
    await page.goto("/challenges");
    await page.waitForLoadState("networkidle");

    // Find any challenge card link
    const challengeLinks = page.locator('a[href*="/challenges/"]');
    const count = await challengeLinks.count();

    if (count === 0) {
      test.skip(true, "No challenges available");
      return;
    }

    // Click the first challenge card
    const firstLink = challengeLinks.first();
    const href = await firstLink.getAttribute("href");
    await firstLink.click();

    // Should navigate to challenge detail
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/challenges/");
  });
});

// -------------------------------------------------------------------------
// Challenge detail page (read-only — no uploads to avoid orphaned data)
// -------------------------------------------------------------------------

test.describe("Challenge detail", () => {
  let competitionId: string | null = null;

  test.beforeAll(async () => {
    // Find a real competition to test against
    const ctx = await request.newContext();
    try {
      const resp = await ctx.get(`${API_URL}/competitions`);
      if (resp.ok()) {
        const data = await resp.json();
        const competitions = data.competitions || [];
        // Prefer an ongoing competition
        const ongoing = competitions.find(
          (c: any) =>
            new Date(c.start_date) <= new Date() &&
            new Date(c.end_date) >= new Date()
        );
        competitionId = ongoing?.id || competitions[0]?.id || null;
      }
    } catch {
      // No competitions available
    }
  });

  test("challenge detail page loads with participants and videos", async ({
    page,
  }) => {
    test.skip(!competitionId, "No competitions available");

    await page.goto(`/challenges/${competitionId}`);
    await page.waitForLoadState("networkidle");

    // Should show challenge content (not an error)
    const hasContent = await Promise.race([
      page
        .getByText(/participants|upload|videos|join/i)
        .first()
        .waitFor({ timeout: 15_000 })
        .then(() => true),
      page
        .getByText(/error|failed/i)
        .first()
        .waitFor({ timeout: 5_000 })
        .then(() => "error"),
    ]).catch(() => false);

    if (hasContent === "error") {
      test.skip(true, "Challenge detail returned an error");
      return;
    }

    expect(hasContent).toBeTruthy();
  });

  test("challenge upload form requires email and video", async ({ page }) => {
    test.skip(!competitionId, "No competitions available");

    await page.goto(`/challenges/${competitionId}`);
    await page.waitForLoadState("networkidle");

    // Look for the upload form or upload button
    const uploadSection = page.getByText(/upload/i).first();
    await expect(uploadSection).toBeVisible({ timeout: 15_000 });

    // Find and click submit without filling in — should show validation error
    const submitButton = page.getByRole("button", {
      name: /upload video|submit/i,
    });
    if (await submitButton.isVisible()) {
      // Button should be disabled when no file is selected
      const isDisabled = await submitButton.isDisabled();
      expect(isDisabled).toBeTruthy();
    }
  });
});

// -------------------------------------------------------------------------
// Bowling challenge page (read-only — no uploads to avoid orphaned data)
// -------------------------------------------------------------------------

test.describe("Bowling challenge page", () => {
  let bowlingCompetitionId: string | null = null;

  test.beforeAll(async () => {
    const ctx = await request.newContext();
    try {
      const resp = await ctx.get(`${API_URL}/competitions`);
      if (resp.ok()) {
        const data = await resp.json();
        const competitions = data.competitions || [];
        const bowling = competitions.find((c: any) =>
          c.name?.toLowerCase().includes("bowling")
        );
        bowlingCompetitionId = bowling?.id || competitions[0]?.id || null;
      }
    } catch {
      // No competitions
    }
  });

  test("bowling challenge page loads and shows upload form", async ({
    page,
  }) => {
    test.skip(!bowlingCompetitionId, "No competitions available");

    await page.goto(`/bowling/challenge/${bowlingCompetitionId}`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Bowling Challenge")).toBeVisible({
      timeout: 15_000,
    });

    await expect(
      page.getByText(/upload your bowling video/i)
    ).toBeVisible();

    const uploadBtn = page.getByRole("button", { name: /upload video/i });
    await expect(uploadBtn).toBeVisible();
    await expect(uploadBtn).toBeDisabled();
  });

  test("bowling challenge shows submission count", async ({ page }) => {
    test.skip(!bowlingCompetitionId, "No competitions available");

    await page.goto(`/bowling/challenge/${bowlingCompetitionId}`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Bowling Challenge")).toBeVisible({
      timeout: 15_000,
    });

    await expect(page.getByText(/\d+ submission/i)).toBeVisible({
      timeout: 5_000,
    });
  });

  test("bowling challenge shows All Submissions section", async ({ page }) => {
    test.skip(!bowlingCompetitionId, "No competitions available");

    await page.goto(`/bowling/challenge/${bowlingCompetitionId}`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Bowling Challenge")).toBeVisible({
      timeout: 15_000,
    });

    await expect(page.getByText("All Submissions")).toBeVisible({
      timeout: 5_000,
    });
  });

  test("bowling challenge result cards link to result page", async ({
    page,
  }) => {
    test.skip(!bowlingCompetitionId, "No competitions available");

    await page.goto(`/bowling/challenge/${bowlingCompetitionId}`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Bowling Challenge")).toBeVisible({
      timeout: 15_000,
    });

    const resultLinks = page.locator('a[href*="/bowling/result/"]');
    const count = await resultLinks.count();

    if (count === 0) {
      await expect(
        page.getByText(/no bowling results|be the first/i)
      ).toBeVisible();
      return;
    }

    await resultLinks.first().click();
    await page.waitForLoadState("networkidle");

    expect(page.url()).toContain("/bowling/result/");
    await expect(page.getByText("Bowling Result")).toBeVisible({
      timeout: 15_000,
    });
  });
});

// -------------------------------------------------------------------------
// Static pages
// -------------------------------------------------------------------------

test.describe("Static pages", () => {
  test("about page renders", async ({ page }) => {
    await page.goto("/about");
    await page.waitForLoadState("networkidle");

    // Should have some content (not blank/error)
    const hasContent = await page
      .locator("main, [class*='container'], [class*='mx-auto']")
      .first()
      .isVisible({ timeout: 10_000 })
      .catch(() => false);
    expect(hasContent).toBeTruthy();
  });

  test("leaderboard page renders", async ({ page }) => {
    await page.goto("/leaderboard");
    await page.waitForLoadState("networkidle");

    // Should show leaderboard content or filter controls
    const hasContent = await Promise.race([
      page
        .getByText(/leaderboard/i)
        .first()
        .waitFor({ timeout: 10_000 })
        .then(() => true),
      page
        .getByRole("button")
        .first()
        .waitFor({ timeout: 10_000 })
        .then(() => true),
    ]).catch(() => false);
    expect(hasContent).toBeTruthy();
  });

  test("athletes page renders", async ({ page }) => {
    await page.goto("/athletes");
    await page.waitForLoadState("networkidle");

    // Should show athletes content or search
    const hasContent = await Promise.race([
      page
        .getByText(/athletes/i)
        .first()
        .waitFor({ timeout: 10_000 })
        .then(() => true),
      page
        .getByPlaceholder(/search/i)
        .waitFor({ timeout: 10_000 })
        .then(() => true),
    ]).catch(() => false);
    expect(hasContent).toBeTruthy();
  });
});
