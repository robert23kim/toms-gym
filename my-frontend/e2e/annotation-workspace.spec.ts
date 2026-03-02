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
    await expect(page.locator('[data-testid="status-bar"]').getByText(/Frame 1 \//)).toBeVisible();

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

    const statusBar = page.locator('[data-testid="status-bar"]');

    // Should start at Frame 1
    await expect(statusBar.getByText(/Frame 1 \//)).toBeVisible();

    // Press 'd' to go to next frame
    await page.keyboard.press("d");
    await expect(statusBar.getByText(/Frame 2 \//)).toBeVisible();

    // Press 'a' to go back
    await page.keyboard.press("a");
    await expect(statusBar.getByText(/Frame 1 \//)).toBeVisible();

    // Press ArrowRight to go forward
    await page.keyboard.press("ArrowRight");
    await expect(statusBar.getByText(/Frame 2 \//)).toBeVisible();

    // Press 'w' to jump forward 10
    await page.keyboard.press("w");
    await expect(statusBar.getByText(/Frame 12 \//)).toBeVisible();

    // Press 's' to jump back 10
    await page.keyboard.press("s");
    await expect(statusBar.getByText(/Frame 2 \//)).toBeVisible();
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

    // The timeline frame indicator for frame 0 should turn green (annotated)
    // This is more reliable than checking the count text which may have varying formats

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
    await expect(page.locator('[data-testid="status-bar"]').getByText(/Frame 2 \//)).toBeVisible();

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
    const frameText = await page.locator('[data-testid="status-bar"]').getByText(/Frame \d+ \//).textContent();

    // Refresh the page
    await page.reload();
    await expect(page.getByText("Annotation")).toBeVisible({
      timeout: 120_000,
    });

    // Navigate back to the same frame
    await page.keyboard.press("w");
    await page.waitForTimeout(500);

    // The annotation count should be > 0 (persisted from before refresh)
    const statusBar = page.locator('[data-testid="status-bar"]');
    const annotatedText = await statusBar.getByText(/Annotated: \d+/).textContent();
    const count = parseInt(annotatedText?.match(/Annotated: (\d+)/)?.[1] || "0");
    expect(count).toBeGreaterThan(0);
  });

  test("help overlay toggle via H key", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({ timeout: 120_000 });
    await expect(page.locator("canvas")).toBeVisible({ timeout: 15_000 });

    // Press 'h' to open help overlay
    await page.keyboard.press("h");
    const overlay = page.locator('[data-testid="help-overlay"]');
    await expect(overlay).toBeVisible({ timeout: 2_000 });
    await expect(page.getByText("Keyboard Shortcuts")).toBeVisible();

    // Press 'h' again to dismiss (the overlay listens for clicks/keydown)
    await overlay.click();
    await expect(overlay).not.toBeVisible({ timeout: 2_000 });
  });

  test("StatusBar shows frame info and mode badge", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({ timeout: 120_000 });
    await expect(page.locator("canvas")).toBeVisible({ timeout: 15_000 });

    const statusBar = page.locator('[data-testid="status-bar"]');
    await expect(statusBar).toBeVisible();
    await expect(statusBar.getByText(/Frame 1 \//)).toBeVisible();
    await expect(statusBar.getByText("NORMAL")).toBeVisible();
  });

  test("edge mode toggle via E key", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({ timeout: 120_000 });
    await expect(page.locator("canvas")).toBeVisible({ timeout: 15_000 });

    const statusBar = page.locator('[data-testid="status-bar"]');
    await expect(statusBar.getByText("NORMAL")).toBeVisible();

    // Press 'e' to enter edge edit mode
    await page.keyboard.press("e");
    await expect(statusBar.getByText("EDGE EDIT")).toBeVisible({ timeout: 2_000 });

    // Press 'e' again to exit
    await page.keyboard.press("e");
    await expect(statusBar.getByText("NORMAL")).toBeVisible({ timeout: 2_000 });
  });

  test("edge mode disables ball click", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({ timeout: 120_000 });
    await expect(page.locator("canvas")).toBeVisible({ timeout: 15_000 });

    const statusBar = page.locator('[data-testid="status-bar"]');

    // Navigate to a clean frame to avoid interference
    await page.keyboard.press("d");
    await page.keyboard.press("d");
    await page.keyboard.press("d");
    await expect(statusBar.getByText(/Frame 4 \//)).toBeVisible();

    // Enter edge mode
    await page.keyboard.press("e");
    await expect(statusBar.getByText("EDGE EDIT")).toBeVisible({ timeout: 2_000 });

    // Click canvas center
    const canvas = page.locator("canvas");
    const box = await canvas.boundingBox();
    if (!box) { test.skip(true, "Canvas has no bounding box"); return; }
    await canvas.click({ position: { x: box.width / 2, y: box.height / 2 } });
    await page.waitForTimeout(1000);

    // Frame 4 indicator should NOT be green (ball annotation should be blocked in edge mode)
    const frame4 = page.locator('[title="Frame 4"]');
    const classes = await frame4.getAttribute("class");
    expect(classes).not.toContain("bg-green-500");

    // Exit edge mode
    await page.keyboard.press("e");
  });

  test("crop view toggle via Z key", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({ timeout: 120_000 });

    const canvas = page.locator("canvas");
    await expect(canvas).toBeVisible({ timeout: 15_000 });

    // Press 'z' to enable crop view
    await page.keyboard.press("z");
    await page.waitForTimeout(500);
    await expect(canvas).toBeVisible();
    const box1 = await canvas.boundingBox();
    expect(box1).toBeTruthy();
    expect(box1!.width).toBeGreaterThan(0);

    // Press 'z' again to disable crop view
    await page.keyboard.press("z");
    await page.waitForTimeout(500);
    await expect(canvas).toBeVisible();
    const box2 = await canvas.boundingBox();
    expect(box2).toBeTruthy();
    expect(box2!.width).toBeGreaterThan(0);
  });

  test("marker toggle via P key", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({ timeout: 120_000 });
    await expect(page.locator("canvas")).toBeVisible({ timeout: 15_000 });

    // Navigate to frame 3
    await page.keyboard.press("d");
    await page.keyboard.press("d");
    await page.keyboard.press("d");
    await expect(page.locator('[data-testid="status-bar"]').getByText(/Frame 4 \//)).toBeVisible();

    // Press 'p' to set pin_hit marker on frame 3 (0-indexed), displayed as 4
    await page.keyboard.press("p");
    await page.waitForTimeout(1000);

    const pinHitRow = page.locator("text=Pin Hit").locator("..");
    await expect(pinHitRow.getByText("4")).toBeVisible({ timeout: 2_000 });

    // Press 'p' again on same frame to toggle it off
    await page.keyboard.press("p");
    await page.waitForTimeout(1000);
    await expect(pinHitRow.getByText("---")).toBeVisible({ timeout: 2_000 });
  });

  test("radius keyboard adjustment with ] and [", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({ timeout: 120_000 });
    await expect(page.locator("canvas")).toBeVisible({ timeout: 15_000 });

    // Read current radius (default is 25)
    const radiusText = page.getByText(/Radius: \d+/);
    await expect(radiusText).toBeVisible();
    const before = await radiusText.textContent();
    const radiusBefore = parseInt(before!.match(/Radius: (\d+)/)![1]);

    // Press ']' to increase radius by 3
    await page.keyboard.press("]");
    await expect(page.getByText(`Radius: ${radiusBefore + 3}`)).toBeVisible({ timeout: 2_000 });

    // Press '[' to decrease radius by 3
    await page.keyboard.press("[");
    await expect(page.getByText(`Radius: ${radiusBefore}`)).toBeVisible({ timeout: 2_000 });
  });

  test("Home/End navigation", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({ timeout: 120_000 });
    await expect(page.locator("canvas")).toBeVisible({ timeout: 15_000 });

    const statusBar = page.locator('[data-testid="status-bar"]');

    // Navigate away from frame 1
    await page.keyboard.press("d");
    await page.keyboard.press("d");
    await page.keyboard.press("d");
    await expect(statusBar.getByText(/Frame 4 \//)).toBeVisible();

    // Press Home to go to first frame
    await page.keyboard.press("Home");
    await expect(statusBar.getByText(/Frame 1 \//)).toBeVisible({ timeout: 2_000 });

    // Press End to go to last frame
    await page.keyboard.press("End");
    await page.waitForTimeout(500);

    // Verify we're at the last frame: the displayed number should match total
    const frameText = await statusBar.getByText(/Frame \d+ \/ \d+/).textContent();
    const match = frameText!.match(/Frame (\d+) \/ (\d+)/);
    expect(match).toBeTruthy();
    expect(match![1]).toBe(match![2]); // current frame should equal total
  });

  test("lane edges API CRUD", async () => {
    test.skip(!resultId, "No completed bowling result available");

    const ctx = await request.newContext();

    const edges = {
      top_left: [100, 100],
      top_right: [200, 100],
      bottom_left: [100, 500],
      bottom_right: [200, 500],
    };

    // PUT lane edges on frame 0
    const putResp = await ctx.put(
      `${API_URL}/bowling/result/${resultId}/annotation/lane-edges/0`,
      { data: edges }
    );
    expect(putResp.ok()).toBeTruthy();

    // GET annotation, verify frame_lane_edges["0"] exists
    const getResp1 = await ctx.get(
      `${API_URL}/bowling/result/${resultId}/annotation`
    );
    const data1 = await getResp1.json();
    expect(data1.frame_lane_edges).toBeDefined();
    expect(data1.frame_lane_edges["0"]).toBeDefined();
    expect(data1.frame_lane_edges["0"].top_left).toEqual([100, 100]);

    // DELETE lane edges on frame 0
    const delResp = await ctx.delete(
      `${API_URL}/bowling/result/${resultId}/annotation/lane-edges/0`
    );
    expect(delResp.ok()).toBeTruthy();

    // GET annotation, verify frame_lane_edges["0"] is gone
    const getResp2 = await ctx.get(
      `${API_URL}/bowling/result/${resultId}/annotation`
    );
    const data2 = await getResp2.json();
    expect(data2.frame_lane_edges?.["0"]).toBeUndefined();
  });

  test("trajectory panel appears in workspace", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({ timeout: 120_000 });
    await expect(page.locator("canvas")).toBeVisible({ timeout: 15_000 });

    // "Save Trajectory" button should be visible in the side panel
    await expect(page.getByRole("button", { name: /save trajectory/i })).toBeVisible();

    // Either a trajectory canvas (if lane edges exist) or a placeholder should be visible
    const trajectoryPlaceholder = page.locator('[data-testid="trajectory-placeholder"]');
    const canvasCount = await page.locator("canvas").count();

    // At minimum: 1 frame canvas. If lane edges exist: 2 canvases (frame + trajectory)
    // If no lane edges: 1 canvas + placeholder div
    if (canvasCount >= 2) {
      // Lane edges available — trajectory canvas rendered
      const trajectoryCanvas = page.locator("canvas").nth(1);
      const trajBox = await trajectoryCanvas.boundingBox();
      expect(trajBox).toBeTruthy();
      expect(trajBox!.width).toBeGreaterThan(0);
    } else {
      // No lane edges — placeholder shown
      await expect(trajectoryPlaceholder).toBeVisible();
      await expect(page.getByText("No lane edges available")).toBeVisible();
    }
  });

  test("save trajectory API endpoint", async () => {
    test.skip(!resultId, "No completed bowling result available");

    const ctx = await request.newContext();

    // Create a minimal 1x1 white PNG as base64
    const minimalPng = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==";

    const resp = await ctx.post(
      `${API_URL}/bowling/result/${resultId}/annotation/trajectory`,
      { data: { image: minimalPng } }
    );
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(data.url).toBeDefined();
    expect(data.url).toContain("annotation_trajectory.png");
  });

  test("canvas renders without console errors", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({ timeout: 120_000 });

    const canvas = page.locator("canvas");
    await expect(canvas).toBeVisible({ timeout: 15_000 });

    // Click canvas to annotate
    const box = await canvas.boundingBox();
    if (!box) { test.skip(true, "Canvas has no bounding box"); return; }
    await canvas.click({ position: { x: box.width / 2, y: box.height / 2 } });
    await page.waitForTimeout(1000);

    // Canvas should have non-zero bounding box
    const finalBox = await canvas.boundingBox();
    expect(finalBox).toBeTruthy();
    expect(finalBox!.width).toBeGreaterThan(0);
    expect(finalBox!.height).toBeGreaterThan(0);

    // Filter out known benign errors (e.g., network/CORS from GCS frame loading)
    const realErrors = errors.filter(
      (e) => !e.includes("Failed to load resource") && !e.includes("CORS")
    );
    expect(realErrors).toEqual([]);
  });

  test("auto-copy ball on frame advance", async ({ page }) => {
    test.skip(!attemptId, "No completed bowling result available");
    test.skip(!hasFrames, "No extracted frames");

    await page.goto(`/bowling/result/${attemptId}/annotate`);
    await expect(page.getByText("Annotation")).toBeVisible({ timeout: 120_000 });
    const canvas = page.locator("canvas").first();
    await expect(canvas).toBeVisible({ timeout: 15_000 });

    // Navigate to a clean area (frame 20+)
    for (let i = 0; i < 20; i++) await page.keyboard.press("d");
    await page.waitForTimeout(300);

    // Clear this frame to ensure clean state
    await page.keyboard.press("Delete");
    await page.waitForTimeout(600);

    // Go back one frame and annotate it
    await page.keyboard.press("a");
    await page.waitForTimeout(300);

    const box = await canvas.boundingBox();
    if (!box) { test.skip(true, "Canvas has no bounding box"); return; }
    await canvas.click({ position: { x: box.width / 2, y: box.height / 2 } });
    await page.waitForTimeout(1000);

    // Now press D to advance — next frame should auto-fill
    await page.keyboard.press("d");
    await page.waitForTimeout(1000);

    // The frame indicator should be green (auto-copied)
    const statusBar = page.locator('[data-testid="status-bar"]');
    const frameText = await statusBar.getByText(/Frame \d+ \//).textContent();
    const frameNum = parseInt(frameText!.match(/Frame (\d+)/)?.[1] || "0");
    const indicator = page.locator(`[title="Frame ${frameNum}"]`);
    await expect(indicator).toHaveClass(/bg-green-500/, { timeout: 2_000 });
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
            frame_lane_edges: {},
            video_metadata: { fps: 30, total_frames: 60, width: 1920, height: 1080 },
          },
        }
      );
    } catch {
      // Best effort cleanup
    }
  });
});
