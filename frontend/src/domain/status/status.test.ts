import { describe, expect, it } from "vitest";
import { groupByStatus, STATUS_LABELS, STATUS_ORDER, isValidStatus } from "./status";
import type { BoardItem } from "./status";

describe("STATUS_ORDER", () => {
  it("未着手→作業中→レビュー→完了の順で4件並ぶ", () => {
    expect(STATUS_ORDER).toEqual(["not_started", "in_progress", "in_review", "done"]);
  });
});

describe("STATUS_LABELS", () => {
  it("全ステータスに日本語ラベルを持つ", () => {
    for (const status of STATUS_ORDER) {
      expect(STATUS_LABELS[status]).toBeTruthy();
    }
  });
});

describe("isValidStatus", () => {
  it("既知のstatusはtrueを返す", () => {
    expect(isValidStatus("in_review")).toBe(true);
  });

  it("未知のstatusはfalseを返す", () => {
    expect(isValidStatus("unknown")).toBe(false);
  });
});

describe("groupByStatus", () => {
  const items: BoardItem[] = [
    { id: 1, name: "SHOT010", status: "not_started", kind: "shot" },
    { id: 2, name: "SHOT020", status: "in_progress", kind: "shot" },
    { id: 3, name: "Character_Hero", status: "in_progress", kind: "asset" },
  ];

  it("ステータスごとに配列を持つマップへグループ化する", () => {
    const grouped = groupByStatus(items);

    expect(grouped.not_started).toHaveLength(1);
    expect(grouped.in_progress).toHaveLength(2);
    expect(grouped.in_review).toHaveLength(0);
    expect(grouped.done).toHaveLength(0);
  });

  it("空配列を渡しても全ステータスのキーが存在する", () => {
    const grouped = groupByStatus([]);

    expect(Object.keys(grouped)).toEqual(STATUS_ORDER);
  });
});
