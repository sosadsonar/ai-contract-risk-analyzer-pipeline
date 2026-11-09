// Tên hiển thị tiếng Việt cho các giai đoạn (Stage) phân tích (TDD §5.3, §5.9).
// Không in mã kỹ thuật thô cho người dùng.
import type { Stage } from "../api/types";

export const STAGE_NAMES: Record<Stage, string> = {
  UPLOAD: "Đang nhận tệp hợp đồng",
  EXTRACTION: "Trích xuất và chuẩn hóa văn bản",
  SCOPE_PRECHECK: "Kiểm tra phạm vi hợp đồng lao động",
  PII_MASKING: "Ẩn thông tin cá nhân (PII)",
  SEGMENTATION: "Tách các điều khoản",
  CLAUSE_GRAPH: "Dựng đồ thị quan hệ điều khoản",
  CLAUSE_CLASSIFICATION: "Phân loại điều khoản (AI)",
  LEGAL_RETRIEVAL: "Đối chiếu kho văn bản pháp luật",
  RISK_ANALYSIS: "Phân tích rủi ro theo vai trò (AI)",
  CITATION_VALIDATION: "Kiểm tra trích dẫn điều luật",
  ASSEMBLY: "Tổng hợp báo cáo kết quả",
  EXPORT: "Chuẩn bị xuất báo cáo",
};

/**
 * Trả về tên hiển thị tiếng Việt của stage.
 * Nếu stage lạ/chưa có trong catalog, trả về thông báo chung thân thiện ("Đang xử lý…"),
 * tuyệt đối không hiển thị mã kỹ thuật thô cho người dùng.
 */
export function getStageName(stage: string | null | undefined): string {
  if (!stage) return "Khởi tạo phiên";
  return (STAGE_NAMES as Record<string, string>)[stage] ?? "Đang xử lý…";
}

