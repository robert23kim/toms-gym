import { Competition } from "./types";

export type Prompt =
  | { id: "bowl-snap"; kind: "camera"; title: string; fallbackTo: string }
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

type OpenChallenge = Pick<Competition, "id" | "title" | "categories">;

const LIFT_CATEGORIES = new Set(["Squat", "Bench Press", "Deadlift", "Bicep Curl", "Plank", "Pushup", "Situp"]);
const BODYWEIGHT = new Set(["Plank", "Pushup", "Situp"]);

/** Lift type the home row can upload with no questions: the challenge's only lift is bodyweight. */
export const quickLiftType = (categories: string[] | undefined): string | null => {
  const lifts = (categories ?? []).filter((c) => LIFT_CATEGORIES.has(c));
  return lifts.length === 1 && BODYWEIGHT.has(lifts[0]) ? lifts[0] : null;
};

export const buildPrompts = (openChallenges: OpenChallenge[]): Prompt[] => [
  { id: "bowl-snap", kind: "camera", title: "Snap tonight's scores", fallbackTo: "/bowling/snap" },
  ...openChallenges.map<Prompt>((c) => {
    const liftType = quickLiftType(c.categories);
    const pill = c.categories?.[0];
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
  { id: "golf-snap", kind: "link", title: "Snap a scorecard", to: "/golf/snap" },
  { id: "lift-upload", kind: "link", title: "Log a lift", to: "/lift/upload" },
];
