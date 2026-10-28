// @vitest-environment happy-dom
import { describe, expect, it, vi, beforeEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ItemDetail } from "../ItemDetail";
import * as apiClient from "@/lib/api-client";
import type { ItemDto } from "@/lib/api-client";

vi.mock("@/lib/api-client", async () => {
  const actual = await vi.importActual<typeof apiClient>("@/lib/api-client");
  return {
    ...actual,
    listShots: vi.fn(),
    listAssets: vi.fn(),
    listVersions: vi.fn(),
    listComments: vi.fn(),
  };
});

const mockedListShots = vi.mocked(apiClient.listShots);
const mockedListAssets = vi.mocked(apiClient.listAssets);
const mockedListVersions = vi.mocked(apiClient.listVersions);
const mockedListComments = vi.mocked(apiClient.listComments);

const TIMESTAMP = "2026-10-27T00:00:00";
const BASE_URL = "http://localhost:8000";

function item(id: number, name: string): ItemDto {
  return {
    id,
    name,
    status: "in_review",
    created_at: TIMESTAMP,
    updated_at: TIMESTAMP,
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  mockedListVersions.mockResolvedValue([]);
  mockedListComments.mockResolvedValue([]);
});

describe("ItemDetail", () => {
  it("読み込み中は、案内を表示する", () => {
    mockedListShots.mockReturnValue(new Promise(() => {}));

    render(<ItemDetail baseUrl={BASE_URL} itemType="shot" itemId={1} />);

    expect(screen.getByText(/読み込み中/)).toBeInTheDocument();
  });

  it("読み込めたら、ショットの名前を見出しに表示する", async () => {
    mockedListShots.mockResolvedValue([item(1, "SHOT010"), item(2, "SHOT020")]);

    render(<ItemDetail baseUrl={BASE_URL} itemType="shot" itemId={2} />);

    expect(
      await screen.findByRole("heading", { name: "SHOT020" }),
    ).toBeInTheDocument();
    expect(mockedListVersions).toHaveBeenCalledWith(BASE_URL, "shot", 2);
  });

  it("アセットのときは、アセットの一覧から探す", async () => {
    mockedListAssets.mockResolvedValue([item(7, "ASSET_hero")]);

    render(<ItemDetail baseUrl={BASE_URL} itemType="asset" itemId={7} />);

    expect(
      await screen.findByRole("heading", { name: "ASSET_hero" }),
    ).toBeInTheDocument();
    expect(mockedListShots).not.toHaveBeenCalled();
  });

  it("一覧に無い ID のときは、失敗の表示にする", async () => {
    mockedListShots.mockResolvedValue([item(1, "SHOT010")]);

    render(<ItemDetail baseUrl={BASE_URL} itemType="shot" itemId={99} />);

    expect(
      await screen.findByText("読み込みに失敗しました。"),
    ).toBeInTheDocument();
  });

  it("通信に失敗したら、再試行ボタンを出し、押すと読み込み中に戻って、成功すれば表示する", async () => {
    mockedListShots.mockRejectedValueOnce(new Error("offline"));
    const user = userEvent.setup();
    render(<ItemDetail baseUrl={BASE_URL} itemType="shot" itemId={1} />);
    await screen.findByText("読み込みに失敗しました。");

    let finish: (items: ItemDto[]) => void = () => {};
    mockedListShots.mockReturnValueOnce(
      new Promise((resolve) => (finish = resolve)),
    );
    await user.click(screen.getByRole("button", { name: "再試行" }));

    expect(screen.getByText(/読み込み中/)).toBeInTheDocument();
    finish([item(1, "SHOT010")]);
    expect(
      await screen.findByRole("heading", { name: "SHOT010" }),
    ).toBeInTheDocument();
  });

  it("ID が変わったあとに、前の ID の応答が遅れて届いても、表示を上書きしない", async () => {
    let finishFirst: (items: ItemDto[]) => void = () => {};
    mockedListShots.mockReturnValueOnce(
      new Promise((resolve) => (finishFirst = resolve)),
    );
    const { rerender } = render(
      <ItemDetail baseUrl={BASE_URL} itemType="shot" itemId={1} />,
    );

    mockedListShots.mockResolvedValueOnce([
      item(1, "SHOT010"),
      item(2, "SHOT020"),
    ]);
    rerender(<ItemDetail baseUrl={BASE_URL} itemType="shot" itemId={2} />);
    expect(
      await screen.findByRole("heading", { name: "SHOT020" }),
    ).toBeInTheDocument();

    await act(async () => finishFirst([item(1, "SHOT010")]));

    expect(
      screen.getByRole("heading", { name: "SHOT020" }),
    ).toBeInTheDocument();
  });
});
