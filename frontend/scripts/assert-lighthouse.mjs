import { readFileSync } from "node:fs";
import { aggregateReports, findFailures, groupByUrl } from "./lighthouse-thresholds.mjs";

const files = process.argv.slice(2);
const reports = files.map((file) => JSON.parse(readFileSync(file, "utf-8")));
const percent = (score) => (typeof score === "number" ? Math.round(score * 100) : "missing");

let failed = false;
for (const [url, runs] of groupByUrl(reports)) {
  const merged = aggregateReports(runs);
  const scores = Object.entries(merged.categories)
    .map(([name, value]) => `${name}=${percent(value.score)}`)
    .join(" ");
  const performance = runs.map((run) => percent(run.categories.performance?.score)).join(",");
  console.log(`${url}: ${scores} (performance of ${runs.length} runs: ${performance})`);
  for (const message of findFailures(merged)) {
    console.error(`  FAIL ${message}`);
    failed = true;
  }
}
process.exit(failed ? 1 : 0);
