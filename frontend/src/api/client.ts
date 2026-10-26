// Lớp gọi API duy nhất của frontend. UI chỉ import từ đây, không gọi fetch trực tiếp.
// VITE_USE_MOCK=true (mặc định) → dùng mock.ts; false → gọi backend thật qua proxy /api.
import * as mock from "./mock";
import type {
  CreateSessionResponse, EndSessionResponse, ErrorResponse, FinalResult, Role, StatusResponse,
} from "./types";

export class ApiError extends Error {
  constructor(public code: string, public httpStatus: number, public retryable = false) {
    super(code);
  }
}

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";
const BASE = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(BASE + path, init);
  } catch {
    throw new ApiError("NETWORK_ERROR", 0, true);
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ErrorResponse | null;
    throw new ApiError(body?.error.code ?? "INTERNAL_ERROR", res.status, body?.error.retryable ?? false);
  }
  return res as Response & { json(): Promise<T> };
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  return (await request<T>(path, init)).json() as Promise<T>;
}

export function createSession(role: Role | null, file: File): Promise<CreateSessionResponse> {
  if (USE_MOCK) return mock.createSession(role, file);
  const form = new FormData();
  if (role) form.append("role", role); // thiếu role → backend trả 400 ROLE_REQUIRED
  form.append("file", file);
  return json("/sessions", { method: "POST", body: form });
}

export const getStatus = (id: string): Promise<StatusResponse> =>
  USE_MOCK ? mock.getStatus(id) : json(`/sessions/${id}/status`);

export const getResult = (id: string): Promise<FinalResult> =>
  USE_MOCK ? mock.getResult(id) : json(`/sessions/${id}/result`);

export const retry = (id: string): Promise<StatusResponse> =>
  USE_MOCK ? mock.retry(id) : json(`/sessions/${id}/retry`, { method: "POST" });

export const endSession = (id: string): Promise<EndSessionResponse> =>
  USE_MOCK ? mock.endSession(id) : json(`/sessions/${id}`, { method: "DELETE" });

export async function exportReport(id: string, format: "docx" | "pdf"): Promise<Blob> {
  if (USE_MOCK) return mock.exportReport(format);
  return (await request(`/sessions/${id}/export?format=${format}`)).blob();
}
