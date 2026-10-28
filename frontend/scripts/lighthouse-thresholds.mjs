export const THRESHOLDS = {
  performance: 0.9,
  accessibility: 1,
  "best-practices": 0.95,
  seo: 1,
};

export function findFailures(report, thresholds = THRESHOLDS) {
  return Object.entries(thresholds)
    .map(([category, minimum]) => ({ category, minimum, score: report.categories[category]?.score }))
    .filter(({ score, minimum }) => score === undefined || score === null || score < minimum)
    .map(({ category, minimum, score }) => `${category}: ${score ?? "missing"} < ${minimum}`);
}

/** The categories whose score moves from run to run on a shared CI runner. */
const NOISY_CATEGORIES = ["performance"];

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

/**
 * Merge several runs of one page into one report to judge.
 * Performance is a median, so one slow run on a busy runner cannot fail the build (and one lucky
 * run cannot hide a real slowdown). Every other category is deterministic, so the lowest run
 * counts. A run without a score makes the category missing.
 */
export function aggregateReports(reports) {
  if (reports.length === 0) throw new Error("no reports to aggregate");
  const names = Object.keys(THRESHOLDS);
  const categories = {};
  for (const name of names) {
    const scores = reports.map((report) => report.categories?.[name]?.score);
    const missing = scores.some((score) => score === undefined || score === null);
    categories[name] = {
      score: missing
        ? null
        : NOISY_CATEGORIES.includes(name)
          ? median(scores)
          : Math.min(...scores),
    };
  }
  return { finalDisplayedUrl: reports[0].finalDisplayedUrl, categories };
}

/** Group reports by the page they measured, keeping the order the pages first appear in. */
export function groupByUrl(reports) {
  const groups = new Map();
  for (const report of reports) {
    const url = report.finalDisplayedUrl;
    groups.set(url, [...(groups.get(url) ?? []), report]);
  }
  return groups;
}
