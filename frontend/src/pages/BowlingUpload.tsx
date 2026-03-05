import React, { useState, useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Upload } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL } from "../config";
import { BowlingResult } from "../lib/types";

const BowlingUpload: React.FC = () => {
  const { competitionId } = useParams<{ competitionId: string }>();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [email, setEmail] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Polling state
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [result, setResult] = useState<BowlingResult | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  useEffect(() => {
    if (!attemptId) return;

    const poll = async () => {
      try {
        const response = await axios.get(`${API_URL}/bowling/result/${attemptId}`);
        setResult(response.data);
        if (response.data.processing_status === "completed" || response.data.processing_status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch (err) {
        console.error("Error polling result:", err);
      }
    };

    poll();
    pollRef.current = setInterval(poll, 3000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [attemptId]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("video/")) {
      setSelectedFile(file);
      setError(null);
    } else {
      setError("Please drop a video file");
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please select a video file");
      return;
    }

    const userId = localStorage.getItem("userId");
    if (!userId && !email) {
      setError("Please enter your email address");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("video", selectedFile);
      if (userId) {
        formData.append("user_id", userId);
      } else {
        formData.append("email", email);
      }
      if (competitionId) {
        formData.append("competition_id", competitionId);
      }

      const response = await axios.post(`${API_URL}/bowling/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setAttemptId(response.data.attempt_id);
    } catch (err: any) {
      console.error("Upload error:", err);
      let errorMsg = "Upload failed";
      if (err.response?.data?.error) {
        errorMsg = `${errorMsg}: ${err.response.data.error}`;
      } else if (err.response?.status) {
        errorMsg = `${errorMsg} with status ${err.response.status}`;
      }
      setError(errorMsg);
    } finally {
      setIsUploading(false);
    }
  };

  // Polling / result view
  if (attemptId) {
    return (
      <Layout>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
        >
          <div className="max-w-2xl mx-auto">
            {!result || result.processing_status === "queued" ? (
              <div className="bg-card rounded-lg shadow-lg p-8 text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
                <h2 className="text-xl font-semibold mb-2">Queued...</h2>
                <p className="text-muted-foreground">Your bowling video is waiting to be processed.</p>
              </div>
            ) : result.processing_status === "processing" ? (
              <div className="bg-card rounded-lg shadow-lg p-8 text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <h2 className="text-xl font-semibold mb-2">Processing your bowling video...</h2>
                <p className="text-muted-foreground">This usually takes a minute or two.</p>
              </div>
            ) : result.processing_status === "failed" ? (
              <div className="bg-card rounded-lg shadow-lg p-8">
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-500 mb-4">
                  <h2 className="text-xl font-semibold mb-2">Processing Failed</h2>
                  <p>{result.error_message || "An unexpected error occurred."}</p>
                </div>
                <button
                  onClick={() => {
                    setAttemptId(null);
                    setResult(null);
                    setSelectedFile(null);
                  }}
                  className="w-full bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90"
                >
                  Try Again
                </button>
              </div>
            ) : (
              <div className="bg-card rounded-lg shadow-lg p-6 sm:p-8 space-y-6">
                <h2 className="text-2xl font-bold">Results</h2>

                {result.debug_video_url && (
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
                )}

                {result.trajectory_png_url && (
                  <div>
                    <h3 className="text-lg font-semibold mb-2">Trajectory</h3>
                    <img
                      src={result.trajectory_png_url}
                      alt="Ball trajectory"
                      className="w-full rounded-lg"
                    />
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  {result.board_at_pins != null && (
                    <div className="bg-primary/5 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-primary">{result.board_at_pins}</div>
                      <div className="text-sm text-muted-foreground">Board at Pins</div>
                    </div>
                  )}
                  {result.entry_board != null && (
                    <div className="bg-primary/5 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-primary">{result.entry_board}</div>
                      <div className="text-sm text-muted-foreground">Entry Board</div>
                    </div>
                  )}
                  {result.detection_rate != null && (
                    <div className="bg-primary/5 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-primary">{(result.detection_rate * 100).toFixed(1)}%</div>
                      <div className="text-sm text-muted-foreground">Detection Rate</div>
                    </div>
                  )}
                  {result.processing_time_s != null && (
                    <div className="bg-primary/5 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-primary">{result.processing_time_s.toFixed(1)}s</div>
                      <div className="text-sm text-muted-foreground">Processing Time</div>
                    </div>
                  )}
                </div>

                <Link
                  to={`/bowling/result/${attemptId}`}
                  className="block w-full bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90 text-center"
                >
                  View Full Result
                </Link>
              </div>
            )}
          </div>
        </motion.div>
      </Layout>
    );
  }

  // Upload form view
  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
      >
        <div className="max-w-2xl mx-auto">
          {competitionId ? (
            <Link
              to={`/bowling/challenge/${competitionId}`}
              className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
            >
              <ArrowLeft className="mr-2" size={16} />
              Back to Challenge
            </Link>
          ) : (
            <Link
              to="/"
              className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
            >
              <ArrowLeft className="mr-2" size={16} />
              Back to Home
            </Link>
          )}

          <div className="bg-card rounded-lg shadow-lg overflow-hidden">
            <div className="p-6 sm:p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <Upload className="w-6 h-6 text-blue-500" />
                </div>
                <h1 className="text-2xl font-bold">Upload Bowling Video</h1>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                {!localStorage.getItem("userId") && (
                  <div>
                    <label className="block text-sm font-medium mb-2">Email Address</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="Enter your email to link this upload"
                      className="w-full px-3 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      No account needed! Your video will be linked to this email.
                    </p>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium mb-2">Video</label>
                  <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                      isDragging
                        ? "border-primary bg-primary/5"
                        : "border-input hover:border-primary/50"
                    }`}
                  >
                    <input
                      type="file"
                      accept="video/*"
                      onChange={handleFileSelect}
                      className="hidden"
                      id="bowling-video-upload"
                    />
                    <label
                      htmlFor="bowling-video-upload"
                      className="cursor-pointer flex flex-col items-center"
                    >
                      <Upload className="w-8 h-8 text-muted-foreground mb-2" />
                      <span className="text-muted-foreground">
                        {selectedFile
                          ? selectedFile.name
                          : "Click or drag and drop a bowling video"}
                      </span>
                    </label>
                  </div>
                </div>

                {error && (
                  <div className="text-red-500 text-sm">{error}</div>
                )}

                <button
                  type="submit"
                  disabled={isUploading || !selectedFile}
                  className="w-full bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isUploading ? "Uploading..." : "Upload Video"}
                </button>
              </form>
            </div>
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default BowlingUpload;
