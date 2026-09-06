import { KanbanBoard } from "@/components/kanban/KanbanBoard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function HomePage() {
  return <KanbanBoard baseUrl={API_BASE_URL} />;
}
