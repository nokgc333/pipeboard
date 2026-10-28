"use client";

import { useCallback, useEffect, useState } from "react";
import type { BoardItem, Status } from "@/domain/status/status";
import { STATUS_LABELS, STATUS_ORDER, groupByStatus } from "@/domain/status/status";
import { ApiError, listAssets, listShots, updateStatus } from "@/lib/api-client";
import { KanbanColumn } from "./KanbanColumn";

type LoadState = "loading" | "error" | "ready";

/** Read every shot and asset as board items. It sets no state, so an effect can call it safely. */
async function fetchBoard(baseUrl: string): Promise<BoardItem[]> {
  const [shots, assets] = await Promise.all([listShots(baseUrl), listAssets(baseUrl)]);
  return [
    ...shots.map((s) => ({ ...s, kind: "shot" as const })),
    ...assets.map((a) => ({ ...a, kind: "asset" as const })),
  ];
}

export interface KanbanBoardProps {
  baseUrl: string;
}

export function KanbanBoard({ baseUrl }: KanbanBoardProps) {
  const [items, setItems] = useState<BoardItem[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [announcement, setAnnouncement] = useState("");

  // Bumped by "retry" to run the load again.
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let isCurrent = true;
    fetchBoard(baseUrl)
      .then((merged) => {
        if (!isCurrent) return;
        setItems(merged);
        setLoadState("ready");
      })
      .catch(() => {
        if (isCurrent) setLoadState("error");
      });
    return () => {
      isCurrent = false;
    };
  }, [baseUrl, attempt]);

  const retry = useCallback(() => {
    setLoadState("loading");
    setAttempt((n) => n + 1);
  }, []);

  const handleChangeStatus = useCallback(
    (id: number, kind: "shot" | "asset", nextStatus: Status) => {
      // 楽観的更新: 先にUIを更新し、失敗したら元に戻す（要件定義書FR-001シナリオ）
      let previous: Status | undefined;
      let name = "";
      setItems((current) =>
        current.map((item) => {
          if (item.id === id && item.kind === kind) {
            previous = item.status;
            name = item.name;
            return { ...item, status: nextStatus };
          }
          return item;
        }),
      );

      updateStatus(baseUrl, kind, id, nextStatus)
        .then(() => setAnnouncement(`${name}を「${STATUS_LABELS[nextStatus]}」に変更しました`))
        .catch((err: unknown) => {
          setItems((current) =>
            current.map((item) =>
              item.id === id && item.kind === kind && previous
                ? { ...item, status: previous }
                : item,
            ),
          );
          const reason = err instanceof ApiError ? `（${err.message}）` : "";
          setAnnouncement(`${name}の更新に失敗したため元に戻しました${reason}`);
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
          onClick={retry}
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
    <div className="p-6">
      <p role="status" aria-live="polite" className="mb-3 min-h-5 text-sm text-slate-700">
        {announcement}
      </p>
      <div className="flex gap-4 overflow-x-auto">
        {STATUS_ORDER.map((status) => (
          <KanbanColumn
            key={status}
            status={status}
            items={grouped[status]}
            onChangeStatus={handleChangeStatus}
          />
        ))}
      </div>
    </div>
  );
}
