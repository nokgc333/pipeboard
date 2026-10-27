// @vitest-environment happy-dom
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "../KanbanBoard";
import * as apiClient from "@/lib/api-client";
import type { ItemDto } from "@/lib/api-client";

vi.mock("@/lib/api-client", async () => {
  const actual = await vi.importActual<typeof apiClient>("@/lib/api-client");
  return {
    ...actual,
    listShots: vi.fn(),
    listAssets: vi.fn(),
    updateStatus: vi.fn(),
  };
});

const mockedListShots = vi.mocked(apiClient.listShots);
const mockedListAssets = vi.mocked(apiClient.listAssets);
const mockedUpdateStatus = vi.mocked(apiClient.updateStatus);

beforeEach(() => {
  vi.resetAllMocks();
});

const TIMESTAMP = "2026-10-27T00:00:00";

function item(id: number, name: string, status: ItemDto["status"]): ItemDto {
  return { id, name, status, created_at: TIMESTAMP, updated_at: TIMESTAMP };
}

describe("KanbanBoard", () => {
  it("読み込み中はスケルトンを表示する", () => {
    mockedListShots.mockReturnValue(new Promise(() => {}));
    mockedListAssets.mockReturnValue(new Promise(() => {}));

    render(<KanbanBoard baseUrl="http://localhost:8000" />);

    expect(screen.getByText(/読み込み中/)).toBeInTheDocument();
  });

  it("0件の場合は空状態メッセージを表示する", async () => {
    mockedListShots.mockResolvedValue([]);
    mockedListAssets.mockResolvedValue([]);

    render(<KanbanBoard baseUrl="http://localhost:8000" />);

    expect(await screen.findByText(/まだショット\/アセットがありません/)).toBeInTheDocument();
  });

  it("取得したショット/アセットを4列に振り分けて表示する", async () => {
    mockedListShots.mockResolvedValue([item(1, "SHOT010", "in_progress")]);
    mockedListAssets.mockResolvedValue([item(2, "Character_Hero", "done")]);

    render(<KanbanBoard baseUrl="http://localhost:8000" />);

    expect(await screen.findByText("SHOT010")).toBeInTheDocument();
    expect(screen.getByText("Character_Hero")).toBeInTheDocument();
  });

  it("API接続失敗時はエラーバナーと再試行ボタンを表示する", async () => {
    mockedListShots.mockRejectedValue(new Error("network error"));
    mockedListAssets.mockResolvedValue([]);

    render(<KanbanBoard baseUrl="http://localhost:8000" />);

    expect(await screen.findByText(/読み込みに失敗しました/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "再試行" })).toBeInTheDocument();
  });

  it("ステータス変更失敗時は楽観的更新をロールバックする", async () => {
    mockedListShots.mockResolvedValue([item(1, "SHOT010", "not_started")]);
    mockedListAssets.mockResolvedValue([]);
    mockedUpdateStatus.mockRejectedValue(new apiClient.ApiError(400, "Invalid status"));
    const user = userEvent.setup();

    render(<KanbanBoard baseUrl="http://localhost:8000" />);
    await screen.findByText("SHOT010");

    await user.selectOptions(screen.getByLabelText(/ステータス変更/), "in_progress");

    // ロールバックにより最終的に元のステータス(not_started)へ戻ることを確認する
    await waitFor(() => {
      expect(screen.getByLabelText(/SHOT010.*未着手/)).toBeInTheDocument();
    });
  });

  it("ステータス変更に成功すると、状況をスクリーンリーダー向けに通知する", async () => {
    mockedListShots.mockResolvedValue([item(1, "SHOT010", "not_started")]);
    mockedListAssets.mockResolvedValue([]);
    mockedUpdateStatus.mockResolvedValue(item(1, "SHOT010", "in_progress"));
    const user = userEvent.setup();

    render(<KanbanBoard baseUrl="http://localhost:8000" />);
    await screen.findByText("SHOT010");
    await user.selectOptions(screen.getByLabelText(/ステータス変更/), "in_progress");

    const status = await screen.findByRole("status");
    expect(status).toHaveTextContent("SHOT010を「作業中」に変更しました");
    expect(status).toHaveAttribute("aria-live", "polite");
  });

  it("失敗したときは、元に戻したことと理由を通知する", async () => {
    mockedListShots.mockResolvedValue([item(1, "SHOT010", "not_started")]);
    mockedListAssets.mockResolvedValue([]);
    mockedUpdateStatus.mockRejectedValue(new apiClient.ApiError(409, "Missing checks: unibridge"));
    const user = userEvent.setup();

    render(<KanbanBoard baseUrl="http://localhost:8000" />);
    await screen.findByText("SHOT010");
    await user.selectOptions(screen.getByLabelText(/ステータス変更/), "done");

    const status = await screen.findByRole("status");
    expect(status).toHaveTextContent("SHOT010の更新に失敗したため元に戻しました");
    expect(status).toHaveTextContent("Missing checks: unibridge");
  });

  it("通知の領域は、変更の前から存在し、空である", async () => {
    mockedListShots.mockResolvedValue([item(1, "SHOT010", "not_started")]);
    mockedListAssets.mockResolvedValue([]);

    render(<KanbanBoard baseUrl="http://localhost:8000" />);
    await screen.findByText("SHOT010");

    expect(screen.getByRole("status")).toBeEmptyDOMElement();
  });
});
