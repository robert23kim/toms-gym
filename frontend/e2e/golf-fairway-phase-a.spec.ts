import { test, expect, Page } from "@playwright/test";

/**
 * Fairway Phase A — visual + UX polish smoke test.
 *
 * Backend is stubbed per-test (the `/golf/upload` route is rate-limited
 * 10/hr in prod, so we can't realistically seed a fresh round on every
 * run). Tests that need a specific round/profile/leaderboard response
 * use `page.route` to serve deterministic JSON.
 *
 * Stub URLs target API_URL explicitly so the glob does NOT match the
 * frontend SPA navigation at the same path (e.g. `/golf/round/<id>`).
 */

const API_URL =
  process.env.API_URL ||
  "https://my-python-backend-quyiiugyoq-ue.a.run.app";

test.describe.configure({ mode: "serial" });

// Deterministic IDs used across tests.
const seededRoundId = "00000000-0000-4000-8000-000000000001";
const seededUserId  = "00000000-0000-4000-8000-000000000002";

function stubSeededRound(page: Page, overrides: Record<string, unknown> = {}) {
  return page.route(`${API_URL}/golf/round/${seededRoundId}`, async (route) => {
    const body = {
      id: seededRoundId,
      user_id: seededUserId,
      course_name: "Phase A Course",
      slope_rating: 128,
      course_rating: 71.2,
      adjusted_gross_score: null,
      differential: null,
      scorecard_image_url: null,
      ocr_confidence: 0.95,
      processing_status: "ocr_complete",
      played_at: "2026-04-18",
      holes: Array.from({ length: 18 }, (_, i) => ({
        hole_number: i + 1,
        par: 4,
        strokes: null,
        ocr_confidence: 0.99,
      })),
      detected_players: [],
      ...overrides,
    };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
}

function stubProfile(page: Page) {
  return Promise.all([
    page.route(`${API_URL}/golf/rounds?user_id=${seededUserId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ rounds: [], handicap_index: null }),
      });
    }),
    page.route(`${API_URL}/users/${seededUserId}/profile`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: seededUserId, name: "Phase A Golfer", email: "" }),
      });
    }),
  ]);
}

function stubLeaderboard(page: Page) {
  return page.route(new RegExp(`${API_URL.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\\\$&")}/golf/leaderboard`), async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        leaderboard: [
          {
            rank: 1,
            user_id: seededUserId,
            user_name: "Phase A Golfer",
            handicap_index: 12.4,
            rounds_played: 5,
            best_differential: 9.1,
          },
        ],
      }),
    });
  });
}

test("golf upload page is wrapped in fw-scope", async ({ page }) => {
  await page.goto("/golf/upload");
  const scope = page.locator(".fw-scope").first();
  await expect(scope).toBeVisible();
});

test("golf upload shows Fairway header, alignment guides, and two CTAs", async ({ page }) => {
  await page.goto("/golf/upload");
  await expect(page.locator(".fw-h1", { hasText: "Log round" })).toBeVisible();
  await expect(page.locator(".fw-corner-guides")).toBeVisible();
  await expect(page.getByRole("button", { name: /capture photo/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /upload from library/i })).toBeVisible();
  await expect(page.getByText(/lay flat, fill frame, avoid glare/i)).toBeVisible();
});

test("staged parse progress shows 5 tasks during upload", async ({ page }) => {
  await page.goto("/golf/upload");

  // Stall the upload POST ~3s so the staged UI animates fully.
  await page.route("**/golf/upload", async (route) => {
    await new Promise((r) => setTimeout(r, 3000));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ round_id: "stub-round-id", user_id: "stub-user-id" }),
    });
  });

  await page.fill('input[type="email"]', "fairway-smoke@test.com").catch(() => {});
  await page.fill('input[placeholder*="Pebble Beach" i]', "Smoke Course");
  await page.setInputFiles("#golf-scorecard-upload", "e2e/fixtures/scorecard-test.jpg");
  await page.getByRole("button", { name: /analyse scorecard/i }).click();

  for (const label of [
    "Detecting layout",
    "Identifying course",
    "Reading par and yardage",
    "Extracting player scores",
    "Flagging low-confidence holes",
  ]) {
    await expect(page.getByText(label)).toBeVisible({ timeout: 3500 });
  }
});

test("review cells use Fairway color semantics vs par", async ({ page }) => {
  await stubSeededRound(page);
  await page.goto(`/golf/review/${seededRoundId}`);

  // Find at least one hole input. Because the seeded round is from a tiny
  // test image the OCR will produce no scores, so we'll type a known value
  // and assert the class changes accordingly.
  const firstCell = page.locator('[data-testid="scorecard-cell-1"]');
  await expect(firstCell).toBeVisible();

  // Click to edit, enter a birdie (par 4 → stroke 3)
  await firstCell.click();
  await page.keyboard.type("3");
  await page.keyboard.press("Enter");
  await expect(firstCell).toHaveClass(/fw-cell-birdie/);

  // Enter a par
  await firstCell.click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.type("4");
  await page.keyboard.press("Enter");
  await expect(firstCell).toHaveClass(/fw-cell-par/);

  // Enter a bogey
  await firstCell.click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.type("5");
  await page.keyboard.press("Enter");
  await expect(firstCell).toHaveClass(/fw-cell-bogey-plus/);
});

test("low-confidence cells get the fw-cell-needs-review glow", async ({ page }) => {
  // Stub the round fetch so hole 3 is low-confidence and holes 1-2 are not.
  await page.route(`${API_URL}/golf/round/${seededRoundId}`, async (route) => {
    const body = {
      id: seededRoundId,
      user_id: "stub-user",
      course_name: "Stub Course",
      slope_rating: 128,
      course_rating: 71.2,
      adjusted_gross_score: null,
      differential: null,
      scorecard_image_url: null,
      ocr_confidence: 0.5,
      processing_status: "ocr_complete",
      played_at: "2026-04-18",
      holes: Array.from({ length: 18 }, (_, i) => ({
        hole_number: i + 1,
        par: 4,
        strokes: i === 2 ? 4 : null,
        ocr_confidence: i === 2 ? 0.5 : 0.99,
      })),
      detected_players: [],
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto(`/golf/review/${seededRoundId}`);
  await expect(page.locator('[data-testid="scorecard-cell-3"]')).toHaveClass(/fw-cell-needs-review/);
  await expect(page.locator('[data-testid="scorecard-cell-1"]')).not.toHaveClass(/fw-cell-needs-review/);

  // The old AlertTriangle icon should be gone.
  await expect(page.locator('[data-testid="scorecard-cell-3"] svg')).toHaveCount(0);
});

test("N holes need review banner appears when any cell < 0.85", async ({ page }) => {
  await page.route(`${API_URL}/golf/round/${seededRoundId}`, async (route) => {
    const body = {
      id: seededRoundId,
      user_id: "stub",
      course_name: "Stub",
      slope_rating: 128,
      course_rating: 71.2,
      adjusted_gross_score: null,
      differential: null,
      scorecard_image_url: null,
      ocr_confidence: 0.6,
      processing_status: "ocr_complete",
      played_at: "2026-04-18",
      holes: Array.from({ length: 18 }, (_, i) => ({
        hole_number: i + 1,
        par: 4,
        strokes: 4,
        ocr_confidence: i < 3 ? 0.5 : 0.95, // 3 low-confidence holes
      })),
      detected_players: [],
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto(`/golf/review/${seededRoundId}`);
  await expect(page.locator('[data-testid="review-banner"]')).toHaveText(/3 holes? need review/i);
});

test("live differential footer updates as scores change", async ({ page }) => {
  await page.route(`${API_URL}/golf/round/${seededRoundId}`, async (route) => {
    const body = {
      id: seededRoundId,
      user_id: "stub",
      course_name: "Stub",
      slope_rating: 128,
      course_rating: 71.2,
      adjusted_gross_score: null,
      differential: null,
      scorecard_image_url: null,
      ocr_confidence: 0.95,
      processing_status: "ocr_complete",
      played_at: "2026-04-18",
      holes: Array.from({ length: 18 }, (_, i) => ({
        hole_number: i + 1,
        par: 4,
        strokes: 4, // total 72, = course rating → differential 0.0
        ocr_confidence: 0.95,
      })),
      detected_players: [],
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto(`/golf/review/${seededRoundId}`);
  const footer = page.locator('[data-testid="review-differential"]');
  await expect(footer).toContainText("0.7");
  // ((72 - 71.2) × 113) / 128 = 0.70625 → "0.7"

  // Change hole 1 from 4 → 5. New total 73. Differential: ((73-71.2)*113)/128 = 1.5890625 → "1.6"
  await page.locator('[data-testid="scorecard-cell-1"]').click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.type("5");
  await page.keyboard.press("Enter");
  await expect(footer).toContainText("1.6");
});

test("review page uses Fairway typography and surface styles", async ({ page }) => {
  await stubSeededRound(page);
  await page.goto(`/golf/review/${seededRoundId}`);
  await expect(page.locator(".fw-scope .fw-h1", { hasText: /review/i })).toBeVisible();
  await expect(page.locator(".fw-surface").first()).toBeVisible();
});

test("round page shows highlights grid and hole bar chart", async ({ page }) => {
  await page.route(`${API_URL}/golf/round/${seededRoundId}`, async (route) => {
    const body = {
      id: seededRoundId,
      user_id: "stub",
      course_name: "Stub Course",
      slope_rating: 128,
      course_rating: 71.2,
      adjusted_gross_score: 80,
      differential: 7.8,
      scorecard_image_url: null,
      ocr_confidence: 0.95,
      processing_status: "confirmed",
      played_at: "2026-04-18",
      holes: Array.from({ length: 18 }, (_, i) => ({
        hole_number: i + 1,
        par: 4,
        strokes: 4 + (i % 3 === 0 ? 1 : 0),
        ocr_confidence: 0.95,
      })),
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto(`/golf/round/${seededRoundId}`);
  await expect(page.locator('[data-testid="highlights-grid"]')).toBeVisible();
  await expect(page.locator('[data-testid="hole-bar-chart"] rect')).toHaveCount(18);
});

test("profile page uses Fairway stat tiles for rounds played", async ({ page }) => {
  await stubProfile(page);
  await page.goto(`/golf/profile/${seededUserId}`);
  await expect(page.locator(".fw-scope .fw-h1")).toBeVisible();
  await expect(page.locator('[data-testid="profile-stats"]')).toBeVisible();
});

test("leaderboard uses Fairway row style", async ({ page }) => {
  await stubLeaderboard(page);
  await page.goto("/golf/leaderboard");
  await expect(page.locator(".fw-scope .fw-h1", { hasText: /leaderboard/i })).toBeVisible();
  await expect(page.locator('[data-testid="leaderboard-list"]')).toHaveClass(/fw-surface/);
});

test("full Phase A surface is Fairway-skinned", async ({ page }) => {
  await stubSeededRound(page);
  await stubProfile(page);
  await stubLeaderboard(page);

  await page.goto("/golf/upload");
  await expect(page.locator(".fw-scope .fw-h1", { hasText: /log round/i })).toBeVisible();

  await page.goto(`/golf/review/${seededRoundId}`);
  await expect(page.locator(".fw-scope .fw-h1", { hasText: /review/i })).toBeVisible();

  await page.goto(`/golf/round/${seededRoundId}`);
  await expect(page.locator(".fw-scope")).toBeVisible();

  await page.goto(`/golf/profile/${seededUserId}`);
  await expect(page.locator('[data-testid="profile-stats"]')).toBeVisible();

  await page.goto("/golf/leaderboard");
  await expect(page.locator('[data-testid="leaderboard-list"]')).toBeVisible();
});
