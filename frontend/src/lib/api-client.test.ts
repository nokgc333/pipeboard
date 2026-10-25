import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  listShots,
  listAssets,
  listVersions,
  listComments,
  updateStatus,
  uploadVersion,
  createComment,
} from "./api-client";

describe("api-client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("listShots: GET /shots を呼び出しJSONを返す", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ id: 1, name: "SHOT010", status: "not_started" }],
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await listShots("http://localhost:8000");

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/shots");
    expect(result).toEqual([{ id: 1, name: "SHOT010", status: "not_started" }]);
  });

  it("updateStatus: PATCH /shots/{id}/status を呼び出す", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 1, status: "in_review" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await updateStatus("http://localhost:8000", "shot", 1, "in_review");

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/shots/1/status", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "in_review" }),
    });
  });

  it("APIがエラーレスポンスを返した場合ApiErrorを送出する（楽観的更新のロールバック判定に使う）", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ title: "Shot 999 not found" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(updateStatus("http://localhost:8000", "shot", 999, "done")).rejects.toBeInstanceOf(
      ApiError,
    );
  });

  it("listAssets: GET /assets を呼び出す", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);

    await listAssets("http://localhost:8000");

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/assets");
  });

  it("listVersions: item_typeに応じてshots/assetsのバージョン一覧を取得する", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);

    await listVersions("http://localhost:8000", "asset", 5);

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/assets/5/versions");
  });

  it("listComments: item_typeに応じてshots/assetsのコメント一覧を取得する", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);

    await listComments("http://localhost:8000", "shot", 1);

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/shots/1/comments");
  });

  it("エラーレスポンスにtitleが無い場合もフォールバックメッセージでApiErrorを送出する", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("not json");
      },
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(listShots("http://localhost:8000")).rejects.toMatchObject({
      status: 500,
      message: "Request failed: 500",
    });
  });

  it("uploadVersion: multipart/form-dataでPOST /versionsを呼び出す", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 1, version_number: 1 }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const file = new File([new Uint8Array([1])], "a.png", { type: "image/png" });

    await uploadVersion("http://localhost:8000", "shot", 1, file);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/versions?item_type=shot&item_id=1");
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
  });

  it("createComment: POST /comments を呼び出す", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 1, body: "note" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await createComment("http://localhost:8000", { item_type: "shot", item_id: 1, body: "note" });

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/comments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item_type: "shot", item_id: 1, body: "note" }),
    });
  });
});

describe("api-client authorization", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("sends a bearer token when NEXT_PUBLIC_API_TOKEN is set", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_TOKEN", "secret-token-1");
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);

    await listShots("http://localhost:8000");

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/shots", {
      headers: { Authorization: "Bearer secret-token-1" },
    });
  });

  it("keeps the content type when it adds the token to a JSON request", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_TOKEN", "secret-token-1");
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await createComment("http://localhost:8000", { item_type: "shot", item_id: 1, body: "hi" });

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.headers).toEqual({
      "Content-Type": "application/json",
      Authorization: "Bearer secret-token-1",
    });
  });

  it("surfaces 401 and 403 as an ApiError with the problem title", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({ title: "Insufficient permissions" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(listShots("http://localhost:8000")).rejects.toMatchObject({
      status: 403,
      message: "Insufficient permissions",
    });
  });
});
