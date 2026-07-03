import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL } from "../config";
import FairwayScope from "../components/FairwayScope";
import StagedParseProgress from "../components/golf/StagedParseProgress";
import { useMediaUpload } from "../hooks/useMediaUpload";

const GolfUpload: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const {
    file: selectedFile,
    previewUrl,
    isDragging,
    error,
    setError,
    onInputChange: handleFileSelect,
    onDrop: handleDrop,
    onDragOver: handleDragOver,
    onDragLeave: handleDragLeave,
  } = useMediaUpload({ accept: "image", maxBytes: 20 * 1024 * 1024 });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please select a scorecard image");
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
      formData.append("image", selectedFile);
      if (userId) {
        formData.append("user_id", userId);
      } else {
        formData.append("email", email);
      }

      const response = await axios.post(`${API_URL}/golf/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      if (response.data.user_id) {
        localStorage.setItem("userId", response.data.user_id);
      }

      navigate(`/golf/review/${response.data.round_id}`);
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

  return (
    <Layout>
      <FairwayScope>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="min-h-screen py-10 px-4 sm:px-6 lg:px-8"
        >
          <div className="max-w-2xl mx-auto">
            <Link
              to="/golf/leaderboard"
              className="inline-flex items-center fw-text-secondary hover:opacity-80 mb-6 text-sm"
            >
              <ArrowLeft className="mr-2" size={16} />
              Back to Golf
            </Link>

            <div className="fw-surface p-6 sm:p-8 space-y-6">
              <div>
                <h1 className="fw-h1">Log round</h1>
                <p className="fw-text-secondary text-sm mt-1">
                  Snap your scorecard — scores, pars, and tee ratings are read
                  straight off the photo. You confirm on the next screen.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                {!localStorage.getItem("userId") && (
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Email</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      className="w-full px-3 h-9 rounded-md border border-[var(--fw-border-tertiary)] bg-[var(--fw-bg-primary)] text-sm focus:outline-none focus:border-[var(--fw-info)]"
                    />
                    <p className="text-xs fw-text-secondary mt-1">
                      No account needed — your round is linked to this email.
                    </p>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium mb-1.5">Scorecard photo</label>
                  <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    className={`fw-corner-guides rounded-lg p-10 text-center transition-colors ${
                      isDragging
                        ? "border-[var(--fw-info)] bg-[var(--fw-bg-info)]"
                        : "border-[var(--fw-border-tertiary)] bg-[var(--fw-bg-secondary)]"
                    } border-[0.5px] border-dashed`}
                  >
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleFileSelect}
                      className="hidden"
                      id="golf-scorecard-upload"
                    />

                    {previewUrl ? (
                      <img
                        src={previewUrl}
                        alt="Scorecard preview"
                        className="max-h-56 rounded-md mb-3 object-contain mx-auto"
                      />
                    ) : (
                      <p className="fw-text-secondary text-sm mb-4">
                        Lay flat, fill frame, avoid glare.
                      </p>
                    )}

                    <div className="flex gap-3 justify-center flex-wrap">
                      <button
                        type="button"
                        onClick={() => document.getElementById("golf-scorecard-upload")?.click()}
                        className="inline-flex items-center gap-2 h-9 px-4 rounded-md border border-[var(--fw-border-secondary)] bg-[var(--fw-bg-primary)] text-sm cursor-pointer hover:bg-[var(--fw-bg-tertiary)]"
                      >
                        Upload from library
                      </button>
                      <button
                        type="button"
                        onClick={() => document.getElementById("golf-scorecard-upload")?.click()}
                        className="inline-flex items-center gap-2 h-9 px-4 rounded-md bg-[var(--fw-info)] text-white text-sm hover:opacity-90"
                      >
                        Capture photo
                      </button>
                    </div>

                    {selectedFile && (
                      <p className="text-xs fw-text-secondary mt-3">{selectedFile.name}</p>
                    )}
                  </div>
                </div>

                {error && (
                  <div className="text-sm text-[var(--fw-text-danger)] bg-[var(--fw-bg-danger)] border border-[var(--fw-border-warning)] rounded-md px-3 py-2">
                    {error}
                  </div>
                )}

                {isUploading ? (
                  <StagedParseProgress />
                ) : (
                  <button
                    type="submit"
                    disabled={!selectedFile}
                    className="w-full h-10 rounded-md bg-[var(--fw-info)] text-white font-medium text-sm hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Analyse scorecard
                  </button>
                )}
              </form>
            </div>
          </div>
        </motion.div>
      </FairwayScope>
    </Layout>
  );
};

export default GolfUpload;
