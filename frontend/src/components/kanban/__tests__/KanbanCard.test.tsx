// @vitest-environment happy-dom
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanCard } from "../KanbanCard";

describe("KanbanCard", () => {
  it("ショット名と現在ステータスを表示する", () => {
    render(<KanbanCard id={1} name="SHOT010" status="in_review" kind="shot" onChangeStatus={() => {}} />);

    expect(screen.getByText("SHOT010")).toBeInTheDocument();
    expect(screen.getByLabelText(/SHOT010.*レビュー/)).toBeInTheDocument();
  });

  it("種別バッジ(Shot/Asset)を表示する", () => {
    render(<KanbanCard id={1} name="Character_Hero" status="not_started" kind="asset" onChangeStatus={() => {}} />);

    expect(screen.getByText("Asset")).toBeInTheDocument();
  });

  it("ステータス変更メニューから選択すると onChangeStatus が呼ばれる（キーボード操作の代替手段）", async () => {
    const user = userEvent.setup();
    const onChangeStatus = vi.fn();
    render(
      <KanbanCard id={1} name="SHOT010" status="not_started" kind="shot" onChangeStatus={onChangeStatus} />,
    );

    await user.selectOptions(screen.getByLabelText(/ステータス変更/), "in_progress");

    expect(onChangeStatus).toHaveBeenCalledWith(1, "shot", "in_progress");
  });
});
