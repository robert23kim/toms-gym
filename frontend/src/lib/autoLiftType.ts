export const AUTO_LIFT_TYPE = "Auto";
export const AUTO_HELPER = "We'll work out the lift from your video. You can change it after.";
/** Engine confidence below this asks the athlete to confirm the type. */
export const CONFIRM_THRESHOLD = 0.6;

const BODYWEIGHT = new Set(["plank", "pushup", "situp"]);
/** The 100 Club scores squats as air squats, so they count as bodyweight there. */
const CLUB_BODYWEIGHT = new Set([...BODYWEIGHT, "squat"]);

/** Reads the backend switch from GET /competitions/<id>, nested or top level; only a literal true counts. */
export function autoLiftTypeEnabled(payload: unknown): boolean {
  if (!payload || typeof payload !== "object") return false;
  const p = payload as { auto_lift_type_enabled?: unknown; competition?: { auto_lift_type_enabled?: unknown } };
  return p.competition?.auto_lift_type_enabled === true || p.auto_lift_type_enabled === true;
}

/** Automatic is offered only when switched on and every lift type of a multi-type challenge is bodyweight. */
export function offersAutomatic(
  enabled: boolean,
  liftTypes: readonly string[] | null | undefined,
  mode?: string | null,
): boolean {
  const types = (liftTypes ?? []).map((t) => t.trim().toLowerCase()).filter(Boolean);
  if (!enabled || types.length < 2) return false;
  const allowed = mode === "consistency" ? CLUB_BODYWEIGHT : BODYWEIGHT;
  return types.every((t) => allowed.has(t));
}

const PLURAL: Record<string, string> = {
  pushup: "Pushups",
  situp: "Situps",
  squat: "Squats",
  plank: "Plank",
  "bicep curl": "Bicep curls",
  "bench press": "Bench press",
  deadlift: "Deadlifts",
};

const SINGULAR: Record<string, string> = {
  pushup: "a pushup",
  situp: "a situp",
  squat: "a squat",
  plank: "a plank",
};

export const isAutoLiftType = (t: string | null | undefined): boolean =>
  (t ?? "").trim().toLowerCase() === "auto";

/** "Pushups" for the result line. */
export function liftTypeCountedAs(t: string): string {
  const k = t.trim().toLowerCase();
  return PLURAL[k] ?? t;
}

/** "a pushup" for the confirm prompt. */
export function liftTypeQuestion(t: string): string {
  const k = t.trim().toLowerCase();
  return SINGULAR[k] ?? `a ${k}`;
}
