// Mock backend theo TDD §5. Mục đích: làm UI khi backend chưa xong. Thay bằng API thật khi N4 xong.
// Mẹo thử các nhánh bằng tên file: "busy" → SYSTEM_BUSY; "scan" → REJECTED; "fail" → FAILED; còn lại → COMPLETED.
import { DATA_NOTICE, DISCLAIMER } from "../lib/notices";
import { ApiError } from "./client";
import type {
  CreateSessionResponse, EndSessionResponse, FinalResult, Role, StatusResponse,
} from "./types";

interface MockSession { id: string; role: Role; name: string; t0: number; retries: number; ended: boolean }
const sessions = new Map<string, MockSession>();
const wait = (ms = 250) => new Promise((r) => setTimeout(r, ms));
const now = () => new Date().toISOString();

export async function createSession(role: Role | null, file: File): Promise<CreateSessionResponse> {
  await wait();
  if (!role) throw new ApiError("ROLE_REQUIRED", 400);
  if (file.name.toLowerCase().includes("busy")) throw new ApiError("SYSTEM_BUSY", 409, true);
  const id = crypto.randomUUID();
  sessions.set(id, { id, role, name: file.name.toLowerCase(), t0: Date.now(), retries: 0, ended: false });
  return { session_id: id, status: "UPLOADED", created_at: now() };
}

function need(id: string): MockSession {
  const s = sessions.get(id);
  if (!s) throw new ApiError("SESSION_NOT_FOUND", 404);
  return s;
}

export async function getStatus(id: string): Promise<StatusResponse> {
  await wait(100);
  const s = need(id);
  const base = { session_id: id, manual_retry_count: s.retries, updated_at: now() };
  if (s.ended) return { ...base, status: "EXPIRED", stage: null, progress: null, error_code: null };
  const sec = (Date.now() - s.t0) / 1000;
  if (sec < 1.5) return { ...base, status: "VALIDATING", stage: "EXTRACTION", progress: null, error_code: null };
  if (s.name.includes("scan"))
    return { ...base, status: "REJECTED", stage: null, progress: null, error_code: "NO_EXTRACTABLE_TEXT" };
  if (sec < 4)
    return { ...base, status: "PROCESSING", stage: "RISK_ANALYSIS", error_code: null,
             progress: { completed_units: Math.round(sec * 5), total_units: 20 } };
  if (s.name.includes("fail") && s.retries < 2)
    return { ...base, status: "FAILED", stage: "RISK_ANALYSIS", progress: null, error_code: "AI_TIMEOUT" };
  return { ...base, status: "COMPLETED", stage: null, progress: null, error_code: null };
}

// Dựng clause theo code point (giống backend) để UI test highlight đúng.
function buildSample(id: string, role: Role): FinalResult {
  const parts = [
    "Điều 1. Thời gian thử việc là 90 ngày, lương thử việc bằng 50% lương chính thức.\n",
    "Điều 2. Người lao động phải hoàn thành công việc theo yêu cầu của công ty.\n",
  ];
  let cursor = 0;
  const clauses = parts.map((p, i) => {
    const len = Array.from(p).length;
    const c = { clause_id: `cl_000${i + 1}`, original_text: p, start_char: cursor, end_char: cursor + len,
                clause_labels: [i === 0 ? "CONTRACT_TERM" : "JOB_INFO"] };
    cursor += len;
    return c;
  });
  return {
    schema_version: "final_result_v1", offset_unit: "unicode_code_point", session_id: id, role,
    status: "COMPLETED", analysis_date: now().slice(0, 10), canonical_text: parts.join(""), clauses,
    risks: [{
      clause_id: "cl_0001", risk_labels: ["PROBATION"], // risk_taxonomy_v02: 21 nhãn, xem lib/labels.ts
      risk_basis: [{ label: "PROBATION", basis_type: "LEGAL_VIOLATION" }],
      severity: "HIGH", explanation: "Dữ liệu mẫu (mock).", evidence_status: "SUPPORTED",
      citation_ids: ["BLLD2019:art26"],
    }],
    citations: [{ citation_id: "BLLD2019:art26", document_name: "Bộ luật Lao động 2019", article: "26", content: "(mock)" }],
    disclaimer: DISCLAIMER, data_notice: DATA_NOTICE, version_pins: { mock: "true" },
  };
}

export async function getResult(id: string): Promise<FinalResult> {
  await wait();
  const s = need(id);
  return buildSample(id, s.role);
}

export async function retry(id: string): Promise<StatusResponse> {
  await wait();
  const s = need(id);
  if (s.retries >= 2) throw new ApiError("RETRY_LIMIT_EXCEEDED", 409);
  s.retries += 1;
  s.t0 = Date.now();
  return getStatus(id);
}

export async function endSession(id: string): Promise<EndSessionResponse> {
  await wait();
  need(id).ended = true;
  return { session_id: id, status: "EXPIRED", message: "Phiên đã kết thúc và dữ liệu phiên đã được xóa." };
}

export async function exportReport(format: "docx" | "pdf"): Promise<Blob> {
  await wait();
  if (format === "pdf") throw new ApiError("FEATURE_NOT_ENABLED", 501);
  return new Blob(["mock"], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
}
