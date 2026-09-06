import type { CommentDto } from "@/lib/api-client";

export function CommentList({ comments }: { comments: CommentDto[] }) {
  if (comments.length === 0) {
    return <p className="text-sm text-slate-500">まだコメントがありません。</p>;
  }

  return (
    <ul className="flex flex-col gap-2">
      {comments.map((c) => (
        <li key={c.id} className="rounded border border-slate-200 bg-white p-2 text-sm">
          {c.tag ? (
            <span className="mr-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
              {c.tag}
            </span>
          ) : null}
          <span>{c.body}</span>
        </li>
      ))}
    </ul>
  );
}
