"use client";

import { useCallback, useEffect, useState } from "react";
import type { BoardItem, Status } from "@/domain/status/status";
import { STATUS_ORDER, groupByStatus } from "@/domain/status/status";
import { ApiError, listAssets, listShots, updateStatus } from "@/lib/api-client";
import { KanbanColumn } from "./KanbanColumn";

type LoadState = "loading" | "error" | "ready";

export interface KanbanBoardProps {
  baseUrl: string;
}

export function KanbanBoard({ baseUrl }: KanbanBoardProps) {
  const [items, setItems] = useState<BoardItem[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");

  const load = useCallback(async () => {
    setLoadState("loading");
    try {
      const [shots, assets] = await Promise.all([listShots(baseUrl), listAssets(baseUrl)]);
      const merged: BoardItem[] = [
        ...shots.map((s) => ({ ...s, kind: "shot" as const })),
        ...assets.map((a) => ({ ...a, kind: "asset" as const })),
      ];
      setItems(merged);
      setLoadState("ready");
    } catch {
      setLoadState("error");
    }
  }, [baseUrl]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleChangeStatus = useCallback(
    (id: number, kind: "shot" | "asset", nextStatus: Status) => {
      // 楽観的更新: 先にUIを更新し、失敗したら元に戻す（要件定義書FR-001シナリオ）
      let previous: Status | undefined;
      setItems((current) =>
        current.map((item) => {
          if (item.id === id && item.kind === kind) {
            previous = item.status;
            return { ...item, status: nextStatus };
          }
          return item;
        }),
      );

      updateStatus(baseUrl, kind, id, nextStatus).catch((err: unknown) => {
        if (err instanceof ApiError || err) {
          setItems((current) =>
            current.map((item) =>
              item.id === id && item.kind === kind && previous
                ? { ...item, status: previous }
                : item,
            ),
          );
        }
      });
    },
    [baseUrl],
  );

  if (loadState === "loading") {
    return <p className="p-6 text-slate-500">読み込み中…</p>;
  }

  if (loadState === "error") {
    return (
      <div className="m-6 rounded border border-red-300 bg-red-50 p-4 text-red-700">
        <p>読み込みに失敗しました。ネットワーク接続を確認してください。</p>
        <button
          type="button"
          className="mt-2 rounded bg-red-600 px-3 py-1 text-sm text-white"
          onClick={() => void load()}
        >
          再試行
        </button>
      </div>
    );
  }

  if (items.length === 0) {
    return <p className="p-6 text-slate-500">まだショット/アセットがありません。</p>;
  }

  const grouped = groupByStatus(items);

  return (
    <div className="flex gap-4 overflow-x-auto p-6">
      {STATUS_ORDER.map((status) => (
        <KanbanColumn
          key={status}
          status={status}
          items={grouped[status]}
          onChangeStatus={handleChangeStatus}
        />
      ))}
    </div>
  );
}
