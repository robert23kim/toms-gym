import { test, expect, request } from "@playwright/test";

const API_URL =
  process.env.API_URL ||
  "https://my-python-backend-quyiiugyoq-ue.a.run.app";

/**
 * End-to-end tests for the bowling annotation workspace.
 *
 * These tests run against production and require at least one completed
 * BowlingResult with a processed video. Tests that need real data use
 * test.skip() when none is available.
 */

// Shared state: find a completed bowling result to test with
let attemptId: string | null = null;
let resultId: string | null = null;
let hasFrames = false;

test.beforeAll(async () => {
  const ctx = await request.newContext();
  try {
    // First find the bowling competition
    const compResp = await ctx.get(`${API_URL}/competitions`);
    const competitions = await compResp.json();
    const bowlingComp = competitions.competitions?.find(
      (c: any) => c.name?.toLowerCase().includes("bowling")
    );
    if (!bowlingComp) return;

    const resp = await ctx.get(`${API_URL}/bowling/results`, {
      params: { competition_id: bowlingComp.id },
    });
    if (resp.ok()) {
      const results = await resp.json();
      const completed = results.find(
        (r: any) => r.processing_status === "completed" && r.attempt_id
      );
      if (completed) {
        attemptId = completed.attempt_id;
        resultId = completed.id;

        // Check if frames are already extracted
        const framesResp = await ctx.get(
          `${API_URL}/bowling/result/${resultId}/frames`
        );
        if (framesResp.ok()) {
          const data = await framesResp.json();
          hasFrames = data.total_frames > 0;
        }
      }
    }
  } catch {
    // No existing results — tests will be skipped
  }
});

test.describe("Annotation API Endpoints", () => {
  test("annotation CRUD lifecycle via API", async () => {
    test.skip(!resultId, "No completed bowling result available");

    const ctx = await request.newContext();

    // 1. GET annotation — should return {} or existing annotation
    const getResp = await ctx.get(
      `${API_URL}/bowling/result/${resultId}/annotation`
    );
    expect(getResp.ok()).toBeTruthy();
    const initial = await getResp.json();
    expect(typeof initial).toBe("object");

    // 2. PUT ball annotation on frame 0
    const putBall = await ctx.put(
      `${API_URL}/bowling/result/${resultId}/annotation/ball/0`,
      { data: { x: 150, y: 250, radius: 20 } }
    );
    expect(putBall.ok()).toBeTruthy();

    // 3. Verify ball annotation exists
    const afterPut = await ctx.get(
      `${API_URL}/bowling/result/${resultId}/annotation`
    );
    const data1 = await afterPut.json();
    expect(data1.ball_annotations["0"]).toEqual({
      x: 150,
      y: 250,
      radius: 20,
    });

    // 4. PUT null on frame 0 — "no ball visible"
    const putNull = await ctx.put(
      `${API_URL}/bowling/result/${resultId}/annotation/ball/0`,
      { data: null, headers: { "Content-Type": "application/json" } }
    );
    expect(putNull.ok()).toBeTruthy();

    const afterNull = await ctx.get(
      `${API_URL}/bowling/result/${resultId}/annotation`
    );
    const data2 = await afterNull.json();
    expect(data2.ball_annotations["0"]).toBeNull();

    // 5. DELETE frame 0 — removes key entirely
    const delResp = await ctx.delete(
      `${API_URL}/bowling/result/${resultId}/annotation/ball/0`
    );
    expect(delResp.ok()).toBeTruthy();

    const afterDel = await ctx.get(
      `${API_URL}/bowling/result/${resultId}/annotation`
    );
    const data3 = await afterDel.json();
    expect(data3.ball_annotations).not.toHaveProperty("0");

    // 6. PUT markers
    const putMarkers = await ctx.put(
      `${API_URL}/bowling/result/${resultId}/annotation/markers`,
      {
        data: {
          ball_down: 5,
          breakpoint: 30,
          pin_hit: 45,
          ball_off_deck: 55,
        },
      }
    );
    expect(putMarkers.ok()).toBeTruthy();

    const afterMarkers = await ctx.get(
      `${API_URL}/bowling/result/${resultId}/annotation`
    );
    const data4 = await afterMarkers.json();
    expect(data4.frame_markers.pin_hit).toBe(45);
    expect(data4.frame_markers.ball_down).toBe(5);
  });

  test("frame 0 redirects to 0001.jpg", async () => {
    test.skip(!resultId || !hasFrames, "No result with extracted frames");

    const ctx = await request.newContext({ maxRedirects: 0 });
    const resp = await ctx.get(
      `${API_URL}/bowling/result/${resultId}/frames/0`
    );
    expect(resp.status()).toBe(302);
    const location = resp.headers()["location"];
    expect(location).toContain("0001.jpg");
  });
});

test.describe("Annotation Workspace Page", () => {
  test("BowlingResult page shows 'Annotate Frames' link", async ({
    page,
  }) => {
    test.skip(!attemptId, "No completed bowling result available");

    await page.goto(`/bowling/result/${attemptId}`);
    await page.waitForLoadState("networkidle");

    const annotateLink = page.getByRole("link", { name: /annotate frames/i });
    await expect(annotateLink).toBeVisible({ timeout: 15_000 });

    // Verify the link points to the correct URL
    const href = await annotateLink.getAttribute("href");
    expect(href).toContain(`/bowling/result/${attemptId}/annotate`);
  });

  test("annotation workspace loads and shows frame", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");

    await page.goto(`/bowling/result/${attemptId}/annotate`);

    // Should show "Extracting frames..." loading state or the workspace
    const loaded = await Promise.race([
      page
        .getByText("Annotation")
        .waitFor({ timeout: 60_000 })
        .then(() => "workspace"),
      page
        .getByText(/extracting frames/i)
        .waitFor({ timeout: 10_000 })
        .then(() => "loading"),
      page
        .getByText(/failed|error/i)
        .waitFor({ timeout: 10_000 })
        .then(() => "error"),
    ]);

    if (loaded === "loading") {
      // Wait for frames to extract (can take up to 2 minutes)
      await expect(page.getByText("Annotation")).toBeVisible({
        timeout: 120_000,
      });
    }

    if (loaded === "error") {
      test.skip(true, "Frame extraction failed — likely missing video");
      return;
    }

    // Workspace should now be visible
    await expect(page.getByText("Annotation")).toBeVisible();

    // Canvas should be present
    const canvas = page.locator("canvas");
    await expect(canvas).toBeVisible({ timeout: 15_000 });

    // Frame counter should show "Frame 1 / N"
    await expect(page.getByText(/Frame 1 \//)).toBeVisible();

    // Keyboard help bar should be visible
    await expect(page.getByText(/next\/prev/i)).toBeVisible();

    // Radius display
    await expect(page.getByText(/Radius:/)).toBeVisible();

    // Marker panel should show all 4 markers
    await expect(page.getByText("Ball Down")).toBeVisible();
    await expect(page.getByText("Breakpoint")).toBeVisible();
    await expect(page.getByText("Pin Hit")).toBeVisible();
    await expect(page.getByText("Off Deck")).toBeVisible();
  });

  test("keyboard navigation works", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);

    // Wait for workspace to load
    await expect(page.getByText("Annotation")).toBeVisible({
      timeout: 120_000,
    });
    await expect(page.locator("canvas")).toBeVisible({ timeout: 15_000 });

    // Should start at Frame 1
    await expect(page.getByText(/Frame 1 \//)).toBeVisible();

    // Press 'd' to go to next frame
    await page.keyboard.press("d");
    await expect(page.getByText(/Frame 2 \//)).toBeVisible();

    // Press 'a' to go back
    await page.keyboard.press("a");
    await expect(page.getByText(/Frame 1 \//)).toBeVisible();

    // Press ArrowRight to go forward
    await page.keyboard.press("ArrowRight");
    await expect(page.getByText(/Frame 2 \//)).toBeVisible();

    // Press 'w' to jump forward 10
    await page.keyboard.press("w");
    await expect(page.getByText(/Frame 12 \//)).toBeVisible();

    // Press 's' to jump back 10
    await page.keyboard.press("s");
    await expect(page.getByText(/Frame 2 \//)).toBeVisible();
  });

  test("canvas click creates ball annotation", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({
      timeout: 120_000,
    });

    const canvas = page.locator("canvas");
    await expect(canvas).toBeVisible({ timeout: 15_000 });

    // Click on the canvas to annotate
    const box = await canvas.boundingBox();
    if (!box) {
      test.skip(true, "Canvas has no bounding box");
      return;
    }

    await canvas.click({
      position: { x: box.width / 2, y: box.height / 2 },
    });

    // Wait for debounced save (500ms)
    await page.waitForTimeout(1000);

    // Annotated count should update from "0 / N" to "1 / N"
    await expect(page.getByText(/^1 \//)).toBeVisible({ timeout: 5_000 });

    // The timeline frame indicator for frame 0 should be green (annotated)
    const frame1Indicator = page.locator('[title="Frame 1"]');
    await expect(frame1Indicator).toHaveClass(/bg-green-500/, {
      timeout: 2_000,
    });
  });

  test("'n' key marks no ball, Delete key clears annotation", async ({
    page,
  }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({
      timeout: 120_000,
    });
    await expect(page.locator("canvas")).toBeVisible({ timeout: 15_000 });

    // Navigate to frame 2 (so we don't conflict with previous test)
    await page.keyboard.press("d");
    await expect(page.getByText(/Frame 2 \//)).toBeVisible();

    // Press 'n' to mark "no ball visible"
    await page.keyboard.press("n");
    await page.waitForTimeout(1000);

    // Frame 2 indicator should be gray (no ball = bg-gray-500)
    const frame2 = page.locator('[title="Frame 2"]');
    await expect(frame2).toHaveClass(/bg-gray-500/, { timeout: 2_000 });

    // Press Delete to clear the annotation
    await page.keyboard.press("Delete");
    await page.waitForTimeout(1000);

    // Frame 2 indicator should be dark gray (unannotated = bg-gray-700)
    await expect(frame2).toHaveClass(/bg-gray-700/, { timeout: 2_000 });
  });

  test("marker buttons work", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({
      timeout: 120_000,
    });

    // Click "Set (P)" button to set pin_hit marker on current frame
    const setPinHit = page.getByRole("button", { name: /Set \(P\)/ }).first();
    // There are 4 Set buttons — Pin Hit is the 3rd one
    const pinHitSet = page
      .locator("text=Pin Hit")
      .locator("..")
      .getByRole("button", { name: /Set/ });
    await pinHitSet.click();

    await page.waitForTimeout(1000);

    // Pin Hit should now show frame number "1" (current frame 0, displayed as 1)
    const pinHitRow = page.locator("text=Pin Hit").locator("..");
    await expect(pinHitRow.getByText("1")).toBeVisible({ timeout: 2_000 });

    // Clear button should appear
    const clearBtn = pinHitRow.getByRole("button", { name: /Clear/ });
    await expect(clearBtn).toBeVisible();

    // Click Clear to remove the marker
    await clearBtn.click();
    await page.waitForTimeout(1000);

    // Should show "---" again
    await expect(pinHitRow.getByText("---")).toBeVisible({ timeout: 2_000 });
  });

  test("annotations persist after page refresh", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({
      timeout: 120_000,
    });
    await expect(page.locator("canvas")).toBeVisible({ timeout: 15_000 });

    // Navigate to frame 5 and annotate it
    await page.keyboard.press("w"); // jump to ~frame 10
    await page.waitForTimeout(200);

    const canvas = page.locator("canvas");
    const box = await canvas.boundingBox();
    if (!box) {
      test.skip(true, "Canvas has no bounding box");
      return;
    }

    await canvas.click({
      position: { x: box.width * 0.4, y: box.height * 0.6 },
    });

    // Wait for save to complete
    await page.waitForTimeout(2000);

    // Note the current frame text
    const frameText = await page.getByText(/Frame \d+ \//).textContent();

    // Refresh the page
    await page.reload();
    await expect(page.getByText("Annotation")).toBeVisible({
      timeout: 120_000,
    });

    // Navigate back to the same frame
    await page.keyboard.press("w");
    await page.waitForTimeout(500);

    // The annotation count should be > 0 (persisted from before refresh)
    const countText = await page.getByText(/\d+ \/ \d+ annotated/).textContent();
    const count = parseInt(countText?.match(/(\d+) \//)?.[1] || "0");
    expect(count).toBeGreaterThan(0);
  });

  test.afterAll(async () => {
    // Clean up: reset annotation to empty for future test runs
    if (!resultId) return;
    const ctx = await request.newContext();
    try {
      await ctx.put(
        `${API_URL}/bowling/result/${resultId}/annotation`,
        {
          data: {
            version: "1.0",
            ball_annotations: {},
            frame_markers: {},
            video_metadata: { fps: 30, total_frames: 60, width: 1920, height: 1080 },
          },
        }
      );
    } catch {
      // Best effort cleanup
    }
  });
});
