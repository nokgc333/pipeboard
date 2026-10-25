/** バックエンドAPI(FastAPI)向けの薄いfetchラッパー。 */
import type { Status } from "@/domain/status/status";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface ItemDto {
  id: number;
  name: string;
  status: Status;
  created_at?: string;
  updated_at?: string;
}

export interface VersionDto {
  id: number;
  item_type: "shot" | "asset";
  item_id: number;
  version_number: number;
  thumbnail_path: string;
  original_filename: string | null;
  created_at: string;
}

export interface CommentDto {
  id: number;
  item_type: "shot" | "asset";
  item_id: number;
  body: string;
  tag: string | null;
  created_at: string;
}

function withAuthorization(init?: RequestInit): RequestInit | undefined {
  const token = process.env.NEXT_PUBLIC_API_TOKEN;
  if (!token) return init;
  return {
    ...init,
    headers: {
      ...(init?.headers as Record<string, string> | undefined),
      Authorization: `Bearer ${token}`,
    },
  };
}

async function request<T>(url: string, requestInit?: RequestInit): Promise<T> {
  const init = withAuthorization(requestInit);
  const response = init === undefined ? await fetch(url) : await fetch(url, init);
  if (!response.ok) {
    const problem = await response.json().catch(() => ({}));
    throw new ApiError(response.status, problem.title ?? `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function jsonInit(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export function listShots(baseUrl: string): Promise<ItemDto[]> {
  return request<ItemDto[]>(`${baseUrl}/shots`);
}

export function listAssets(baseUrl: string): Promise<ItemDto[]> {
  return request<ItemDto[]>(`${baseUrl}/assets`);
}

export function updateStatus(
  baseUrl: string,
  itemType: "shot" | "asset",
  itemId: number,
  status: Status,
): Promise<ItemDto> {
  const path = itemType === "shot" ? "shots" : "assets";
  return request<ItemDto>(`${baseUrl}/${path}/${itemId}/status`, jsonInit("PATCH", { status }));
}

export function listVersions(
  baseUrl: string,
  itemType: "shot" | "asset",
  itemId: number,
): Promise<VersionDto[]> {
  const path = itemType === "shot" ? "shots" : "assets";
  return request<VersionDto[]>(`${baseUrl}/${path}/${itemId}/versions`);
}

export function listComments(
  baseUrl: string,
  itemType: "shot" | "asset",
  itemId: number,
): Promise<CommentDto[]> {
  const path = itemType === "shot" ? "shots" : "assets";
  return request<CommentDto[]>(`${baseUrl}/${path}/${itemId}/comments`);
}

export function uploadVersion(
  baseUrl: string,
  itemType: "shot" | "asset",
  itemId: number,
  file: File,
): Promise<VersionDto> {
  const formData = new FormData();
  formData.append("file", file);
  return request<VersionDto>(
    `${baseUrl}/versions?item_type=${itemType}&item_id=${itemId}`,
    { method: "POST", body: formData },
  );
}

export function createComment(
  baseUrl: string,
  payload: { item_type: "shot" | "asset"; item_id: number; body: string; tag?: string },
): Promise<CommentDto> {
  return request<CommentDto>(`${baseUrl}/comments`, jsonInit("POST", payload));
}
