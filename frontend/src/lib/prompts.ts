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

const BODYWEIGHT_FORM_IDS: Record<string, string> = {
  Plank: "Plank",
  Pushup: "Pushup",
  Situp: "Situp",
};

/** Lift type the home row can upload with no questions: one bodyweight category, nothing to weigh. */
export const quickLiftType = (categories: string[] | undefined): string | null => {
  const ids = (categories ?? []).map((c) => BODYWEIGHT_FORM_IDS[c]).filter(Boolean);
  return ids.length === 1 && (categories ?? []).length === 1 ? ids[0] : null;
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
