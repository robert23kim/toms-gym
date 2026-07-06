import React, { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Upload } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL } from "../config";
import { useMediaUpload } from "../hooks/useMediaUpload";

const BowlingUpload: React.FC = () => {
  const { competitionId } = useParams<{ competitionId: string }>();
  const navigate = useNavigate();
  const [email, setEmail] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const {
    file: selectedFile,
    isDragging,
    error,
    setError,
    onInputChange: handleFileSelect,
    onDrop: handleDrop,
    onDragOver: handleDragOver,
    onDragLeave: handleDragLeave,
  } = useMediaUpload({ accept: "video", maxBytes: 500 * 1024 * 1024 });

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

      // Analysis is enqueued server-side on upload. Send the user to the status
      // page instead of a dead-end wait; it polls by attempt id and survives
      // reload via its URL (T8).
      navigate(`/bowling/status/${response.data.attempt_id}`);
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
