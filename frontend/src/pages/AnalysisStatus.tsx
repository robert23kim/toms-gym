import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, Link, useLocation, useSearchParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowLeft, CheckCircle2, Loader2, Mail, XCircle } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL } from "../config";
import { getChallengeLeaderboard } from "../lib/api";
import type { ChallengeLeaderboard } from "../lib/types";
import { deriveStanding, personalBest, attemptScore, metricForLift, formatWithUnit } from "../lib/standing";
import ResultLadder from "../components/challenge/ResultLadder";
import ConsistencyResult from "../components/challenge/ConsistencyResult";
import { cleanRepCount, isQualityScoredLift } from "../lib/cleanReps";
import { getUserId } from "../lib/identity";
import LiftTypeLine from "../components/challenge/LiftTypeLine";
import { autoLiftTypeEnabled, isAutoLiftType, offersAutomatic, pickLiftTypeFields, type LiftTypeFields } from "../lib/autoLiftType";

// T8 — Post-upload status page. Survives reload via its URL (attemptId is in the
// path) and polls the existing per-attempt result endpoints. Covers LIFTING and
// BOWLING; golf review is synchronous so it has no status page.

type AnalysisKind = "lifting" | "bowling";

type ProcessingStatus = "queued" | "processing" | "completed" | "failed";

interface StatusResult extends LiftTypeFields {
  processing_status: ProcessingStatus;
  error_message?: string | null;
  user_id?: string | null;
  competition_id?: string | null;
  attempt_created_at?: string | null;
  report?: {
    total_reps?: number | null;
    total_in_plank_s?: number | null;
    overall_grade?: string | null;
    lift_type?: string | null;
    rep_metrics?: { form_score?: number | null }[] | null;
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
  const userId = getUserId();
  const [searchParams] = useSearchParams();
  const challengeParam = searchParams.get("challenge");
  const [board, setBoard] = useState<ChallengeLeaderboard | null>(null);
  const reduceMotion = useReducedMotion();
  const boardId = kind === "lifting" ? result?.competition_id || challengeParam : null;
  // A challenge upload goes back to that board's own form, never the generic page (competition '1').
  const uploadPath = kind === "lifting" && challengeParam
    ? `/challenges/${encodeURIComponent(challengeParam)}?upload=1`
    : config.uploadPath;

  useEffect(() => {
    if (!boardId) return;
    let cancelled = false;
    getChallengeLeaderboard(boardId)
      .then((b) => { if (!cancelled) setBoard(b); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [boardId, status]);

  const [autoEnabled, setAutoEnabled] = useState(false);
  useEffect(() => {
    if (!boardId) return;
    let cancelled = false;
    axios
      .get(`${API_URL}/competitions/${boardId}`)
      .then((r) => { if (!cancelled) setAutoEnabled(autoLiftTypeEnabled(r.data)); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [boardId]);
  const location = useLocation();

  const leader = board?.rows[0] && board.rows[0].score > 0 ? board.rows[0] : null;

  const liftLine = pickLiftTypeFields(result);
  const candidates = board?.lift_types ?? [];
  const viewerOwns = !!userId && !!result?.user_id && String(userId) === String(result.user_id);
  const restartPolling = () => {
    startedAtRef.current = Date.now();
    setElapsedS(0);
    if (!pollRef.current) pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
  };
  const handleLiftTypeRequeued = (liftType: string) => {
    setResult((r) =>
      r
        ? { ...r, processing_status: "queued", report: null, lift_type: liftType, lift_type_source: "user", lift_type_confidence: null, needs_lift_type: false }
        : r,
    );
    restartPolling();
  };
  const uncounted = kind === "lifting" && status === "completed" && isAutoLiftType(liftLine.liftType);
  const renderLiftLine = (prominent = false) =>
    kind === "lifting" && liftLine.present && attemptId && !!board && offersAutomatic(autoEnabled, candidates, board.metric) ? (
      <LiftTypeLine
        attemptId={attemptId}
        viewerId={userId}
        isOwner={viewerOwns}
        candidates={candidates}
        liftType={liftLine.liftType}
        source={liftLine.source}
        confidence={liftLine.confidence}
        needsLiftType={liftLine.needsLiftType}
        onRequeued={handleLiftTypeRequeued}
        findProfileHref={`/find-profile?next=${encodeURIComponent(location.pathname + location.search)}`}
        prominent={prominent}
        className="justify-center"
      />
    ) : null;

  const renderReveal = () => {
    if (kind !== "lifting" || !result?.report || isAutoLiftType(result.report.lift_type)) return null;
    const club = board?.metric === "consistency" ? board : null;
    const liftMetric = metricForLift(result.report.lift_type);
    const metric = club ? (liftMetric === "time" ? "time" : "reps") : board?.metric ?? liftMetric;
    const score = club
      ? metric === "time"
        ? result.report.total_in_plank_s ?? null
        : result.report.total_reps ?? null
      : attemptScore(metric, result.report, null);
    const grade = result.report.overall_grade;
    if (score == null && !grade) return null;
    const standing = !club && board && result.user_id ? deriveStanding(board, result.user_id) : null;
    const clean = club && metric === "reps" && isQualityScoredLift(result.report.lift_type)
      ? cleanRepCount(result.report.rep_metrics)
      : null;
    const total = result.report.total_reps ?? null;
    const halfCredit = clean != null && total != null && clean < total;
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
          {halfCredit && (
            <p className="mt-1 text-sm text-muted-foreground tabular-nums">
              {clean} clean of {total} · sloppy reps count half
            </p>
          )}
          {renderLiftLine()}
        </motion.div>
        {club && (
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-left mb-6"
          >
            <ConsistencyResult
              board={club}
              userId={result.user_id}
              report={result.report}
              attemptAt={result.attempt_created_at}
              isOwner={!userId || !result.user_id || String(userId) === String(result.user_id)}
            />
          </motion.div>
        )}
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
                    to={uploadPath}
                    className="inline-block w-full bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90 text-center"
                  >
                    Upload Again
                  </Link>
                </div>
              ) : status === "completed" ? (
                <div className="text-center">
                  {uncounted ? (
                    <>
                      <h1 className="text-2xl font-bold mb-2">Which lift was this?</h1>
                      <p className="text-muted-foreground mb-6">
                        {viewerOwns
                          ? "We couldn't tell from the video. Pick one and we'll count it."
                          : "We couldn't tell from the video, so it isn't counted yet."}
                      </p>
                      {renderLiftLine(true) && <div className="mb-3">{renderLiftLine(true)}</div>}
                    </>
                  ) : renderReveal() ?? (
                    <>
                      <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
                      <h1 className="text-2xl font-bold mb-2">Analysis complete!</h1>
                      <p className="text-muted-foreground mb-6">
                        Your results are ready to view.
                      </p>
                      {renderLiftLine() && <div className="-mt-4 mb-6">{renderLiftLine()}</div>}
                    </>
                  )}
                  <div className="flex flex-col gap-3">
                    {config.resultPath(attemptId ?? "", result) ? (
                      <Link
                        to={config.resultPath(attemptId ?? "", result) as string}
                        className={
                          uncounted && viewerOwns && autoEnabled
                            ? "w-full bg-secondary text-secondary-foreground py-2 px-4 rounded-lg hover:bg-secondary/90 text-center"
                            : "w-full bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90 text-center"
                        }
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
                      to={uploadPath}
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
                          {` · ${board.rows.length} ${board.rows.length === 1 ? "athlete" : "athletes"} on the board`}
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
