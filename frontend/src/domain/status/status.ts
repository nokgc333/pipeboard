/**
 * ステータス遷移ルール・カンバングルーピングの純粋関数（バックエンドの
 * domain/status_transition.pyと対になる、tonihaya-calendarのdomain分離パターンを踏襲）。
 */

export const STATUS_ORDER = ["not_started", "in_progress", "in_review", "done"] as const;

export type Status = (typeof STATUS_ORDER)[number];

export const STATUS_LABELS: Record<Status, string> = {
  not_started: "未着手",
  in_progress: "作業中",
  in_review: "レビュー",
  done: "完了",
};

export function isValidStatus(value: string): value is Status {
  return (STATUS_ORDER as readonly string[]).includes(value);
}

export interface BoardItem {
  id: number;
  name: string;
  status: Status;
  kind: "shot" | "asset";
}

export type GroupedItems = Record<Status, BoardItem[]>;

export function groupByStatus(items: BoardItem[]): GroupedItems {
  const grouped: GroupedItems = {
    not_started: [],
    in_progress: [],
    in_review: [],
    done: [],
  };

  for (const item of items) {
    grouped[item.status].push(item);
  }
  return grouped;
}
