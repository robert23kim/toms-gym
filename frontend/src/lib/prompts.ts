import { Competition } from "./types";

export type Prompt =
  | { id: "bowl-snap"; kind: "camera"; title: string; fallbackTo: string }
  | { id: string; kind: "link"; title: string; to: string; pill?: string };

type OpenChallenge = Pick<Competition, "id" | "title" | "categories">;

export const buildPrompts = (openChallenges: OpenChallenge[]): Prompt[] => [
  { id: "bowl-snap", kind: "camera", title: "Snap tonight's scores", fallbackTo: "/bowling/snap" },
  ...openChallenges.map<Prompt>((c) => ({
    id: `challenge:${c.id}`,
    kind: "link",
    title: c.title,
    to: `/challenges/${c.id}/upload`,
    pill: c.categories?.[0],
  })),
  { id: "golf-snap", kind: "link", title: "Snap a scorecard", to: "/golf/snap" },
  { id: "lift-upload", kind: "link", title: "Log a lift", to: "/lift/upload" },
];
