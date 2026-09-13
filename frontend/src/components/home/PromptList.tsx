import React, { Fragment, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { ArrowRight, Camera, CircleDot, Dumbbell, Flag, FolderOpen, Trophy, Video } from "lucide-react";
import { Prompt } from "../../lib/prompts";
import { triggerLiftingAnalysis, uploadBowlingSheet } from "../../lib/api";
import { buildSheetForm } from "../../lib/bowlingSheetForm";
import { todayLocal } from "../../lib/dates";
import { uploadVideo } from "../../lib/resumableUpload";
import { useUploadGuard } from "../../lib/useUploadGuard";
import { reportUploadError } from "../../lib/telemetry";

interface Props {
  prompts: Prompt[];
  userId: string | null;
}

const iconFor = (prompt: Prompt): React.ReactNode => {
  if (prompt.id === "bowl-snap") return <CircleDot className="w-5 h-5" />;
  if (prompt.id === "golf-snap") return <Flag className="w-5 h-5" />;
  if (prompt.id === "lift-upload") return <Dumbbell className="w-5 h-5" />;
  return <Trophy className="w-5 h-5" />;
};

const uploadErrorMessage = (err: unknown): string => {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { error?: string } | undefined)?.error;
    if (detail) return `Upload failed: ${detail}`;
    if (err.response?.status) return `Upload failed with status ${err.response.status}`;
  }
  return "Upload failed";
};

const rowClass =
  "group flex items-center gap-3 glass rounded-2xl pl-3 pr-2.5 py-2.5 text-left transition-colors hover:bg-secondary/40";
const chipClass = "w-11 h-11 shrink-0 rounded-xl bg-accent/10 text-accent grid place-items-center";
const primaryAction =
  "shrink-0 w-11 h-11 rounded-xl grid place-items-center bg-accent text-accent-foreground shadow-sm transition-colors hover:bg-accent/90 cursor-pointer";
const secondaryAction =
  "shrink-0 w-11 h-11 rounded-xl grid place-items-center border border-input text-foreground/80 transition-colors hover:bg-secondary/60 cursor-pointer";

interface ActionRowProps {
  icon: React.ReactNode;
  title: string;
  pill?: string;
  status: string | null;
  error: string | null;
  busy: boolean;
  inputs: { id: string; label: string; icon: React.ReactNode; accept: string; capture?: "environment"; primary: boolean }[];
  onFile: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const ActionRow: React.FC<ActionRowProps> = ({ icon, title, pill, status, error, busy, inputs, onFile }) => (
  <div className={rowClass}>
    <span className={chipClass}>{icon}</span>
    <span className="flex-1 min-w-0">
      <span className="block font-medium leading-tight">{status ?? title}</span>
      {pill && !status && (
        <span className="inline-block text-[11px] font-semibold px-2 py-0.5 mt-0.5 rounded-full bg-accent/10 text-accent">
          {pill}
        </span>
      )}
      {error && <span className="block text-xs text-destructive mt-0.5">{error}</span>}
    </span>
    {inputs.map((input) => (
      <Fragment key={input.id}>
        <label
          htmlFor={input.id}
          aria-label={input.label}
          title={input.label}
          className={`${input.primary ? primaryAction : secondaryAction} ${busy ? "opacity-50 pointer-events-none" : ""}`}
        >
          {input.icon}
        </label>
        <input
          id={input.id}
          data-testid={input.id}
          type="file"
          accept={input.accept}
          capture={input.capture}
          className="hidden"
          disabled={busy}
          onChange={onFile}
        />
      </Fragment>
    ))}
  </div>
);

const BowlSnapRow: React.FC<{ prompt: Extract<Prompt, { kind: "camera" }>; userId: string }> = ({ prompt, userId }) => {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const sheet = await uploadBowlingSheet(
        buildSheetForm(file, { sheetType: "night", playedOn: todayLocal(), userId }),
      );
      navigate(`/bowling/scoresheet/${sheet.sheet_id}`);
    } catch (err) {
      setError(uploadErrorMessage(err));
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  };

  return (
    <ActionRow
      icon={iconFor(prompt)}
      title={prompt.title}
      status={busy ? "Reading…" : null}
      error={error}
      busy={busy}
      onFile={onFile}
      inputs={[
        { id: "home-bowl-camera", label: "Take a photo of the score screen", icon: <Camera className="w-5 h-5" />, accept: "image/*", capture: "environment", primary: true },
        { id: "home-bowl-library", label: "Upload a photo of the score screen", icon: <FolderOpen className="w-5 h-5" />, accept: "image/*", primary: false },
      ]}
    />
  );
};

const ChallengeVideoRow: React.FC<{ prompt: Extract<Prompt, { kind: "video" }>; userId: string }> = ({ prompt, userId }) => {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  useUploadGuard(busy);

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setProgress(0);
    setError(null);
    try {
      const data = await uploadVideo(
        file,
        { competition_id: prompt.competitionId, lift_type: prompt.liftType, weight: "0", user_id: userId },
        setProgress,
        { compression: prompt.liftType === "Plank" ? "fast-only" : "auto" },
      );
      if (!data.attempt_id) throw new Error("Upload finished without an attempt id");
      localStorage.setItem("last_attempt_id", data.attempt_id);
      try {
        await triggerLiftingAnalysis(data.attempt_id);
      } catch (analyzeErr) {
        console.error("Auto-analyze failed:", analyzeErr);
      }
      navigate(`/lift/status/${data.attempt_id}?challenge=${prompt.competitionId}`);
    } catch (err) {
      reportUploadError("PromptList", file, err, { liftType: prompt.liftType, competitionId: prompt.competitionId });
      setError(uploadErrorMessage(err));
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  };

  const status = busy ? (progress < 100 ? `Uploading ${progress}%` : "Finishing up…") : null;
  const idBase = `home-challenge-${prompt.competitionId}`;
  return (
    <ActionRow
      icon={iconFor(prompt)}
      title={prompt.title}
      pill={prompt.pill}
      status={status}
      error={error}
      busy={busy}
      onFile={onFile}
      inputs={[
        { id: `${idBase}-record`, label: `Record your ${prompt.liftType.toLowerCase()}s now`, icon: <Video className="w-5 h-5" />, accept: "video/*", capture: "environment", primary: true },
        { id: `${idBase}-upload`, label: `Upload a ${prompt.liftType.toLowerCase()} video`, icon: <FolderOpen className="w-5 h-5" />, accept: "video/*", primary: false },
      ]}
    />
  );
};

const PromptList: React.FC<Props> = ({ prompts, userId }) => (
  <section aria-label="To-do" className="flex flex-col gap-2.5 text-left">
    <h2 className="text-xs uppercase tracking-widest text-muted-foreground text-center mb-1">
      Tonight's to-do
    </h2>
    {prompts.map((prompt) => {
      if (prompt.kind === "camera" && userId) return <BowlSnapRow key={prompt.id} prompt={prompt} userId={userId} />;
      if (prompt.kind === "video" && userId) return <ChallengeVideoRow key={prompt.id} prompt={prompt} userId={userId} />;
      const to = prompt.kind === "link" ? prompt.to : prompt.fallbackTo;
      const pill = prompt.kind === "camera" ? undefined : prompt.pill;
      return (
        <Link key={prompt.id} to={to} className={rowClass}>
          <span className={chipClass}>{iconFor(prompt)}</span>
          <span className="flex-1 min-w-0 font-medium truncate">{prompt.title}</span>
          {pill && (
            <span className="shrink-0 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-accent/10 text-accent">
              {pill}
            </span>
          )}
          <span className={primaryAction}>
            {prompt.kind === "camera" ? <Camera className="w-5 h-5" /> : prompt.kind === "video" ? <Video className="w-5 h-5" /> : <ArrowRight className="w-5 h-5" />}
          </span>
        </Link>
      );
    })}
  </section>
);

export default PromptList;
