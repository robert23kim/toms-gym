import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, ChevronDown, ChevronRight, PencilRuler, Share2 } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import LaneEdgeEditor from "../components/LaneEdgeEditor";
import BowlingStatCard from "../components/BowlingStatCard";
import { useToast } from "../components/ui/use-toast";
import { createAndCopyShareLink } from "../lib/share";
import { API_URL } from "../config";
import { BowlingResult as BowlingResultType, LaneEdges, Annotation } from "../lib/types";
import {
  deriveEntryBoard,
  derivePocket,
  deriveSpeedMph,
  deriveHook,
} from "../lib/bowlingStats";

const HOOK_ARROW: Record<"left" | "right" | "straight", string> = {
  left: "←",
  right: "→",
  straight: "↑",
};

const BowlingResult: React.FC = () => {
  const { attemptId } = useParams<{ attemptId: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<BowlingResultType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editedEdges, setEditedEdges] = useState<LaneEdges | null>(null);
  const [saving, setSaving] = useState(false);
  const [polling, setPolling] = useState(false);
  const [annotation, setAnnotation] = useState<Annotation | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [sharing, setSharing] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    const fetchResult = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API_URL}/bowling/result/${attemptId}`);
        setResult(response.data);
      } catch (err: any) {
        console.error("Error fetching bowling result:", err);
        setError(
          err.response?.data?.error ||
          err.message ||
          "Failed to load bowling result"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchResult();
  }, [attemptId]);

  // Poll for result updates when reanalyzing
  useEffect(() => {
    if (!polling) return;
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_URL}/bowling/result/${attemptId}`);
        const updated = response.data;
        if (updated.processing_status === "completed" || updated.processing_status === "failed") {
          setResult(updated);
          setPolling(false);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [polling, attemptId]);

  // Fetch annotation summary when result is loaded
  useEffect(() => {
    if (!result?.id || result.processing_status !== 'completed') return;
    axios.get(`${API_URL}/bowling/result/${result.id}/annotation`)
      .then(res => {
        if (res.data?.version) setAnnotation(res.data);
      })
      .catch(() => {}); // Silently fail — annotation is optional
  }, [result?.id, result?.processing_status]);

  const handleSaveAndReanalyze = async () => {
    if (!editedEdges || !result) return;
    setSaving(true);
    try {
      await axios.put(`${API_URL}/bowling/result/${result.id}/lane-edges`, {
        lane_edges: editedEdges,
      });
      await axios.post(`${API_URL}/bowling/result/${result.id}/reanalyze`);
      setResult((prev) => prev ? {
        ...prev,
        processing_status: "processing" as const,
        lane_edges_manual: editedEdges,
      } : null);
      setPolling(true);
    } catch (err: any) {
      console.error("Save/reanalyze error:", err);
      setError(err.response?.data?.error || "Failed to save lane edges");
    } finally {
      setSaving(false);
    }
  };

  const handleResetEdges = () => {
    if (result?.lane_edges_auto) {
      setEditedEdges(result.lane_edges_auto);
    }
  };

  // --- Share (T13) — distinct region; independent of the T12 low-confidence block.
  const handleShare = async () => {
    if (sharing || !result) return;
    setSharing(true);
    try {
      const board = deriveEntryBoard(result);
      const pk = derivePocket(board);
      const spd = deriveSpeedMph(annotation);
      const bits: string[] = [];
      if (board != null) bits.push(`Entry board ${Math.round(board)}`);
      if (spd != null) bits.push(`${spd.toFixed(1)} mph`);
      const shortUrl = await createAndCopyShareLink({
        targetUrl: window.location.href,
        ogTitle: "Bowling — Your Throw",
        ogDescription: bits.join(" · ") || "Tracked on Tom's Gym",
        ogStat: pk ? pk.label : board != null ? String(Math.round(board)) : undefined,
      });
      toast({ title: "Short link copied!", description: shortUrl });
    } catch (err) {
      toast({
        title: "Could not create short link",
        description: err instanceof Error ? err.message : "Please try again",
        variant: "destructive",
      });
    } finally {
      setSharing(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-6xl mx-auto">
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-6xl mx-auto">
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-500">
              {error}
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (!result) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-6xl mx-auto text-center">
            <h2 className="text-2xl font-bold">Result not found</h2>
            <Link to="/" className="text-primary hover:underline mt-4 inline-block">
              Return Home
            </Link>
          </div>
        </div>
      </Layout>
    );
  }

  // --- Consumer-facing derived stats (see lib/bowlingStats.ts) ---------------
  const entryBoard = deriveEntryBoard(result);
  const pocket = derivePocket(entryBoard);
  const speedMph = deriveSpeedMph(annotation);
  const hook = deriveHook(result);

  const annotateHref = `/bowling/result/${attemptId}/annotate`;

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
      >
        <div className="max-w-6xl mx-auto">
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
          >
            <ArrowLeft className="mr-2" size={16} />
            Back
          </button>

          <div className="bg-card rounded-lg shadow-lg overflow-hidden">
            <div className="p-6 sm:p-8 space-y-6">
              {/* Share region (T13) */}
              <div className="flex items-start justify-between gap-3">
                <h1 className="text-2xl font-bold">Your Throw</h1>
                {result.processing_status === "completed" && (
                  <button
                    onClick={handleShare}
                    disabled={sharing}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-muted text-muted-foreground hover:bg-muted/80 disabled:opacity-50 text-sm font-medium shrink-0"
                    title="Copy short link to share"
                  >
                    <Share2 className="h-4 w-4" />
                    {sharing ? "Creating..." : "Share"}
                  </button>
                )}
              </div>

              {result.processing_status === "queued" || result.processing_status === "processing" ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
                  <p className="text-muted-foreground">
                    {result.processing_status === "queued"
                      ? "Queued for processing..."
                      : "Processing your bowling video..."}
                  </p>
                </div>
              ) : result.processing_status === "failed" ? (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-500">
                  <h2 className="text-lg font-semibold mb-1">Processing Failed</h2>
                  <p>{result.error_message || "An unexpected error occurred."}</p>
                </div>
              ) : (
                <>
                  {/* ============================================================
                      DEFAULT (consumer) view: headline stats + annotated video
                      + ball path. No debug jargon lives above the Advanced fold.
                     ============================================================ */}

                  {/* Headline stats a bowler cares about */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <BowlingStatCard
                      value={entryBoard != null ? Math.round(entryBoard) : "—"}
                      label="Entry Board"
                    />
                    <BowlingStatCard
                      value={pocket ? pocket.label : "—"}
                      label="Pocket"
                      tone={pocket ? (pocket.hit ? "good" : "warn") : "default"}
                    />
                    <BowlingStatCard
                      value={speedMph != null ? speedMph.toFixed(1) : "—"}
                      label="Ball Speed"
                      sublabel={speedMph != null ? "est. · mph" : "mph"}
                    />
                    <BowlingStatCard
                      value={
                        hook
                          ? hook.direction === "straight"
                            ? "Straight"
                            : `${HOOK_ARROW[hook.direction]} ${hook.boards}`
                          : "—"
                      }
                      label="Hook"
                      sublabel={hook && hook.direction !== "straight" ? "boards" : undefined}
                    />
                  </div>

                  {/* T12 SEAM: low-confidence filming tips + retry CTA render here
                      (gated on result.detection_rate below a threshold). Owned by
                      task T12 — intentionally not implemented in T10. */}

                  {/* Annotated video + ball path */}
                  <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                    <div className="lg:col-span-3">
                      {result.debug_video_url ? (
                        <video
                          src={result.debug_video_url}
                          controls
                          autoPlay
                          muted
                          className="w-full rounded-lg"
                        />
                      ) : (
                        <div className="w-full aspect-video bg-muted rounded-lg flex items-center justify-center">
                          <span className="text-muted-foreground">No video available</span>
                        </div>
                      )}
                    </div>

                    <div className="lg:col-span-2 space-y-2">
                      <h3 className="text-lg font-semibold">Ball Path</h3>
                      {result.trajectory_png_url ? (
                        <img
                          src={result.trajectory_png_url}
                          alt="Ball trajectory"
                          className="w-full rounded-lg"
                        />
                      ) : (
                        <div className="w-full aspect-[3/4] bg-muted rounded-lg flex items-center justify-center">
                          <span className="text-muted-foreground text-sm">No ball path available</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Prominent manual-annotate CTA (tracking correction) */}
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-primary/5 rounded-lg p-4">
                    <div>
                      <h3 className="text-base font-semibold">Tracking look off?</h3>
                      <p className="text-sm text-muted-foreground">
                        Fine-tune the ball path frame by frame to sharpen your stats.
                      </p>
                    </div>
                    <a
                      href={annotateHref}
                      className="inline-flex items-center justify-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md whitespace-nowrap"
                    >
                      <PencilRuler className="mr-2" size={16} />
                      Annotate Frames
                    </a>
                  </div>

                  {/* ============================================================
                      ADVANCED (dev) view — collapsed by default. Everything
                      engineer-facing lives here: raw numbers, detection/timing,
                      lane-edge editor, annotation frame internals.
                     ============================================================ */}
                  <div className="border-t border-border pt-4">
                    <button
                      onClick={() => setShowAdvanced((v) => !v)}
                      className="inline-flex items-center text-sm font-medium text-muted-foreground hover:text-foreground"
                    >
                      {showAdvanced ? (
                        <ChevronDown size={16} className="mr-1" />
                      ) : (
                        <ChevronRight size={16} className="mr-1" />
                      )}
                      Advanced
                    </button>

                    {showAdvanced && (
                      <div className="mt-4 space-y-6">
                        {/* Raw analysis numbers */}
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                          {result.board_at_pins != null && (
                            <BowlingStatCard
                              value={result.board_at_pins.toFixed(1)}
                              label="Board at Pins"
                              tone="muted"
                            />
                          )}
                          {result.entry_board != null && (
                            <BowlingStatCard
                              value={result.entry_board.toFixed(1)}
                              label="Entry Board (raw)"
                              tone="muted"
                            />
                          )}
                          {result.detection_rate != null && (
                            <BowlingStatCard
                              value={`${result.detection_rate.toFixed(1)}%`}
                              label="Detection Rate"
                              tone="muted"
                            />
                          )}
                          {result.processing_time_s != null && (
                            <BowlingStatCard
                              value={`${result.processing_time_s.toFixed(1)}s`}
                              label="Processing Time"
                              tone="muted"
                            />
                          )}
                        </div>

                        {/* Lane edge editor + re-analyze */}
                        {result.frame_url && (result.lane_edges_auto || result.lane_edges_manual) && (
                          <div>
                            <h3 className="text-lg font-semibold mb-2">Lane Edges</h3>
                            <LaneEdgeEditor
                              frameUrl={result.frame_url}
                              laneEdges={editedEdges || result.lane_edges_manual || result.lane_edges_auto!}
                              onChange={setEditedEdges}
                            />
                            <div className="flex gap-3 mt-3">
                              <button
                                onClick={handleSaveAndReanalyze}
                                disabled={saving || !editedEdges}
                                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50"
                              >
                                {saving ? "Saving..." : "Save & Re-analyze"}
                              </button>
                              {result.lane_edges_manual && (
                                <button
                                  onClick={handleResetEdges}
                                  className="px-4 py-2 bg-muted text-muted-foreground rounded-lg hover:bg-muted/80"
                                >
                                  Reset to Auto
                                </button>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Annotation frame internals */}
                        <div className="bg-muted/40 rounded-lg p-4">
                          {(() => {
                            const total = annotation?.video_metadata?.total_frames || 0;
                            const annotated = Object.keys(annotation?.ball_annotations || {}).length;
                            const pct = total > 0 ? Math.round((annotated / total) * 100) : 0;
                            return (
                              <>
                                <div className="flex items-center gap-4 mb-2">
                                  <h3 className="text-lg font-semibold">Annotation</h3>
                                  {annotation && (
                                    <span className="text-sm text-muted-foreground">
                                      {annotated} / {total} frames ({pct}%)
                                    </span>
                                  )}
                                </div>
                                {annotation && (
                                  <div className="w-full bg-muted rounded-full h-2">
                                    <div
                                      className="bg-green-500 h-2 rounded-full transition-all"
                                      style={{ width: `${pct}%` }}
                                    />
                                  </div>
                                )}
                              </>
                            );
                          })()}
                          {annotation?.frame_markers && Object.keys(annotation.frame_markers).length > 0 && (
                            <div className="flex flex-wrap gap-3 text-sm mt-2">
                              {annotation.frame_markers.ball_down != null && (
                                <span className="text-blue-400">Ball Down: Frame {annotation.frame_markers.ball_down + 1}</span>
                              )}
                              {annotation.frame_markers.breakpoint != null && (
                                <span className="text-yellow-400">Breakpoint: Frame {annotation.frame_markers.breakpoint + 1}</span>
                              )}
                              {annotation.frame_markers.pin_hit != null && (
                                <span className="text-red-400">Pin Hit: Frame {annotation.frame_markers.pin_hit + 1}</span>
                              )}
                              {annotation.frame_markers.ball_off_deck != null && (
                                <span className="text-purple-400">Off Deck: Frame {annotation.frame_markers.ball_off_deck + 1}</span>
                              )}
                            </div>
                          )}
                          <a
                            href={annotateHref}
                            className="inline-block mt-3 text-sm text-blue-500 hover:underline"
                          >
                            Open annotation workspace →
                          </a>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default BowlingResult;
