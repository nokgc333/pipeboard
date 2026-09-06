import Link from "next/link";
import { STATUS_LABELS, STATUS_ORDER } from "@/domain/status/status";
import type { Status } from "@/domain/status/status";

export interface KanbanCardProps {
  id: number;
  name: string;
  status: Status;
  kind: "shot" | "asset";
  thumbnailUrl?: string;
  onChangeStatus: (id: number, kind: "shot" | "asset", status: Status) => void;
}

/**
 * カンバンカード（SCR-001）。
 * ドラッグ&ドロップの代替として、キーボードのみでも操作できる
 * ステータス変更セレクトを常設する（WCAG 2.2 2.5.7相当の配慮、要件定義書§7.5）。
 */
export function KanbanCard({ id, name, status, kind, thumbnailUrl, onChangeStatus }: KanbanCardProps) {
  return (
    <div
      className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm"
      aria-label={`${name}（現在のステータス: ${STATUS_LABELS[status]}）`}
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
          {kind === "shot" ? "Shot" : "Asset"}
        </span>
      </div>
      {thumbnailUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={thumbnailUrl} alt="" className="mb-2 h-20 w-full rounded object-cover" />
      ) : null}
      <Link
        href={`/${kind === "shot" ? "shots" : "assets"}/${id}`}
        className="mb-2 block truncate text-sm font-semibold text-slate-800 hover:underline"
      >
        {name}
      </Link>
      <label className="block text-xs text-slate-500">
        ステータス変更
        <select
          className="mt-1 block w-full rounded border border-slate-300 py-1 text-sm"
          value={status}
          onChange={(e) => onChangeStatus(id, kind, e.target.value as Status)}
        >
          {STATUS_ORDER.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
