import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { ArrowRight, Camera, CircleDot, Dumbbell, Flag, Trophy } from "lucide-react";
import { Prompt } from "../../lib/prompts";
import { uploadBowlingSheet } from "../../lib/api";
import { buildSheetForm } from "../../lib/bowlingSheetForm";
import { todayLocal } from "../../lib/dates";

interface Props {
  prompts: Prompt[];
  userId: string | null;
}

const CAMERA_INPUT_ID = "home-bowl-camera";

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
const actionClass =
  "shrink-0 w-11 h-11 rounded-xl grid place-items-center bg-accent text-accent-foreground shadow-sm transition-colors hover:bg-accent/90";

const PromptList: React.FC<Props> = ({ prompts, userId }) => {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onPhoto = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !userId) return;
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
    <section aria-label="To-do" className="flex flex-col gap-2.5 text-left">
      <h2 className="text-xs uppercase tracking-widest text-muted-foreground text-center mb-1">
        Tonight's to-do
      </h2>
      {prompts.map((prompt) => {
        if (prompt.kind === "camera" && userId) {
          return (
            <div key={prompt.id} className={rowClass}>
              <span className={chipClass}>{iconFor(prompt)}</span>
              <span className="flex-1 min-w-0">
                <span className="block font-medium truncate">
                  {busy ? "Reading…" : prompt.title}
                </span>
                {error && <span className="block text-xs text-destructive mt-0.5">{error}</span>}
              </span>
              <label
                htmlFor={CAMERA_INPUT_ID}
                aria-label="Take a photo of the score screen"
                className={`${actionClass} cursor-pointer ${busy ? "opacity-50 pointer-events-none" : ""}`}
              >
                <Camera className="w-5 h-5" />
              </label>
              <input
                id={CAMERA_INPUT_ID}
                data-testid={CAMERA_INPUT_ID}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                disabled={busy}
                onChange={onPhoto}
              />
            </div>
          );
        }
        const to = prompt.kind === "camera" ? prompt.fallbackTo : prompt.to;
        const pill = prompt.kind === "link" ? prompt.pill : undefined;
        return (
          <Link key={prompt.id} to={to} className={rowClass}>
            <span className={chipClass}>{iconFor(prompt)}</span>
            <span className="flex-1 min-w-0 font-medium truncate">{prompt.title}</span>
            {pill && (
              <span className="shrink-0 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-accent/10 text-accent">
                {pill}
              </span>
            )}
            <span className={actionClass}>
              {prompt.kind === "camera" ? <Camera className="w-5 h-5" /> : <ArrowRight className="w-5 h-5" />}
            </span>
          </Link>
        );
      })}
    </section>
  );
};

export default PromptList;
