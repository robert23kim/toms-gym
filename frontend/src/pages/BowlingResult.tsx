import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import LaneEdgeEditor from "../components/LaneEdgeEditor";
import { API_URL } from "../config";
import { BowlingResult as BowlingResultType, LaneEdges, Annotation } from "../lib/types";

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
              <h1 className="text-2xl font-bold">Bowling Result</h1>

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
                  {/* Top row: video left, trajectory + stats right */}
                  <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                    {/* Debug Video — 3 cols */}
                    <div className="lg:col-span-3">
                      {result.debug_video_url ? (
                        <div>
                          <h3 className="text-lg font-semibold mb-2">Debug Video</h3>
                          <video
                            src={result.debug_video_url}
                            controls
                            autoPlay
                            muted
                            className="w-full rounded-lg"
                          />
                        </div>
                      ) : (
                        <div className="w-full aspect-video bg-muted rounded-lg flex items-center justify-center">
                          <span className="text-muted-foreground">No debug video available</span>
                        </div>
                      )}
                    </div>

                    {/* Right panel: trajectory + stats — 2 cols */}
                    <div className="lg:col-span-2 space-y-4">
                      {/* Trajectory */}
                      <div>
                        <h3 className="text-lg font-semibold mb-2">Trajectory</h3>
                        {result.trajectory_png_url ? (
                          <img
                            src={result.trajectory_png_url}
                            alt="Ball trajectory"
                            className="w-full rounded-lg"
                          />
                        ) : (
                          <div className="w-full aspect-[3/4] bg-muted rounded-lg flex items-center justify-center">
                            <span className="text-muted-foreground text-sm">No trajectory available</span>
                          </div>
                        )}
                      </div>

                      {/* Stats 2x2 */}
                      <div className="grid grid-cols-2 gap-3">
                        {result.board_at_pins != null && (
                          <div className="bg-primary/5 rounded-lg p-3 text-center">
                            <div className="text-2xl font-bold text-primary">{result.board_at_pins}</div>
                            <div className="text-xs text-muted-foreground">Board at Pins</div>
                          </div>
                        )}
                        {result.entry_board != null && (
                          <div className="bg-primary/5 rounded-lg p-3 text-center">
                            <div className="text-2xl font-bold text-primary">{result.entry_board}</div>
                            <div className="text-xs text-muted-foreground">Entry Board</div>
                          </div>
                        )}
                        {result.detection_rate != null && (
                          <div className="bg-primary/5 rounded-lg p-3 text-center">
                            <div className="text-2xl font-bold text-primary">
                              {result.detection_rate.toFixed(1)}%
                            </div>
                            <div className="text-xs text-muted-foreground">Detection Rate</div>
                          </div>
                        )}
                        {result.processing_time_s != null && (
                          <div className="bg-primary/5 rounded-lg p-3 text-center">
                            <div className="text-2xl font-bold text-primary">
                              {result.processing_time_s.toFixed(1)}s
                            </div>
                            <div className="text-xs text-muted-foreground">Processing Time</div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Lane Edges — full width */}
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

                  {/* Annotation bar — compact row */}
                  {result.processing_status === 'completed' && (
                    <div className="bg-primary/5 rounded-lg p-4">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                        <div className="flex-1">
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
                        </div>
                        <a
                          href={`/bowling/result/${attemptId}/annotate`}
                          className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md whitespace-nowrap"
                        >
                          Annotate Frames
                        </a>
                      </div>
                    </div>
                  )}
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
