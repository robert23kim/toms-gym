import { BowlingSheetType } from "./api";
import { ChallengeLeaderboard, Competition } from "./types";
import { formatScoreValue } from "../components/challenge/metric";

export type Prompt =
  | { id: "bowl-snap" | "game-snap"; kind: "camera"; title: string; sheetType: BowlingSheetType; fallbackTo: string }
  | {
      id: string;
      kind: "video";
      title: string;
      pill?: string;
      competitionId: string;
      liftType: string;
      fallbackTo: string;
    }
  | { id: string; kind: "link"; title: string; to: string; pill?: string };

type OpenChallenge = Pick<Competition, "id" | "title" | "categories"> & Partial<Pick<Competition, "mode">>;

const LIFT_CATEGORIES = new Set(["Squat", "Bench Press", "Deadlift", "Bicep Curl", "Plank", "Pushup", "Situp"]);
const BODYWEIGHT = new Set(["Plank", "Pushup", "Situp"]);

/** Lift type the home row can upload with no questions: the challenge's only lift is bodyweight. */
export const quickLiftType = (categories: string[] | undefined): string | null => {
  const lifts = (categories ?? []).filter((c) => LIFT_CATEGORIES.has(c));
  return lifts.length === 1 && BODYWEIGHT.has(lifts[0]) ? lifts[0] : null;
};

/** Home pill for a 100 Club row: "42 / 150 · 3 days left", "Starts Mon"; null when the viewer has no row. */
export const consistencyPill = (
  board: Pick<ChallengeLeaderboard, "rows" | "consistency"> | null | undefined,
  userId: string | null | undefined,
): string | null => {
  if (!board?.consistency || !userId) return null;
  const row = board.rows.find((r) => String(r.user_id) === String(userId));
  if (!row?.this_week) return null;
  const { status, days_left } = board.consistency;
  if (status === "upcoming") return "Starts Mon";
  if (status === "ended") return null;
  const lifts = formatScoreValue(row.this_week.lifts, "consistency");
  return `${lifts} / ${row.this_week.quota} · ${days_left} ${days_left === 1 ? "day" : "days"} left`;
};

export const isConsistencyChallenge = (c: Pick<Competition, "mode">): boolean => c.mode === "consistency";

export type PromptOptions = {
  /** Bowling and golf rows; only the owner's account sees them. */
  sports?: boolean;
};

const BOWLING_PROMPTS: Prompt[] = [
  { id: "bowl-snap", kind: "camera", title: "Snap tonight's bowling recap", sheetType: "night", fallbackTo: "/bowling/snap" },
  { id: "game-snap", kind: "camera", title: "Snap a bowling game", sheetType: "game", fallbackTo: "/bowling/snap" },
];
const GOLF_PROMPTS: Prompt[] = [{ id: "golf-snap", kind: "link", title: "Snap a golf scorecard", to: "/golf/snap" }];

/** `pills` overrides a challenge row's pill by competition id (the 100 Club progress pill). */
export const buildPrompts = (
  openChallenges: OpenChallenge[],
  pills: Record<string, string> = {},
  { sports = true }: PromptOptions = {},
): Prompt[] => [
  ...(sports ? BOWLING_PROMPTS : []),
  ...openChallenges.map<Prompt>((c) => {
    const liftType = isConsistencyChallenge(c) ? null : quickLiftType(c.categories);
    const pill = isConsistencyChallenge(c) ? pills[c.id] : pills[c.id] ?? c.categories?.[0];
    if (liftType) {
      return {
        id: `challenge:${c.id}`,
        kind: "video",
        title: c.title,
        pill,
        competitionId: c.id,
        liftType,
        fallbackTo: `/challenges/${c.id}`,
      };
    }
    return { id: `challenge:${c.id}`, kind: "link", title: c.title, to: `/challenges/${c.id}`, pill };
  }),
  ...(sports ? GOLF_PROMPTS : []),
  { id: "lift-upload", kind: "link", title: "Log a lift", to: "/lift/upload" },
];
