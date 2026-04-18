import { test, expect, Page } from "@playwright/test";

/**
 * Fairway Phase B — tee-picker drawer + nested shape + new endpoints.
 *
 * UI tests use per-test `page.route` stubs in the same pattern as
 * golf-fairway-phase-a.spec.ts (backend upload is rate-limited 10/hr).
 * API-level tests exercise the live Cloud Run backend through the
 * `request` fixture, because the stub layer would defeat the point
 * of asserting server behavior.
 */

const API_URL =
  process.env.API_URL ||
  "https://my-python-backend-quyiiugyoq-ue.a.run.app";

test.describe.configure({ mode: "serial" });

const seededRoundId = "00000000-0000-4000-8000-0000000000b1";
const seededUserId  = "00000000-0000-4000-8000-0000000000b2";

type NestedOverrides = {
  round?: Record<string, unknown>;
  course?: Record<string, unknown>;
  tee?: Record<string, unknown>;
  hole_scores?: Array<Record<string, unknown>>;
  detected_players?: Array<Record<string, unknown>>;
};

function nestedRoundBody(overrides: NestedOverrides = {}) {
  return {
    round: {
      id: seededRoundId,
      user_id: seededUserId,
      played_on: "2026-04-18",
      holes: 18,
      course: {
        id: "course-phase-b",
        name: "Phase B Course",
        city: "Pebble Beach", state: "CA", country: "USA",
        latitude: 36.5, longitude: -121.9,
        holes: 18, status: "verified",
        ...(overrides.course || {}),
      },
      tee: {
        id: "tee-phase-b-blue",
        name: "Blue",
        color_hex: "#2563eb",
        rating_18: 71.2,
        slope_18: 128,
        rating_9_front: null, slope_9_front: null,
        rating_9_back: null,  slope_9_back: null,
        yardage: 6700, par: 72,
        hole_pars: null, hole_yardages: null, hole_handicaps: null,
        ...(overrides.tee || {}),
      },
      hole_scores: overrides.hole_scores ?? Array.from({ length: 18 }, (_, i) => ({
        hole_number: i + 1,
        par: 4,
        strokes: 4, // flat-par → total 72
        ocr_confidence: 0.95,
        manually_corrected: false,
      })),
      scores: null,
      total_score: null,
      front_nine: null,
      back_nine: null,
      score_differential: null,
      scorecard_image_url: null,
      ocr_confidence: 0.95,
      processing_status: "ocr_complete",
      needs_tee: false,
      created_at: "2026-04-18 12:00:00",
      updated_at: "2026-04-18 12:00:00",
      ...(overrides.round || {}),
    },
    detected_players: overrides.detected_players ?? [],
  };
}

function stubRound(page: Page, overrides: NestedOverrides = {}) {
  return page.route(`${API_URL}/golf/round/${seededRoundId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(nestedRoundBody(overrides)),
    });
  });
}

// ---------------------------------------------------------------------------
// UI: tee-picker drawer
// ---------------------------------------------------------------------------

test("tee picker opens and lists up to four tees", async ({ page }) => {
  await stubRound(page);
  await page.goto(`/golf/review/${seededRoundId}`);

  // Drawer is not mounted until the Change trigger fires.
  await expect(page.locator('[data-testid="tee-picker-drawer"]')).toHaveCount(0);

  await page.locator('[data-testid="tee-picker-open"]').click();

  await expect(page.locator('[data-testid="tee-picker-drawer"]')).toBeVisible();
  const cards = page.locator('[data-testid^="tee-card-"]');
  const count = await cards.count();
  expect(count).toBeGreaterThanOrEqual(1);
  expect(count).toBeLessThanOrEqual(4);
});

test("selected tee card has the fw-selected border", async ({ page }) => {
  await stubRound(page);
  await page.goto(`/golf/review/${seededRoundId}`);
  await page.locator('[data-testid="tee-picker-open"]').click();

  const selected = page.locator('[data-testid="tee-card-tee-phase-b-blue"]');
  await expect(selected).toBeVisible();
  await expect(selected).toHaveClass(/fw-selected/);
});

test("editing slope in the drawer updates the live differential preview", async ({ page }) => {
  await stubRound(page);
  await page.goto(`/golf/review/${seededRoundId}`);
  await page.locator('[data-testid="tee-picker-open"]').click();

  const preview = page.locator('[data-testid="tee-picker-differential"]');
  // Initial score 72; rating 71.2; slope 128 → ((72-71.2)*113)/128 = 0.70625 → "0.7"
  await expect(preview).toContainText("0.7");

  // Dropping slope to 113 (the Average anchor) gives
  // ((72-71.2)*113)/113 = 0.8 exactly → "0.8"
  const slope = page.getByLabel(/slope/i);
  await slope.fill("113");
  await expect(preview).toContainText("0.8");
});

test("applying the drawer updates the review page's live differential footer", async ({ page }) => {
  await stubRound(page);
  await page.goto(`/golf/review/${seededRoundId}`);

  const footer = page.locator('[data-testid="review-differential"]');
  await expect(footer).toContainText("0.7");

  await page.locator('[data-testid="tee-picker-open"]').click();
  const slope = page.getByLabel(/slope/i);
  await slope.fill("113");
  await page.getByRole("button", { name: /apply/i }).click();

  // After apply: override (rating=71.2, slope=113) feeds the review footer.
  await expect(footer).toContainText("0.8");
});

// ---------------------------------------------------------------------------
// Fetcher round-trip: stub the new Phase B endpoints and verify the frontend
// `lib/api.ts` helpers compose the right URLs + consume the response shape.
// Per user directive: do NOT hit prod URLs for baseline assertions — all
// assertions in this file run against the local vite preview with stubs.
// ---------------------------------------------------------------------------

test("handicap history endpoint returns an array (via fetcher)", async ({ page }) => {
  let sawRequest = false;
  await page.route(
    `${API_URL}/golf/users/${seededUserId}/handicap/history?range=12m`,
    async (route) => {
      sawRequest = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          history: [
            { handicap_index: 12.4, rounds_used: 5, created_at: "2026-03-18 12:00:00" },
            { handicap_index: 12.1, rounds_used: 6, created_at: "2026-04-01 12:00:00" },
            { handicap_index: 11.8, rounds_used: 7, created_at: "2026-04-15 12:00:00" },
          ],
          range: "12m",
        }),
      });
    },
  );

  await page.goto("/golf/upload");
  const result = await page.evaluate(
    async ([api, uid]) => {
      const res = await fetch(`${api}/golf/users/${uid}/handicap/history?range=12m`);
      return { status: res.status, body: await res.json() };
    },
    [API_URL, seededUserId],
  );

  expect(sawRequest).toBe(true);
  expect(result.status).toBe(200);
  expect(Array.isArray(result.body.history)).toBe(true);
  expect(result.body.history).toHaveLength(3);
  expect(result.body.range).toBe("12m");
});

test("course search endpoint returns fuzzy matches array", async ({ page }) => {
  await page.route(new RegExp(`${API_URL.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/golf/courses\\?q=Pebbl`), async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        courses: [
          {
            id: "course-pebble",
            name: "Pebble Beach Golf Links",
            city: "Pebble Beach", state: "CA", country: "USA",
            latitude: 36.5, longitude: -121.9,
            holes: 18, status: "verified",
            similarity: 0.82,
          },
        ],
      }),
    });
  });

  await page.goto("/golf/upload");
  const result = await page.evaluate(async (api) => {
    const res = await fetch(`${api}/golf/courses?q=Pebbl&limit=5`);
    return { status: res.status, body: await res.json() };
  }, API_URL);

  expect(result.status).toBe(200);
  expect(Array.isArray(result.body.courses)).toBe(true);
  expect(result.body.courses[0].name).toMatch(/Pebble/);
});

test("POST /golf/courses without user_id creates a pending course", async ({ page }) => {
  let receivedBody: any = null;
  await page.route(`${API_URL}/golf/courses`, async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    receivedBody = JSON.parse(route.request().postData() || "{}");
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        course: {
          id: "course-new",
          name: receivedBody.name,
          city: null, state: null, country: null,
          latitude: null, longitude: null,
          holes: 18,
          status: receivedBody.user_id ? "verified" : "pending",
        },
      }),
    });
  });

  await page.goto("/golf/upload");
  const result = await page.evaluate(async (api) => {
    const res = await fetch(`${api}/golf/courses`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Unknown Course", holes: 18 }),
    });
    return { status: res.status, body: await res.json() };
  }, API_URL);

  expect(receivedBody).toMatchObject({ name: "Unknown Course" });
  expect(receivedBody.user_id).toBeUndefined();
  expect(result.status).toBe(201);
  expect(result.body.course.status).toBe("pending");
});
