import type { BoardItem, Status } from "@/domain/status/status";
import { STATUS_LABELS } from "@/domain/status/status";
import { KanbanCard } from "./KanbanCard";

export interface KanbanColumnProps {
  status: Status;
  items: BoardItem[];
  onChangeStatus: (id: number, kind: "shot" | "asset", status: Status) => void;
}

export function KanbanColumn({ status, items, onChangeStatus }: KanbanColumnProps) {
  return (
    <div className="flex min-w-64 flex-1 flex-col rounded-lg bg-slate-50 p-3">
      <h2 className="mb-3 text-sm font-bold text-slate-700">
        {STATUS_LABELS[status]}
        <span className="ml-2 text-xs font-normal text-slate-400">{items.length}</span>
      </h2>
      <div className="flex flex-col gap-2">
        {items.map((item) => (
          <KanbanCard
            key={`${item.kind}-${item.id}`}
            id={item.id}
            name={item.name}
            status={item.status}
            kind={item.kind}
            onChangeStatus={onChangeStatus}
          />
        ))}
      </div>
    </div>
  );
}
