// Mock backend theo TDD §5. Mục đích: làm UI khi backend chưa xong. Thay bằng API thật khi N4 xong.
// Mẹo thử các nhánh bằng tên file:
// - "busy"   → SYSTEM_BUSY (409)
// - "scan"   → REJECTED (NO_EXTRACTABLE_TEXT)
// - "fail"   → FAILED (AI_TIMEOUT ở 2 lần đầu, bấm Retry lần 2 sẽ sang COMPLETED)
// - "norisk" → COMPLETED nhưng không có rủi ro (risks = [])
// - còn lại  → COMPLETED (có đủ HIGH, MEDIUM đa nhãn, và INSUFFICIENT_EVIDENCE)
import { DATA_NOTICE, DISCLAIMER } from "../lib/notices";
import { ApiError } from "./client";
import type {
  CreateSessionResponse, EndSessionResponse, FinalResult, Role, StatusResponse,
} from "./types";

interface MockSession { id: string; role: Role; name: string; t0: number; retries: number; ended: boolean }
const sessions = new Map<string, MockSession>();
const wait = (ms = 200) => new Promise((r) => setTimeout(r, ms));
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
  if (sec < 1.2) return { ...base, status: "VALIDATING", stage: "EXTRACTION", progress: null, error_code: null };
  if (s.name.includes("scan"))
    return { ...base, status: "REJECTED", stage: null, progress: null, error_code: "NO_EXTRACTABLE_TEXT" };
  if (sec < 3.5)
    return {
      ...base,
      status: "PROCESSING",
      stage: "RISK_ANALYSIS",
      error_code: null,
      progress: { completed_units: Math.min(20, Math.round(sec * 6)), total_units: 20 },
    };
  if (s.name.includes("fail") && s.retries < 1)
    return { ...base, status: "FAILED", stage: "RISK_ANALYSIS", progress: null, error_code: "AI_TIMEOUT" };
  return { ...base, status: "COMPLETED", stage: null, progress: null, error_code: null };
}

function buildSample(id: string, role: Role, fileName: string): FinalResult {
  const parts = [
    "Điều 1. Thời gian thử việc là 90 ngày, lương thử việc bằng 70% mức lương chính thức của công việc.\n\n",
    "Điều 2. Người lao động làm việc 08 giờ/ngày từ thứ Hai đến thứ Sáu hằng tuần.\n\n",
    "Điều 3. Khi nghỉ việc, người lao động phải hoàn trả toàn bộ chi phí đào tạo và không được làm việc cho bất kỳ doanh nghiệp cùng ngành nào trong 24 tháng.\n\n",
    "Điều 4. Thưởng cuối năm phụ thuộc vào đánh giá nội bộ của công ty mà không quy định tiêu chí cụ thể.\n",
  ];
  let cursor = 0;
  const labelsByIdx = [
    ["CONTRACT_TERM", "COMPENSATION_BENEFITS"],
    ["WORKING_TIME"],
    ["TRAINING", "EMPLOYEE_OBLIGATIONS_DISCIPLINE"],
    ["COMPENSATION_BENEFITS"],
  ];
  const clauses = parts.map((p, i) => {
    const len = Array.from(p).length; // đếm theo Unicode code point
    const c = {
      clause_id: `cl_000${i + 1}`,
      original_text: p,
      start_char: cursor,
      end_char: cursor + len,
      clause_labels: labelsByIdx[i],
    };
    cursor += len;
    return c;
  });

  const isNoRisk = fileName.includes("norisk") || fileName.includes("clean");

  return {
    schema_version: "final_result_v1",
    offset_unit: "unicode_code_point",
    session_id: id,
    role,
    status: "COMPLETED",
    analysis_date: now().slice(0, 10),
    canonical_text: parts.join(""),
    clauses,
    risks: isNoRisk
      ? []
      : [
        {
          clause_id: "cl_0001",
          risk_labels: ["PROBATION"],
          risk_basis: [{ label: "PROBATION", basis_type: "LEGAL_VIOLATION" }],
          severity: "HIGH",
          explanation:
            role === "EMPLOYEE"
              ? "Lương thử việc 70% thấp hơn mức tối thiểu 85% và thời gian thử việc 90 ngày vượt quá giới hạn pháp luật cho phép, gây thiệt hại trực tiếp về thu nhập của người lao động."
              : "Quy định lương thử việc 70% và thời gian thử việc 90 ngày trái quy định bắt buộc của pháp luật lao động, dẫn đến nguy cơ điều khoản bị tuyên vô hiệu và bị xử phạt hành chính.",
          evidence_status: "SUPPORTED",
          citation_ids: ["BLLD2019:art25", "BLLD2019:art26"],
        },
        {
          clause_id: "cl_0003",
          risk_labels: ["TRAINING_COMMITMENT", "POST_EMPLOYMENT_RESTRICTION"],
          risk_basis: [
            { label: "TRAINING_COMMITMENT", basis_type: "UNFAVORABLE" },
            { label: "POST_EMPLOYMENT_RESTRICTION", basis_type: "UNFAVORABLE" },
          ],
          severity: "MEDIUM",
          explanation:
            "Điều khoản vừa buộc hoàn trả chi phí đào tạo không kèm định mức cụ thể, vừa hạn chế quyền làm việc trong 24 tháng sau khi chấm dứt hợp đồng trên phạm vi quá rộng.",
          evidence_status: "SUPPORTED",
          citation_ids: ["BLLD2019:art62"],
        },
        {
          clause_id: "cl_0004",
          risk_labels: ["BONUS_BENEFITS"],
          risk_basis: [{ label: "BONUS_BENEFITS", basis_type: "AMBIGUOUS" }],
          severity: null,
          explanation:
            "Điều khoản quy định điều kiện xét thưởng hoàn toàn phụ thuộc vào đánh giá nội bộ nhưng thiếu tiêu chí định lượng rõ ràng, dễ phát sinh tranh chấp khi thực hiện.",
          evidence_status: "INSUFFICIENT_EVIDENCE",
          citation_ids: [],
        },
      ],
    citations: [
      {
        citation_id: "BLLD2019:art25",
        document_name: "Bộ luật Lao động 2019",
        article: "25",
        content: "Thời gian thử việc không quá 60 ngày đối với công việc có chức danh nghề cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên.",
      },
      {
        citation_id: "BLLD2019:art26",
        document_name: "Bộ luật Lao động 2019",
        article: "26",
        content: "Tiền lương của người lao động trong thời gian thử việc do hai bên thỏa thuận nhưng ít nhất phải bằng 85% mức lương của công việc đó.",
      },
      {
        citation_id: "BLLD2019:art62",
        document_name: "Bộ luật Lao động 2019",
        article: "62",
        content: "Hợp đồng đào tạo nghề phải có các nội dung chủ yếu về chi phí đào tạo và trách nhiệm hoàn trả chi phí đào tạo.",
      },
    ],
    disclaimer: DISCLAIMER,
    data_notice: DATA_NOTICE,
    version_pins: {
      extraction_version: "extract_v1.1",
      clause_taxonomy_version: "clause_taxonomy_v03",
      risk_taxonomy_version: "risk_taxonomy_v02",
      severity_rubric_version: "severity_v01",
    },
  };
}

export async function getResult(id: string): Promise<FinalResult> {
  await wait();
  const s = need(id);
  return buildSample(id, s.role, s.name);
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
  return new Blob(["Báo cáo phân tích rủi ro hợp đồng (Mock DOCX)"], {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
}