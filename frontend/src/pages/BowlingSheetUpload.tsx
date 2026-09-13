import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import axios from "axios";
import { ArrowLeft, Camera, ImageIcon } from "lucide-react";
import Layout from "../components/Layout";
import { useMediaUpload } from "../hooks/useMediaUpload";
import { uploadBowlingSheet, BowlingSheetType } from "../lib/api";
import { buildSheetForm } from "../lib/bowlingSheetForm";
import { todayLocal } from "../lib/dates";

const MAX_BYTES = 20 * 1024 * 1024;

const SHEET_TYPES: { value: BowlingSheetType; label: string; hint: string }[] = [
  { value: "night", label: "Night results", hint: "The end-of-night totals screen." },
  { value: "game", label: "Single game", hint: "One game's frame-by-frame lane screen." },
];

const uploadErrorMessage = (err: unknown): string => {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { error?: string } | undefined)?.error;
    if (detail) return `Upload failed: ${detail}`;
    if (err.response?.status) return `Upload failed with status ${err.response.status}`;
  }
  return "Upload failed";
};

const BowlingSheetUpload: React.FC<{ autoCamera?: boolean }> = ({ autoCamera = false }) => {
  const navigate = useNavigate();
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const [email, setEmail] = useState("");
  const [sheetType, setSheetType] = useState<BowlingSheetType>("night");
  const [playedOn, setPlayedOn] = useState(() => todayLocal());
  const [isUploading, setIsUploading] = useState(false);
  const storedUserId = localStorage.getItem("userId");

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
  } = useMediaUpload({ accept: "image", maxBytes: MAX_BYTES });

  useEffect(() => {
    // /bowling/snap fast path — browsers that require a user gesture ignore
    // this and the "Take photo" button still works.
    if (autoCamera) cameraInputRef.current?.click();
  }, [autoCamera]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please select a score sheet photo");
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
      const sheet = await uploadBowlingSheet(
        buildSheetForm(selectedFile, { sheetType, playedOn, userId, email }),
      );
      navigate(`/bowling/scoresheet/${sheet.sheet_id}`);
    } catch (err) {
      setError(uploadErrorMessage(err));
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-2xl mx-auto py-6 px-4"
      >
        <Link
          to="/bowl"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-6"
        >
          <ArrowLeft className="mr-2" size={16} />
          Back to Bowl
        </Link>

        <div className="glass rounded-2xl p-6 sm:p-8 space-y-6">
          <div>
            <h1 className="text-2xl font-semibold">Snap a score sheet</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Photograph the screen at the end of the night. Every game gets read
              off the picture — you check it on the next screen.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <fieldset>
              <legend className="block text-sm font-medium mb-2">What did you shoot?</legend>
              <div className="grid grid-cols-2 gap-2.5">
                {SHEET_TYPES.map((option) => (
                  <label
                    key={option.value}
                    className={`cursor-pointer rounded-xl border px-4 py-3 text-left transition-colors ${
                      sheetType === option.value
                        ? "border-accent bg-accent/10"
                        : "border-input hover:bg-secondary/40"
                    }`}
                  >
                    <input
                      type="radio"
                      name="sheet_type"
                      value={option.value}
                      checked={sheetType === option.value}
                      onChange={() => setSheetType(option.value)}
                      className="sr-only"
                    />
                    <span className="block font-medium text-sm">{option.label}</span>
                    <span className="block text-xs text-muted-foreground mt-0.5">
                      {option.hint}
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>

            <div>
              <label htmlFor="bowling-sheet-date" className="block text-sm font-medium mb-1.5">
                Date bowled
              </label>
              <input
                id="bowling-sheet-date"
                type="date"
                value={playedOn}
                onChange={(e) => setPlayedOn(e.target.value)}
                className="w-full px-3 h-10 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>

            {!storedUserId && (
              <div>
                <label htmlFor="bowling-sheet-email" className="block text-sm font-medium mb-1.5">
                  Email
                </label>
                <input
                  id="bowling-sheet-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full px-3 h-10 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  No account needed — your games are linked to this email.
                </p>
              </div>
            )}

            <div>
              <span className="block text-sm font-medium mb-1.5">Score sheet photo</span>
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                className={`rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
                  isDragging ? "border-accent bg-accent/5" : "border-input"
                }`}
              >
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="bowling-sheet-upload"
                />
                <input
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="bowling-sheet-camera"
                  ref={cameraInputRef}
                />

                {previewUrl ? (
                  <img
                    src={previewUrl}
                    alt="Score sheet preview"
                    className="max-h-56 rounded-lg mb-3 object-contain mx-auto"
                  />
                ) : (
                  <p className="text-sm text-muted-foreground mb-4">
                    Fill the frame with the screen, keep it square on, avoid glare.
                  </p>
                )}

                <div className="flex gap-2.5 justify-center flex-wrap">
                  <button
                    type="button"
                    onClick={() => document.getElementById("bowling-sheet-upload")?.click()}
                    className="inline-flex items-center gap-2 h-10 px-4 rounded-lg border border-input bg-background text-sm hover:bg-secondary/40"
                  >
                    <ImageIcon className="w-4 h-4" />
                    Choose existing photo
                  </button>
                  <button
                    type="button"
                    onClick={() => cameraInputRef.current?.click()}
                    className="inline-flex items-center gap-2 h-10 px-4 rounded-lg bg-accent text-accent-foreground text-sm hover:bg-accent/90"
                  >
                    <Camera className="w-4 h-4" />
                    Take photo
                  </button>
                </div>

                {selectedFile && (
                  <p className="text-xs text-muted-foreground mt-3">{selectedFile.name}</p>
                )}
              </div>
            </div>

            {error && (
              <div className="text-sm text-destructive bg-destructive/10 border border-destructive/30 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isUploading || !selectedFile}
              className="w-full h-11 rounded-lg bg-accent text-accent-foreground font-medium text-sm hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUploading ? "Reading…" : "Read score sheet"}
            </button>
          </form>
        </div>
      </motion.div>
    </Layout>
  );
};

export default BowlingSheetUpload;
