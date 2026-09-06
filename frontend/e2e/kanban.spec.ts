import { expect, test } from "@playwright/test";

/**
 * TC-001, TC-004, TC-005のE2E視点での確認（仕様書§12.4）。
 * 実行にはバックエンドが http://localhost:8000 で起動しシードデータが投入済みであること。
 * ローカルでの実行手順はREADME参照。CI組み込みはv1では見送っている
 * （バックエンド起動・DBシードの待ち合わせをCI上で安定させるコストが高いため）。
 */
test("カンバンボードにショット/アセットが表示され、ステータス変更ができる", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("SHOT010")).toBeVisible();

  await page.getByLabel(/SHOT010.*ステータス変更|ステータス変更/).first().selectOption("in_progress");

  await expect(page.getByLabel(/SHOT010.*作業中/)).toBeVisible();
});
