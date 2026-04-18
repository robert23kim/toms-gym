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
