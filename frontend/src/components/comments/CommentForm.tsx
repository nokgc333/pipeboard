"use client";

import { useState } from "react";
import { validateCommentBody } from "@/domain/comment/comment-validation";

export function CommentForm({ onSubmit }: { onSubmit: (body: string, tag?: string) => void }) {
  const [body, setBody] = useState("");
  const [tag, setTag] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        const validationError = validateCommentBody(body);
        if (validationError) {
          setError(validationError);
          return;
        }
        onSubmit(body, tag || undefined);
        setBody("");
        setTag("");
        setError(null);
      }}
    >
      <textarea
        className="rounded border border-slate-300 p-2 text-sm"
        placeholder="コメントを入力"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={3}
      />
      <input
        className="rounded border border-slate-300 p-2 text-sm"
        placeholder="タグ（任意）"
        value={tag}
        onChange={(e) => setTag(e.target.value)}
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <button type="submit" className="self-start rounded bg-slate-800 px-3 py-1 text-sm text-white">
        投稿
      </button>
    </form>
  );
}
