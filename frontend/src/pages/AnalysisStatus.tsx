import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, CheckCircle2, Loader2, Mail, XCircle } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL } from "../config";

// T8 — Post-upload status page. Survives reload via its URL (attemptId is in the
// path) and polls the existing per-attempt result endpoints. Covers LIFTING and
// BOWLING; golf review is synchronous so it has no status page.

type AnalysisKind = "lifting" | "bowling";

type ProcessingStatus = "queued" | "processing" | "completed" | "failed";

interface StatusResult {
  processing_status: ProcessingStatus;
  error_message?: string | null;
  // Lifting
  annotated_video_url?: string | null;
  // Bowling
  debug_video_url?: string | null;
  trajectory_png_url?: string | null;
}

interface KindConfig {
  label: string; // e.g. "your lift"
  resultEndpoint: (id: string) => string;
  resultPath: (id: string) => string | null; // dedicated result page, if any
  uploadPath: string;
  backPath: string;
  backLabel: string;
}

const KIND_CONFIG: Record<AnalysisKind, KindConfig> = {
  lifting: {
    label: "your lift",
    resultEndpoint: (id) => `${API_URL}/lifting/result/${id}`,
    resultPath: () => null, // no dedicated lifting result page; link to profile
    uploadPath: "/upload",
    backPath: "/",
    backLabel: "Back to Home",
  },
  bowling: {
    label: "your bowling video",
    resultEndpoint: (id) => `${API_URL}/bowling/result/${id}`,
    resultPath: (id) => `/bowling/result/${id}`,
    uploadPath: "/bowling/upload",
    backPath: "/",
    backLabel: "Back to Home",
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
                  <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
                  <h1 className="text-2xl font-bold mb-2">Analysis complete!</h1>
                  <p className="text-muted-foreground mb-6">
                    Your results are ready to view.
                  </p>
                  <div className="flex flex-col gap-3">
                    {config.resultPath(attemptId ?? "") ? (
                      <Link
                        to={config.resultPath(attemptId ?? "") as string}
                        className="w-full bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90 text-center"
                      >
                        View Full Result
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
