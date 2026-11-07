import {
  groupUploadsByDay,
  pointsReceipt,
  ringSegments,
  timeLabel,
  typeColor,
  type ClubUpload,
} from "../clubBreakdown";
import { consistencyRules } from "../../../__fixtures__/consistencyLeaderboard";

const LIFTS = ["Situp", "Pushup", "Squat", "Plank"];

describe("ringSegments", () => {
  it("splits the ring by type in lift-type order, skipping zero types", () => {
    const segs = ringSegments(
      { by_type: { Plank: 8, Situp: 40, Pushup: 52, Squat: 0 }, quota: 100, lifts: 100 },
      LIFTS,
    );
    expect(segs.map((s) => s.type)).toEqual(["Situp", "Pushup", "Plank"]);
    const close = (got: number[], want: number[]) => got.forEach((n, i) => expect(n).toBeCloseTo(want[i], 9));
    close(segs.map((s) => s.fraction), [0.4, 0.52, 0.08]);
    close(segs.map((s) => s.start), [0, 0.4, 0.92]);
  });

  it("never overflows the ring when lifts pass the quota", () => {
    const segs = ringSegments(
      { by_type: { Situp: 31.5, Pushup: 65, Plank: 11, Squat: 0 }, quota: 100, lifts: 107.5 },
      LIFTS,
    );
    const total = segs.reduce((n, s) => n + s.fraction, 0);
    expect(total).toBeCloseTo(1, 6);
    expect(segs[0].fraction).toBeCloseTo(31.5 / 107.5, 6);
  });

  it("leaves the ring short of full while the quota is not met", () => {
    const segs = ringSegments({ by_type: { Situp: 42 }, quota: 150, lifts: 42 }, LIFTS);
    expect(segs).toEqual([{ type: "Situp", fraction: 0.28, start: 0 }]);
  });

  it("lists a type the board did not announce after the known ones", () => {
    const segs = ringSegments({ by_type: { Burpee: 10, Situp: 10 }, quota: 100, lifts: 20 }, LIFTS);
    expect(segs.map((s) => s.type)).toEqual(["Situp", "Burpee"]);
  });
});

describe("typeColor", () => {
  it("gives each club lift its own colour and a fallback for anything else", () => {
    const seen = new Set(LIFTS.map(typeColor));
    expect(seen.size).toBe(4);
    expect(typeColor("Burpee")).toBe(typeColor("Anything"));
    expect(typeColor("situp")).toBe(typeColor("Situp"));
  });
});

describe("pointsReceipt", () => {
  const week = (over: object) => ({
    index: 1,
    quota: 100,
    lifts: 100,
    met: true,
    pending: 0,
    by_type: { Situp: 40, Pushup: 52, Plank: 8, Squat: 0 },
    plank_seconds: 82.8,
    leading: ["Situp"],
    ...over,
  });

  it("adds capped lifts and the quota bonus now, and the type bonus only if the lead holds", () => {
    const r = pointsReceipt(week({}), consistencyRules);
    expect(r).toMatchObject({ banked: 100, met: true, toGo: 0, quotaBonus: 50, leads: ["Situp"], typeBonus: 25, total: 150, ifLeadsHold: 175 });
  });

  it("caps banked lifts at the quota", () => {
    const r = pointsReceipt(week({ lifts: 107.5 }), consistencyRules);
    expect(r.banked).toBe(100);
    expect(r.total).toBe(150);
  });

  it("withholds the quota bonus and counts down while the quota is open", () => {
    const r = pointsReceipt(week({ lifts: 42, quota: 150, met: false, leading: [] }), consistencyRules);
    expect(r).toMatchObject({ banked: 42, met: false, toGo: 108, quotaBonus: 0, leads: [], total: 42, ifLeadsHold: 42 });
  });

  it("stacks one type bonus per lead", () => {
    const r = pointsReceipt(week({ leading: ["Situp", "Plank"] }), consistencyRules);
    expect(r.ifLeadsHold).toBe(200);
  });
});

describe("uploads by day", () => {
  const upload = (id: string, at: string, over: Partial<ClubUpload> = {}): ClubUpload => ({
    id,
    liftType: "Situp",
    at,
    lifts: 10,
    seconds: null,
    failed: false,
    href: `/v/${id}`,
    ...over,
  });

  it("groups newest first by the challenge's local day", () => {
    const groups = groupUploadsByDay(
      [
        upload("mon", "2026-11-02T12:43:36+00:00"),
        upload("fri-late", "2026-11-06T18:24:09+00:00"),
        upload("fri-early", "2026-11-06T18:21:06+00:00"),
        upload("sat-ny", "2026-11-08T03:30:00+00:00"),
      ],
      "America/New_York",
    );
    expect(groups.map((g) => g.day)).toEqual(["Sat 7 Nov", "Fri 6 Nov", "Mon 2 Nov"]);
    expect(groups[1].items.map((u) => u.id)).toEqual(["fri-late", "fri-early"]);
  });

  it("formats the upload time in the challenge's zone", () => {
    expect(timeLabel("2026-11-06T18:24:09+00:00", "America/New_York")).toBe("1:24 pm");
    expect(timeLabel("2026-11-06T18:24:09", "America/New_York")).toBe("1:24 pm");
  });
});
