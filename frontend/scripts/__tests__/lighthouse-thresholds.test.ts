import { describe, expect, it } from "vitest";
// @ts-expect-error -- plain ESM script without type declarations
import { THRESHOLDS, aggregateReports, findFailures, groupByUrl } from "../lighthouse-thresholds.mjs";

const report = (scores: Record<string, number | null>) => ({
  categories: Object.fromEntries(Object.entries(scores).map(([k, v]) => [k, { score: v }])),
});

const PASSING = { performance: 0.9, accessibility: 1, "best-practices": 0.95, seo: 1 };

describe("findFailures", () => {
  it("returns nothing when every category meets its threshold exactly", () => {
    expect(findFailures(report(PASSING))).toEqual([]);
  });

  it("names the category, the score and the minimum that failed", () => {
    expect(findFailures(report({ ...PASSING, accessibility: 0.98 }))).toEqual([
      "accessibility: 0.98 < 1",
    ]);
  });

  it("reports every failing category", () => {
    expect(findFailures(report({ ...PASSING, performance: 0.5, seo: 0.9 }))).toHaveLength(2);
  });

  it("treats a missing or null score as a failure", () => {
    const missing = findFailures({ categories: {} });
    const nulled = findFailures(report({ ...PASSING, seo: null }));

    expect(missing).toHaveLength(4);
    expect(nulled).toEqual(["seo: missing < 1"]);
  });

  it("requires accessibility and seo to be perfect", () => {
    expect(THRESHOLDS.accessibility).toBe(1);
    expect(THRESHOLDS.seo).toBe(1);
  });
});

const run = (scores: Record<string, number | null>, url = "http://localhost:3000/") => ({
  finalDisplayedUrl: url,
  ...report(scores),
});

describe("aggregateReports", () => {
  it("takes the median of the noisy performance score", () => {
    const merged = aggregateReports([
      run({ ...PASSING, performance: 0.85 }),
      run({ ...PASSING, performance: 1 }),
      run({ ...PASSING, performance: 0.9 }),
    ]);

    expect(merged.categories.performance.score).toBe(0.9);
  });

  it("lets one slow run be outvoted by two good ones", () => {
    const merged = aggregateReports([
      run({ ...PASSING, performance: 0.7 }),
      run({ ...PASSING, performance: 0.95 }),
      run({ ...PASSING, performance: 0.97 }),
    ]);

    expect(findFailures(merged)).toEqual([]);
  });

  it("still fails when most runs are slow", () => {
    const merged = aggregateReports([
      run({ ...PASSING, performance: 0.85 }),
      run({ ...PASSING, performance: 0.87 }),
      run({ ...PASSING, performance: 0.99 }),
    ]);

    expect(findFailures(merged)).toEqual(["performance: 0.87 < 0.9"]);
  });

  it("averages the two middle scores when the number of runs is even", () => {
    const merged = aggregateReports([
      run({ ...PASSING, performance: 0.8 }),
      run({ ...PASSING, performance: 0.9 }),
    ]);

    expect(merged.categories.performance.score).toBeCloseTo(0.85);
  });

  it("keeps the other categories strict: the lowest run counts", () => {
    const merged = aggregateReports([
      run({ ...PASSING, accessibility: 1 }),
      run({ ...PASSING, accessibility: 0.98 }),
      run({ ...PASSING, accessibility: 1 }),
    ]);

    expect(findFailures(merged)).toEqual(["accessibility: 0.98 < 1"]);
  });

  it("treats a run without a score as missing, so it cannot hide a failure", () => {
    const merged = aggregateReports([
      run({ ...PASSING, seo: 1 }),
      run({ ...PASSING, seo: null }),
      run({ ...PASSING, seo: 1 }),
    ]);

    expect(findFailures(merged)).toEqual(["seo: missing < 1"]);
  });

  it("keeps the address of the page", () => {
    expect(aggregateReports([run(PASSING, "http://localhost:3000/shots/1")]).finalDisplayedUrl).toBe(
      "http://localhost:3000/shots/1",
    );
  });

  it("refuses to judge a page that was not measured", () => {
    expect(() => aggregateReports([])).toThrow(/no reports/i);
  });
});

describe("groupByUrl", () => {
  it("collects the runs of each page together", () => {
    const groups = groupByUrl([
      run(PASSING, "http://localhost:3000/"),
      run(PASSING, "http://localhost:3000/shots/1"),
      run(PASSING, "http://localhost:3000/"),
    ]);

    expect([...groups.keys()]).toEqual(["http://localhost:3000/", "http://localhost:3000/shots/1"]);
    expect(groups.get("http://localhost:3000/")).toHaveLength(2);
  });
});
