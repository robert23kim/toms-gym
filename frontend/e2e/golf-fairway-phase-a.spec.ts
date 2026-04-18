import { test, expect, request } from "@playwright/test";

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

test("golf upload page is wrapped in fw-scope", async ({ page }) => {
  await page.goto("/golf/upload");
  const scope = page.locator(".fw-scope").first();
  await expect(scope).toBeVisible();
});
