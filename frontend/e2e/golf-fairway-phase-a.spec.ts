import { test, expect, request, APIRequestContext } from "@playwright/test";
import fs from "fs";
import path from "path";

/**
 * Fairway Phase A — visual + UX polish smoke test.
 *
 * Strategy: seed a golf round via the real backend so we have a deterministic
 * round ID to hit, then drive the UI and assert Fairway markers.
 */

const API_URL =
  process.env.API_URL ||
  "https://my-python-backend-quyiiugyoq-ue.a.run.app";

test.describe.configure({ mode: "serial" });

// Module-level seed — populated by beforeAll, read by downstream tests.
let seededRoundId = "";
let seededUserId = "";

test.beforeAll(async () => {
  const ctx: APIRequestContext = await request.newContext();

  const uniq = Date.now().toString(36);
  const email = `fairway-phase-a-${uniq}@test.com`;
  const register = await ctx.post(`${API_URL}/auth/register`, {
    data: { email, password: "TestPassword123!", name: `Phase A ${uniq}` },
  });
  if (!register.ok()) {
    throw new Error(
      `Failed to register test user: ${register.status()} ${await register.text()}`
    );
  }

  const fixturePath = path.resolve(__dirname, "fixtures/scorecard-test.jpg");
  const imageBuffer = fs.readFileSync(fixturePath);
  const upload = await ctx.post(`${API_URL}/golf/upload`, {
    multipart: {
      image: {
        name: "scorecard-test.jpg",
        mimeType: "image/jpeg",
        buffer: imageBuffer,
      },
      email,
      course_name: `Phase A Test Course ${uniq}`,
      slope_rating: "128",
      course_rating: "71.2",
      played_at: new Date().toISOString().split("T")[0],
    },
  });
  if (!upload.ok()) {
    throw new Error(
      `Failed to seed round: ${upload.status()} ${await upload.text()}`
    );
  }
  const body = await upload.json();
  seededRoundId = body.round_id;
  seededUserId = body.user_id;
  expect(seededRoundId).toMatch(/^[0-9a-f-]{36}$/);
  expect(seededUserId).toMatch(/^[0-9a-f-]{36}$/);
});

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
  await page.route(`**/golf/round/${seededRoundId}`, async (route) => {
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
  await page.route(`**/golf/round/${seededRoundId}`, async (route) => {
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
