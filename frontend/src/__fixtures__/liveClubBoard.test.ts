import { liveClubBoard } from "./liveClubBoard";

it("carries placeholder athletes only, with the live board's shape and numbers", () => {
  const rows = liveClubBoard.rows;
  expect(rows.map((r) => r.name)).toEqual(["athlete.one", "athlete.two"]);
  for (const r of rows) expect(String(r.user_id)).toMatch(/^00000000-0000-4000-8000-/);
  const leaders = Object.values(liveClubBoard.consistency!.type_leaders ?? {}).flat();
  for (const l of leaders) {
    expect(l.name).toMatch(/^athlete\./);
    expect(String(l.user_id)).toMatch(/^00000000-0000-4000-8000-/);
  }
  expect(rows.map((r) => r.score)).toEqual([375, 350]);
});
