"use client";

import { useCallback, useEffect, useState } from "react";
import { STATUS_LABELS } from "@/domain/status/status";
import type { ItemDto, VersionDto, CommentDto } from "@/lib/api-client";
import {
  createComment,
  listComments,
  listVersions,
  uploadVersion,
  listShots,
  listAssets,
} from "@/lib/api-client";
import { VersionGallery } from "@/components/gallery/VersionGallery";
import { UploadForm } from "@/components/gallery/UploadForm";
import { CommentList } from "@/components/comments/CommentList";
import { CommentForm } from "@/components/comments/CommentForm";

export interface ItemDetailProps {
  baseUrl: string;
  itemType: "shot" | "asset";
  itemId: number;
}

type LoadState = "loading" | "error" | "ready";

export function ItemDetail({ baseUrl, itemType, itemId }: ItemDetailProps) {
  const [item, setItem] = useState<ItemDto | null>(null);
  const [versions, setVersions] = useState<VersionDto[]>([]);
  const [comments, setComments] = useState<CommentDto[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");

  const load = useCallback(async () => {
    setLoadState("loading");
    try {
      const list = itemType === "shot" ? await listShots(baseUrl) : await listAssets(baseUrl);
      const found = list.find((i) => i.id === itemId) ?? null;
      const [versionList, commentList] = await Promise.all([
        listVersions(baseUrl, itemType, itemId),
        listComments(baseUrl, itemType, itemId),
      ]);
      setItem(found);
      setVersions(versionList);
      setComments(commentList);
      setLoadState("ready");
    } catch {
      setLoadState("error");
    }
  }, [baseUrl, itemType, itemId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loadState === "loading") {
    return <p className="p-6 text-slate-500">読み込み中…</p>;
  }

  if (loadState === "error" || item === null) {
    return (
      <div className="m-6 rounded border border-red-300 bg-red-50 p-4 text-red-700">
        <p>読み込みに失敗しました。</p>
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

  return (
    <div className="mx-auto max-w-3xl p-6">
      <header className="mb-6 flex items-center gap-3">
        <h1 className="text-xl font-bold text-slate-800">{item.name}</h1>
        <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">
          {STATUS_LABELS[item.status]}
        </span>
      </header>

      <section className="mb-8">
        <h2 className="mb-2 text-sm font-bold text-slate-700">バージョン</h2>
        <VersionGallery versions={versions} baseUrl={baseUrl} />
        <div className="mt-3">
          <UploadForm
            onUpload={(file) => {
              void uploadVersion(baseUrl, itemType, itemId, file).then((v) =>
                setVersions((current) => [v, ...current]),
              );
            }}
          />
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-bold text-slate-700">コメント</h2>
        <CommentList comments={comments} />
        <div className="mt-3">
          <CommentForm
            onSubmit={(body, tag) => {
              void createComment(baseUrl, { item_type: itemType, item_id: itemId, body, tag }).then(
                (c) => setComments((current) => [...current, c]),
              );
            }}
          />
        </div>
      </section>
    </div>
  );
}
