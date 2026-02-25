import React, { useState, useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Upload, Users } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL } from "../config";
import { BowlingResult } from "../lib/types";

const BowlingChallenge: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [results, setResults] = useState<BowlingResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [email, setEmail] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Active processing state (for the just-uploaded result)
  const [activeAttemptId, setActiveAttemptId] = useState<string | null>(null);
  const [activeResult, setActiveResult] = useState<BowlingResult | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchResults = async () => {
    try {
      const response = await axios.get(`${API_URL}/bowling/results?competition_id=${id}`);
      setResults(Array.isArray(response.data) ? response.data : response.data.results || []);
    } catch (err: any) {
      console.error("Error fetching bowling results:", err);
      setError(
        err.response?.data?.error ||
        err.message ||
        "Failed to load bowling results"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, [id]);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  // Poll for active result
  useEffect(() => {
    if (!activeAttemptId) return;

    const poll = async () => {
      try {
        const response = await axios.get(`${API_URL}/bowling/result/${activeAttemptId}`);
        setActiveResult(response.data);
        if (response.data.processing_status === "completed" || response.data.processing_status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          // Refresh the results list to include the new result
          fetchResults();
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
  }, [activeAttemptId]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadError(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("video/")) {
      setSelectedFile(file);
      setUploadError(null);
    } else {
      setUploadError("Please drop a video file");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError("Please select a video file");
      return;
    }

    const userId = localStorage.getItem("userId");
    if (!userId && !email) {
      setUploadError("Please enter your email address");
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      const formData = new FormData();
      formData.append("video", selectedFile);
      if (userId) {
        formData.append("user_id", userId);
      } else {
        formData.append("email", email);
      }
      formData.append("competition_id", id || "");

      const response = await axios.post(`${API_URL}/bowling/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      // Start polling for this result
      setActiveAttemptId(response.data.attempt_id);
      setActiveResult(null);
      setSelectedFile(null);
    } catch (err: any) {
      console.error("Upload error:", err);
      let errorMsg = "Upload failed";
      if (err.response?.data?.error) {
        errorMsg = `${errorMsg}: ${err.response.data.error}`;
      }
      setUploadError(errorMsg);
    } finally {
      setIsUploading(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-4xl mx-auto">
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
          <div className="max-w-4xl mx-auto">
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-500">
              {error}
            </div>
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
        <div className="max-w-4xl mx-auto">
          <Link
            to="/challenges"
            className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
          >
            <ArrowLeft className="mr-2" size={16} />
            Back to Challenges
          </Link>

          {/* Header */}
          <div className="bg-card rounded-lg shadow-lg overflow-hidden mb-8">
            <div className="p-6 sm:p-8">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
                <h1 className="text-3xl font-bold mb-4 sm:mb-0">Bowling Challenge</h1>
                <div className="flex items-center text-muted-foreground">
                  <Users className="mr-2" size={16} />
                  <span>{results.length} submission{results.length !== 1 ? "s" : ""}</span>
                </div>
              </div>

              {/* Upload Form */}
              <div className="bg-blue-500/5 rounded-lg p-6 border border-blue-500/10">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-blue-500/10 rounded-lg">
                    <Upload className="w-5 h-5 text-blue-500" />
                  </div>
                  <h2 className="text-xl font-semibold">Upload Your Bowling Video</h2>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  {!localStorage.getItem("userId") && (
                    <div>
                      <label className="block text-sm font-medium mb-1">Email Address</label>
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
                    <label className="block text-sm font-medium mb-1">Video</label>
                    <div
                      onDrop={handleDrop}
                      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                      onDragLeave={() => setIsDragging(false)}
                      className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
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
                        <Upload className="w-6 h-6 text-muted-foreground mb-2" />
                        <span className="text-sm text-muted-foreground">
                          {selectedFile
                            ? selectedFile.name
                            : "Click or drag and drop a bowling video"}
                        </span>
                      </label>
                    </div>
                  </div>

                  {uploadError && (
                    <div className="text-red-500 text-sm">{uploadError}</div>
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

          {/* Active Processing Result */}
          {activeAttemptId && (
            <div className="bg-card rounded-lg shadow-lg overflow-hidden mb-8">
              <div className="p-6 sm:p-8">
                {!activeResult || activeResult.processing_status === "queued" ? (
                  <div className="text-center py-4">
                    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary mx-auto mb-3"></div>
                    <h3 className="text-lg font-semibold mb-1">Queued...</h3>
                    <p className="text-sm text-muted-foreground">Your bowling video is waiting to be processed.</p>
                  </div>
                ) : activeResult.processing_status === "processing" ? (
                  <div className="text-center py-4">
                    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500 mx-auto mb-3"></div>
                    <h3 className="text-lg font-semibold mb-1">Processing your bowling video...</h3>
                    <p className="text-sm text-muted-foreground">This usually takes a minute or two.</p>
                  </div>
                ) : activeResult.processing_status === "failed" ? (
                  <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-500">
                    <h3 className="font-semibold mb-1">Processing Failed</h3>
                    <p className="text-sm">{activeResult.error_message || "An unexpected error occurred."}</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <h3 className="text-xl font-bold">Your Results</h3>

                    {activeResult.debug_video_url && (
                      <div>
                        <h4 className="text-sm font-semibold mb-2 text-muted-foreground">Debug Video</h4>
                        <video
                          src={activeResult.debug_video_url}
                          controls
                          autoPlay
                          muted
                          className="w-full rounded-lg"
                        />
                      </div>
                    )}

                    {activeResult.trajectory_png_url && (
                      <div>
                        <h4 className="text-sm font-semibold mb-2 text-muted-foreground">Trajectory</h4>
                        <img
                          src={activeResult.trajectory_png_url}
                          alt="Ball trajectory"
                          className="w-full rounded-lg"
                        />
                      </div>
                    )}

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      {activeResult.board_at_pins != null && (
                        <div className="bg-primary/5 rounded-lg p-3 text-center">
                          <div className="text-xl font-bold text-primary">{activeResult.board_at_pins}</div>
                          <div className="text-xs text-muted-foreground">Board at Pins</div>
                        </div>
                      )}
                      {activeResult.entry_board != null && (
                        <div className="bg-primary/5 rounded-lg p-3 text-center">
                          <div className="text-xl font-bold text-primary">{activeResult.entry_board}</div>
                          <div className="text-xs text-muted-foreground">Entry Board</div>
                        </div>
                      )}
                      {activeResult.detection_rate != null && (
                        <div className="bg-primary/5 rounded-lg p-3 text-center">
                          <div className="text-xl font-bold text-primary">{activeResult.detection_rate.toFixed(1)}%</div>
                          <div className="text-xs text-muted-foreground">Detection Rate</div>
                        </div>
                      )}
                      {activeResult.processing_time_s != null && (
                        <div className="bg-primary/5 rounded-lg p-3 text-center">
                          <div className="text-xl font-bold text-primary">{activeResult.processing_time_s.toFixed(1)}s</div>
                          <div className="text-xs text-muted-foreground">Processing Time</div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* All Results Grid */}
          <h2 className="text-2xl font-bold mb-4">All Submissions</h2>
          {results.length === 0 && !activeAttemptId ? (
            <div className="bg-card rounded-lg shadow-lg p-8 text-center">
              <p className="text-muted-foreground">
                No bowling results yet. Be the first to upload!
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {results.map((result) => (
                <Link
                  key={result.attempt_id}
                  to={`/bowling/result/${result.attempt_id}`}
                  className="bg-card rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow"
                >
                  {result.trajectory_png_url ? (
                    <img
                      src={result.trajectory_png_url}
                      alt="Trajectory"
                      className="w-full h-48 object-cover"
                    />
                  ) : (
                    <div className="w-full h-48 bg-muted flex items-center justify-center">
                      {result.processing_status === "completed" ? (
                        <span className="text-muted-foreground text-sm">No trajectory</span>
                      ) : result.processing_status === "failed" ? (
                        <span className="text-red-400 text-sm">Failed</span>
                      ) : (
                        <div className="flex flex-col items-center">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-2"></div>
                          <span className="text-muted-foreground text-sm">Processing...</span>
                        </div>
                      )}
                    </div>
                  )}
                  <div className="p-4">
                    {result.user_name && (
                      <h3 className="font-semibold mb-1">{result.user_name}</h3>
                    )}
                    <div className="flex justify-between text-sm text-muted-foreground">
                      {result.board_at_pins != null && (
                        <span>Board: {result.board_at_pins}</span>
                      )}
                      {result.detection_rate != null && (
                        <span>{result.detection_rate.toFixed(1)}% detected</span>
                      )}
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {result.processing_status === "completed"
                        ? "Completed"
                        : result.processing_status === "failed"
                        ? "Failed"
                        : "Processing..."}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </Layout>
  );
};

export default BowlingChallenge;
