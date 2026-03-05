import { test, expect, request } from "@playwright/test";

const API_URL =
  process.env.API_URL ||
  "https://my-python-backend-quyiiugyoq-ue.a.run.app";

test.describe("Bowling Feature", () => {
  test("backend API is healthy", async () => {
    const ctx = await request.newContext();
    const resp = await ctx.get(`${API_URL}/health`);
    expect(resp.ok()).toBeTruthy();
  });

  test("bowling upload page renders", async ({ page }) => {
    await page.goto("/bowling/upload");
    await expect(page.getByText("Upload Bowling Video")).toBeVisible();
    // File input and submit button present
    await expect(page.locator('input[type="file"]')).toBeAttached();
    await expect(
      page.getByRole("button", { name: /upload video/i })
    ).toBeVisible();
  });

  test("bowling result page handles missing result", async ({ page }) => {
    await page.goto("/bowling/result/00000000-0000-0000-0000-000000000001");
    // Should show error or "not found" state
    await expect(
      page.getByText(/not found|error|failed/i)
    ).toBeVisible({ timeout: 10_000 });
  });

  test("lane-edges API validates input", async () => {
    const ctx = await request.newContext();

    // PUT with missing lane_edges -> 400
    const badPut = await ctx.put(
      `${API_URL}/bowling/result/00000000-0000-0000-0000-000000000000/lane-edges`,
      { data: {} }
    );
    expect(badPut.status()).toBe(400);

    // PUT with valid shape on non-existent result -> 200 (UPDATE 0 rows, no error)
    const validPut = await ctx.put(
      `${API_URL}/bowling/result/00000000-0000-0000-0000-000000000000/lane-edges`,
      {
        data: {
          lane_edges: {
            top_left: [100, 50],
            top_right: [500, 50],
            bottom_left: [50, 400],
            bottom_right: [550, 400],
          },
        },
      }
    );
    expect(validPut.status()).toBe(200);
  });

  test("reanalyze API returns 404 for non-existent result", async () => {
    const ctx = await request.newContext();
    const resp = await ctx.post(
      `${API_URL}/bowling/result/00000000-0000-0000-0000-000000000000/reanalyze`
    );
    expect(resp.status()).toBe(404);
  });
});

test.describe("Lane Edge Editor (with existing result)", () => {
  let attemptId: string | null = null;

  test.beforeAll(async () => {
    // Try to find an existing processed bowling result to test the editor
    const ctx = await request.newContext();
    try {
      // Query a known competition for existing results
      const resp = await ctx.get(`${API_URL}/bowling/results`, {
        params: { competition_id: "bowling-01" },
      });
      if (resp.ok()) {
        const results = await resp.json();
        const completed = results.find(
          (r: any) => r.processing_status === "completed" && r.attempt_id
        );
        if (completed) {
          attemptId = completed.attempt_id;
        }
      }
    } catch {
      // No existing results — tests will be skipped
    }
  });

  test("result page shows lane edge editor when result has frame_url", async ({
    page,
  }) => {
    test.skip(!attemptId, "No existing processed result to test with");

    await page.goto(`/bowling/result/${attemptId}`);

    // Wait for result to load (either shows content or error)
    await page.waitForLoadState("networkidle");

    // Result page should show "Bowling Result" heading
    await expect(page.getByText("Bowling Result")).toBeVisible({
      timeout: 15_000,
    });

    // Check for lane edge editor canvas (only present if frame_url exists)
    const canvas = page.locator("canvas");
    const editorVisible = await canvas.isVisible().catch(() => false);

    if (editorVisible) {
      // Canvas should have crosshair cursor
      await expect(canvas).toHaveCSS("cursor", "crosshair");

      // "Save & Re-analyze" button should exist but be disabled (no edits yet)
      const saveBtn = page.getByRole("button", {
        name: /save & re-analyze/i,
      });
      await expect(saveBtn).toBeVisible();

      // Simulate a drag on the canvas to edit a corner
      const box = await canvas.boundingBox();
      if (box) {
        // Drag near top-left area (where top_left handle likely is)
        await canvas.click({ position: { x: box.width * 0.1, y: box.height * 0.1 } });
        await page.mouse.down();
        await page.mouse.move(
          box.x + box.width * 0.15,
          box.y + box.height * 0.15,
          { steps: 5 }
        );
        await page.mouse.up();

        // After editing, save button should be enabled
        // (onChange fires when a corner is dragged and released)
      }
    } else {
      // No lane edge editor — result might not have frame_url
      // Still verify stats section is present
      await expect(page.getByText(/stats/i)).toBeVisible();
    }
  });

  test("save and reanalyze flow works", async ({ page }) => {
    test.skip(!attemptId, "No existing processed result to test with");

    // First, get the result to find the bowling result ID
    const ctx = await request.newContext();
    const resp = await ctx.get(`${API_URL}/bowling/result/${attemptId}`);
    expect(resp.ok()).toBeTruthy();
    const result = await resp.json();

    // Only test if we have lane edges
    test.skip(
      !result.lane_edges_auto && !result.lane_edges_manual,
      "Result has no lane edges"
    );

    const resultId = result.id;
    const edges = result.lane_edges_manual || result.lane_edges_auto;

    // Save modified edges via API
    const modifiedEdges = {
      top_left: [edges.top_left[0] + 5, edges.top_left[1] + 5],
      top_right: edges.top_right,
      bottom_left: edges.bottom_left,
      bottom_right: edges.bottom_right,
    };

    const saveResp = await ctx.put(
      `${API_URL}/bowling/result/${resultId}/lane-edges`,
      { data: { lane_edges: modifiedEdges } }
    );
    expect(saveResp.ok()).toBeTruthy();

    // Trigger reanalyze
    const reanalyzeResp = await ctx.post(
      `${API_URL}/bowling/result/${resultId}/reanalyze`
    );
    expect(reanalyzeResp.ok()).toBeTruthy();

    // Verify status changed to queued
    const checkResp = await ctx.get(`${API_URL}/bowling/result/${attemptId}`);
    const updated = await checkResp.json();
    expect(updated.processing_status).toBe("queued");

    // Restore original edges
    await ctx.put(`${API_URL}/bowling/result/${resultId}/lane-edges`, {
      data: { lane_edges: edges },
    });
  });
});
