// Kiểu dữ liệu khớp TDD §5 (HTTP API) và §6 (domain model, final_result_v1).
// Khi backend đổi schema: sửa file này trước, rồi mới sửa mock/UI.

export type Role = "EMPLOYEE" | "EMPLOYER";
export type SessionStatus =
  | "UPLOADED" | "VALIDATING" | "REJECTED" | "PROCESSING"
  | "COMPLETED" | "FAILED" | "EXPIRED";
export type Stage =
  | "UPLOAD" | "EXTRACTION" | "SCOPE_PRECHECK" | "PII_MASKING" | "SEGMENTATION"
  | "CLAUSE_GRAPH" | "CLAUSE_CLASSIFICATION" | "LEGAL_RETRIEVAL"
  | "RISK_ANALYSIS" | "CITATION_VALIDATION" | "ASSEMBLY" | "EXPORT";
export type Severity = "HIGH" | "MEDIUM" | "LOW" | null;
export type EvidenceStatus = "SUPPORTED" | "INSUFFICIENT_EVIDENCE";
export type BasisType = "LEGAL_VIOLATION" | "UNFAVORABLE" | "AMBIGUOUS";

/** POST /sessions → 201 */
export interface CreateSessionResponse {
  session_id: string;
  status: "UPLOADED";
  created_at: string;
}

/** GET /sessions/{id}/status. Polling không kéo dài TTL phiên. */
export interface StatusResponse {
  session_id: string;
  status: SessionStatus;
  stage: Stage | null;
  manual_retry_count: number;
  progress: { completed_units: number; total_units: number } | null;
  error_code: string | null; // bắt buộc khi REJECTED/FAILED
  updated_at: string;
}

/** Offset là Unicode code point (không phải UTF-16). Xem lib/offset.ts. */
export interface Clause {
  clause_id: string;
  original_text: string;
  start_char: number;
  end_char: number;
  clause_labels: string[];
}

export interface RiskResult {
  clause_id: string;
  risk_labels: string[]; // 1–3 nhãn thuộc risk_taxonomy_v02 (21 nhãn)
  // Backend dựng từ basis_type (LLM chọn 1 giá trị cho cả clause) + risk_labels, một-một với risk_labels.
  // Vì vậy mọi phần tử của một clause có cùng basis_type.
  risk_basis: { label: string; basis_type: BasisType }[];
  // Backend tra bảng taxonomy theo (nhãn, basis_type, vai trò), lấy mức cao nhất; LLM không trả severity.
  severity: Severity; // null khi INSUFFICIENT_EVIDENCE → KHÔNG hiện badge
  explanation: string;
  evidence_status: EvidenceStatus;
  citation_ids: string[];
}

export interface Citation {
  citation_id: string;
  document_name: string;
  article: string;
  content: string;
}

/** GET /sessions/{id}/result (chỉ khi COMPLETED) */
export interface FinalResult {
  schema_version: "final_result_v1";
  offset_unit: "unicode_code_point";
  session_id: string;
  role: Role;
  status: "COMPLETED";
  analysis_date: string;
  canonical_text: string;
  clauses: Clause[];
  risks: RiskResult[];
  citations: Citation[];
  disclaimer: string;
  data_notice: string;
  version_pins: Record<string, string>;
}

/** Body lỗi: {error:{code,message,retryable,details?}} */
export interface ErrorResponse {
  error: { code: string; message: string; retryable: boolean; details?: unknown };
}

export interface EndSessionResponse {
  session_id: string;
  status: "EXPIRED";
  message: string;
}
