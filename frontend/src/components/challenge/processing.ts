import type { LiftingResult } from "../../lib/types";

/**
 * Which of the viewer's attempts are still being analyzed.
 *
 * Leaderboard rows only exist once analysis completes, so a freshly uploaded
 * video is invisible on the challenge page for minutes (or forever, if the
 * job died) — which reads as "my upload vanished". The page uses this to show
 * a "processing" banner instead.
 *
 * An attempt with no fetched result is NOT treated as processing: old attempts
 * may predate analysis entirely, and a missing row must not pin a permanent
 * banner on them.
 */
export function viewerProcessingAttempts(
  videos: ReadonlyArray<{ attempt_id: string; user_id: string | number }>,
  results: Readonly<Record<string, LiftingResult | undefined>>,
  viewerId: string | number | null
): string[] {
  if (viewerId === null || viewerId === undefined) return [];
  return videos
    .filter((v) => String(v.user_id) === String(viewerId))
    .filter((v) => {
      const status = results[v.attempt_id]?.processing_status;
      return status === "queued" || status === "processing";
    })
    .map((v) => v.attempt_id);
}
