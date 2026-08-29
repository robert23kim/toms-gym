import { highlightCopy, roundHighlight } from "../golfBest";

const r = (id: string, holes: number, total_score: number | null, course: string | null) => ({
  id,
  holes,
  total_score,
  course: course ? { id: `c-${course}`, name: course } : null,
});

const rounds = [
  r("a", 18, 105, "Waverly Oaks"),
  r("b", 18, 98, "Sagamore"),
  r("c", 18, 99, "Birch Hill"),
  r("d", 9, 51, "Birch Hill"),
  r("e", 18, 94, "Birch Hill"),
];

describe("roundHighlight", () => {
  it("prefers best-ever over best-at-course, comparing only rounds of the same length", () => {
    expect(roundHighlight(rounds, "e")).toEqual({ kind: "best-ever", holes: 18 });
    expect(roundHighlight(rounds, "d")).toEqual({ kind: "first-at-course", course: "Birch Hill" });
  });

  it("finds a best at the course and a first visit", () => {
    const more = [...rounds, r("f", 18, 96, "Birch Hill")];
    expect(roundHighlight(more, "f")).toBeNull();
    expect(roundHighlight([...rounds.filter((x) => x.id !== "e"), r("g", 18, 98, "Birch Hill")], "g")).toEqual({
      kind: "best-at-course",
      course: "Birch Hill",
    });
    expect(roundHighlight(rounds, "b")).toEqual({ kind: "first-at-course", course: "Sagamore" });
  });

  it("returns null for ties, unknown rounds, unscored rounds and unnamed courses", () => {
    expect(roundHighlight([...rounds, r("h", 18, 94, "Elsewhere")], "h")).toEqual({ kind: "first-at-course", course: "Elsewhere" });
    expect(roundHighlight([...rounds, r("i", 18, 99, "Birch Hill")], "i")).toBeNull();
    expect(roundHighlight(rounds, "zzz")).toBeNull();
    expect(roundHighlight([r("j", 18, null, "X")], "j")).toBeNull();
    expect(roundHighlight([r("k", 18, 80, null)], "k")).toBeNull();
  });

  it("writes the copy", () => {
    expect(highlightCopy({ kind: "best-ever", holes: 18 })).toBe("Your best 18 yet");
    expect(highlightCopy({ kind: "best-at-course", course: "Birch Hill" })).toBe("Your best at Birch Hill");
    expect(highlightCopy({ kind: "first-at-course", course: "Birch Hill" })).toBe("First round at Birch Hill");
  });
});
