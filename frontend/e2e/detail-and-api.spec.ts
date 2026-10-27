import { expect, test } from "@playwright/test";
import type { APIRequestContext } from "@playwright/test";

const API = "http://localhost:8000";

const PNG_BYTES = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);

async function shotIdByName(request: APIRequestContext, name: string): Promise<number> {
  const response = await request.get(`${API}/shots`);
  const shots: { id: number; name: string }[] = await response.json();
  const found = shots.find((s) => s.name === name);
  if (!found) throw new Error(`${name} is not seeded`);
  return found.id;
}

test("詳細ページでコメントを投稿すると、一覧に表示される", async ({ page, request }) => {
  const id = await shotIdByName(request, "SHOT020");
  const body = `e2e-comment-${Date.now()}`;
  await page.goto(`/shots/${id}`);

  await page.getByPlaceholder("コメントを入力").fill(body);
  await page.getByPlaceholder("タグ（任意）").fill("e2e");
  await page.getByRole("button", { name: "投稿" }).click();

  await expect(page.getByText(body)).toBeVisible();
});

test("空のコメントは投稿できず、メッセージが出る", async ({ page, request }) => {
  const id = await shotIdByName(request, "SHOT020");
  await page.goto(`/shots/${id}`);

  await page.getByRole("button", { name: "投稿" }).click();

  await expect(page.locator("p.text-red-600")).toBeVisible();
});

test("画像をアップロードすると、バージョンが増える", async ({ page, request }) => {
  const id = await shotIdByName(request, "SHOT030");
  const before = (await (await request.get(`${API}/shots/${id}/versions`)).json()).length;
  await page.goto(`/shots/${id}`);

  await page
    .getByLabel("バージョン画像を選択")
    .setInputFiles({ name: "frame.png", mimeType: "image/png", buffer: PNG_BYTES });

  await expect(page.getByAltText(`v${before + 1}`)).toBeVisible();
});

test("対応していない拡張子のファイルは、画面で拒否される", async ({ page, request }) => {
  const id = await shotIdByName(request, "SHOT030");
  await page.goto(`/shots/${id}`);

  await page
    .getByLabel("バージョン画像を選択")
    .setInputFiles({ name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("hello") });

  await expect(page.getByText("対応していないファイル形式です")).toBeVisible();
});

test("API はステータスの遷移を検証し、未定義の値を拒否する", async ({ request }) => {
  const id = await shotIdByName(request, "SHOT040");

  const rejected = await request.patch(`${API}/shots/${id}/status`, {
    data: { status: "archived" },
  });
  const accepted = await request.patch(`${API}/shots/${id}/status`, {
    data: { status: "done" },
  });

  expect(rejected.status()).toBe(400);
  expect(accepted.status()).toBe(200);
});

test("API は、拡張子が画像でも中身が画像でないファイルを拒否する", async ({ request }) => {
  const id = await shotIdByName(request, "SHOT030");

  const response = await request.post(`${API}/versions?item_type=shot&item_id=${id}`, {
    multipart: {
      file: { name: "fake.png", mimeType: "image/png", buffer: Buffer.from("not an image at all") },
    },
  });

  expect(response.status()).toBe(400);
});
