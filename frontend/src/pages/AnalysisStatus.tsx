import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowLeft, CheckCircle2, Loader2, Mail, XCircle } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL } from "../config";
import { getChallengeLeaderboard } from "../lib/api";
import type { ChallengeLeaderboard } from "../lib/types";
import { deriveStanding, personalBest, attemptScore, metricForLift, formatWithUnit } from "../lib/standing";
import ResultLadder from "../components/challenge/ResultLadder";

// T8 — Post-upload status page. Survives reload via its URL (attemptId is in the
// path) and polls the existing per-attempt result endpoints. Covers LIFTING and
// BOWLING; golf review is synchronous so it has no status page.

type AnalysisKind = "lifting" | "bowling";

type ProcessingStatus = "queued" | "processing" | "completed" | "failed";

interface StatusResult {
  processing_status: ProcessingStatus;
  error_message?: string | null;
  user_id?: string | null;
  competition_id?: string | null;
  report?: {
    total_reps?: number | null;
    total_in_plank_s?: number | null;
    overall_grade?: string | null;
    lift_type?: string | null;
  } | null;
  // Lifting
  annotated_video_url?: string | null;
  // Bowling
  debug_video_url?: string | null;
  trajectory_png_url?: string | null;
}

interface KindConfig {
  label: string; // e.g. "your lift"
  resultEndpoint: (id: string) => string;
  resultPath: (id: string, result: StatusResult | null) => string | null;
  uploadPath: string;
  backPath: string;
  backLabel: string;
}

const KIND_CONFIG: Record<AnalysisKind, KindConfig> = {
  lifting: {
    label: "your lift",
    resultEndpoint: (id) => `${API_URL}/lifting/result/${id}`,
    resultPath: (id, result) =>
      result?.competition_id && result?.user_id
        ? `/challenges/${result.competition_id}/participants/${result.user_id}/video/${id}`
        : null,
    uploadPath: "/lift/upload",
    backPath: "/lift",
    backLabel: "Back to Lift",
  },
  bowling: {
    label: "your bowling video",
    resultEndpoint: (id) => `${API_URL}/bowling/result/${id}`,
    resultPath: (id) => `/bowling/result/${id}`,
    uploadPath: "/bowling/upload",
    backPath: "/bowl",
    backLabel: "Back to Bowl",
  },
};

const POLL_INTERVAL_MS = 4000;

interface AnalysisStatusProps {
  kind: AnalysisKind;
}

const AnalysisStatus: React.FC<AnalysisStatusProps> = ({ kind }) => {
  const { attemptId } = useParams<{ attemptId: string }>();
  const config = KIND_CONFIG[kind];
  const [result, setResult] = useState<StatusResult | null>(null);
  const [elapsedS, setElapsedS] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startedAtRef = useRef<number>(Date.now());

  const isDone = (s?: ProcessingStatus) => s === "completed" || s === "failed";

  const poll = useCallback(async () => {
    if (!attemptId) return;
    try {
      const response = await axios.get<StatusResult>(config.resultEndpoint(attemptId));
      setResult(response.data);
      if (isDone(response.data.processing_status) && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } catch (err) {
      // A 404 just means the result row isn't created yet — keep polling and
      // keep showing the "queued" state. Any other transient error: keep going.
      if (!axios.isAxiosError(err) || err.response?.status !== 404) {
        console.error("Error polling analysis status:", err);
      }
    }
  }, [attemptId, config]);

  useEffect(() => {
    startedAtRef.current = Date.now();
    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    const elapsedTimer = setInterval(
      () => setElapsedS(Math.floor((Date.now() - startedAtRef.current) / 1000)),
      1000
    );
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      clearInterval(elapsedTimer);
    };
  }, [poll]);

  const status: ProcessingStatus = result?.processing_status ?? "queued";
  const userId = localStorage.getItem("userId");
  const [searchParams] = useSearchParams();
  const challengeParam = searchParams.get("challenge");
  const [board, setBoard] = useState<ChallengeLeaderboard | null>(null);
  const reduceMotion = useReducedMotion();
  const boardId = kind === "lifting" ? result?.competition_id || challengeParam : null;

  useEffect(() => {
    if (!boardId) return;
    let cancelled = false;
    getChallengeLeaderboard(boardId)
      .then((b) => { if (!cancelled) setBoard(b); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [boardId, status]);

  const leader = board?.rows[0] && board.rows[0].score > 0 ? board.rows[0] : null;

  const renderReveal = () => {
    if (kind !== "lifting" || !result?.report) return null;
    const metric = board?.metric ?? metricForLift(result.report.lift_type);
    const score = attemptScore(metric, result.report, null);
    const grade = result.report.overall_grade;
    if (score == null && !grade) return null;
    const standing = board && result.user_id ? deriveStanding(board, result.user_id) : null;
    return (
      <>
        <motion.div
          initial={reduceMotion ? false : { scale: 1.15, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 260, damping: 20 }}
          className="mb-6"
        >
          <p className="text-xs uppercase tracking-widest text-muted-foreground mb-3">
            Your {result.report.lift_type || "lift"}
          </p>
          <h1 className="text-6xl font-bold tabular-nums leading-none">
            {score != null ? formatWithUnit(score, metric) : `Grade ${grade}`}
          </h1>
          {score != null && grade && (
            <p className="mt-3 text-muted-foreground">
              Grade <span className="font-semibold text-foreground">{grade}</span>
            </p>
          )}
        </motion.div>
        {standing && board && (
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-left mb-6"
          >
            <ResultLadder
              standing={standing}
              personalBest={personalBest(standing, score)}
              metric={metric}
              athleteName={standing.row.name}
              isOwner
              challengeId={board.competition_id}
              challengeOpen={false}
            />
          </motion.div>
        )}
      </>
    );
  };

  const renderElapsed = () => {
    const mins = Math.floor(elapsedS / 60);
    const secs = elapsedS % 60;
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
      >
        <div className="max-w-2xl mx-auto">
          <Link
            to={config.backPath}
            className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
          >
            <ArrowLeft className="mr-2" size={16} />
            {config.backLabel}
          </Link>

          <div className="bg-card rounded-lg shadow-lg overflow-hidden">
            <div className="p-6 sm:p-8">
              {status === "failed" ? (
                <div className="text-center">
                  <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                  <h1 className="text-2xl font-bold mb-2">Analysis failed</h1>
                  <p className="text-muted-foreground mb-6">
                    {result?.error_message ||
                      "Something went wrong while analyzing your video. Please try uploading again."}
                  </p>
                  <Link
                    to={config.uploadPath}
                    className="inline-block w-full bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90 text-center"
                  >
                    Upload Again
                  </Link>
                </div>
              ) : status === "completed" ? (
                <div className="text-center">
                  {renderReveal() ?? (
                    <>
                      <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
                      <h1 className="text-2xl font-bold mb-2">Analysis complete!</h1>
                      <p className="text-muted-foreground mb-6">
                        Your results are ready to view.
                      </p>
                    </>
                  )}
                  <div className="flex flex-col gap-3">
                    {config.resultPath(attemptId ?? "", result) ? (
                      <Link
                        to={config.resultPath(attemptId ?? "", result) as string}
                        className="w-full bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90 text-center"
                      >
                        See your result
                      </Link>
                    ) : (
                      <Link
                        to={userId ? `/profile/${userId}` : "/"}
                        className="w-full bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90 text-center"
                      >
                        View Your Profile
                      </Link>
                    )}
                    <Link
                      to={config.uploadPath}
                      className="w-full bg-secondary text-secondary-foreground py-2 px-4 rounded-lg hover:bg-secondary/90 text-center"
                    >
                      Upload Another
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="text-center">
                  <Loader2 className="w-12 h-12 text-primary mx-auto mb-4 animate-spin" />
                  <h1 className="text-2xl font-bold mb-2">
                    {status === "processing"
                      ? `Analyzing ${config.label}…`
                      : "Queued for analysis"}
                  </h1>
                  <p className="text-muted-foreground mb-2">
                    {status === "processing"
                      ? "Our AI is breaking down your video frame by frame."
                      : `${config.label.charAt(0).toUpperCase() + config.label.slice(1)} is in line to be analyzed.`}
                  </p>
                  <p className="text-sm text-muted-foreground mb-6">
                    This usually takes about 2 minutes. Longer videos (like planks)
                    can take up to 10 minutes.
                  </p>

                  {board && (
                    <p className="text-sm text-muted-foreground mb-6">
                      {leader ? (
                        <>
                          <span className="font-semibold text-foreground">{leader.name || "Someone"}</span>
                          {" leads at "}
                          <span className="font-semibold text-foreground">{formatWithUnit(leader.score, board.metric)}</span>
                          {` · ${board.rows.length} on the board`}
                        </>
                      ) : (
                        "Nobody on the board yet — you're first in."
                      )}
                    </p>
                  )}

                  <div className="bg-muted/50 rounded-lg p-4 text-sm text-muted-foreground mb-6">
                    <div className="flex items-center justify-center gap-2 mb-1">
                      <Mail className="w-4 h-4" />
                      <span>We'll email you a link when it's ready.</span>
                    </div>
                    <p className="text-xs">
                      You can safely close this page — this link keeps your place
                      and updates automatically.
                    </p>
                  </div>

                  <p className="text-xs text-muted-foreground">
                    Elapsed: {renderElapsed()} · checking every few seconds…
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default AnalysisStatus;
