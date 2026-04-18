import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Upload, Image } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL } from "../config";
import FairwayScope from "../components/FairwayScope";

const GolfUpload: React.FC = () => {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [email, setEmail] = useState<string>("");
  const [courseName, setCourseName] = useState<string>("");
  const [slopeRating, setSlopeRating] = useState<string>("113");
  const [courseRating, setCourseRating] = useState<string>("72");
  const [playedAt, setPlayedAt] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (file.size > 20 * 1024 * 1024) {
        setError("Image must be under 20MB");
        return;
      }
      setSelectedFile(file);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(URL.createObjectURL(file));
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("image/")) {
      if (file.size > 20 * 1024 * 1024) {
        setError("Image must be under 20MB");
        return;
      }
      setSelectedFile(file);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(URL.createObjectURL(file));
      setError(null);
    } else {
      setError("Please drop an image file");
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
      setError("Please select a scorecard image");
      return;
    }

    const userId = localStorage.getItem("userId");
    if (!userId && !email) {
      setError("Please enter your email address");
      return;
    }

    if (!courseName.trim()) {
      setError("Please enter the course name");
      return;
    }

    const slope = parseFloat(slopeRating);
    if (isNaN(slope) || slope < 55 || slope > 155) {
      setError("Slope rating must be between 55 and 155");
      return;
    }

    const rating = parseFloat(courseRating);
    if (isNaN(rating) || rating < 55 || rating > 85) {
      setError("Course rating must be between 55 and 85");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("image", selectedFile);
      formData.append("course_name", courseName.trim());
      formData.append("slope_rating", slopeRating);
      formData.append("course_rating", courseRating);
      formData.append("played_at", playedAt);
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
          className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
        >
        <div className="max-w-2xl mx-auto">
          <Link
            to="/golf/leaderboard"
            className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
          >
            <ArrowLeft className="mr-2" size={16} />
            Back to Golf
          </Link>

          <div className="bg-card rounded-lg shadow-lg overflow-hidden">
            <div className="p-6 sm:p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-green-500/10 rounded-lg">
                  <Upload className="w-6 h-6 text-green-500" />
                </div>
                <h1 className="text-2xl font-bold">Upload Scorecard</h1>
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
                      No account needed! Your round will be linked to this email.
                    </p>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium mb-2">Course Name</label>
                  <input
                    type="text"
                    value={courseName}
                    onChange={(e) => setCourseName(e.target.value)}
                    placeholder="e.g. Pebble Beach Golf Links"
                    className="w-full px-3 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Slope Rating</label>
                    <input
                      type="number"
                      value={slopeRating}
                      onChange={(e) => setSlopeRating(e.target.value)}
                      min="55"
                      max="155"
                      step="1"
                      placeholder="55-155"
                      className="w-full px-3 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Course Rating</label>
                    <input
                      type="number"
                      value={courseRating}
                      onChange={(e) => setCourseRating(e.target.value)}
                      min="55"
                      max="85"
                      step="0.1"
                      placeholder="55-85"
                      className="w-full px-3 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Date Played</label>
                  <input
                    type="date"
                    value={playedAt}
                    onChange={(e) => setPlayedAt(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Scorecard Photo</label>
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
                      accept="image/*"
                      onChange={handleFileSelect}
                      className="hidden"
                      id="golf-scorecard-upload"
                    />
                    <label
                      htmlFor="golf-scorecard-upload"
                      className="cursor-pointer flex flex-col items-center"
                    >
                      {previewUrl ? (
                        <img
                          src={previewUrl}
                          alt="Scorecard preview"
                          className="max-h-48 rounded-lg mb-2 object-contain"
                        />
                      ) : (
                        <Image className="w-8 h-8 text-muted-foreground mb-2" />
                      )}
                      <span className="text-muted-foreground">
                        {selectedFile
                          ? selectedFile.name
                          : "Click or drag and drop a scorecard photo"}
                      </span>
                      <span className="text-xs text-muted-foreground mt-1">
                        JPEG, PNG, HEIC up to 20MB
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
                  {isUploading ? (
                    <span className="flex items-center justify-center gap-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-foreground"></div>
                      Analyzing scorecard...
                    </span>
                  ) : (
                    "Upload Scorecard"
                  )}
                </button>
              </form>
            </div>
          </div>
        </div>
        </motion.div>
      </FairwayScope>
    </Layout>
  );
};

export default GolfUpload;
