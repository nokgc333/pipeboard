import { ItemDetail } from "@/components/ItemDetail";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default async function ShotDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ItemDetail baseUrl={API_BASE_URL} itemType="shot" itemId={Number(id)} />;
}
