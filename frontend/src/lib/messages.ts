// Catalog thông báo tiếng Việt theo error_code (TDD Phụ lục E). Không hiển thị mã kỹ thuật một mình.
const MESSAGES: Record<string, string> = {
  SYSTEM_BUSY: "Hệ thống đang xử lý một hợp đồng khác. Vui lòng thử lại sau.",
  QUOTA_EXCEEDED: "Hệ thống đã đạt giới hạn phân tích hiện tại. Vui lòng thử lại sau.",
  RATE_LIMITED: "Bạn gửi yêu cầu quá nhanh. Vui lòng chờ rồi thử lại.",
  UNSUPPORTED_FILE_TYPE: "Chỉ hỗ trợ tệp PDF hoặc DOCX có sẵn văn bản.",
  FILE_TOO_LARGE: "Tệp vượt giới hạn dung lượng cho phép.",
  PDF_PAGE_LIMIT_EXCEEDED: "PDF vượt giới hạn số trang cho phép.",
  DOCX_TEXT_LIMIT_EXCEEDED: "DOCX có nội dung vượt giới hạn ký tự cho phép.",
  NO_EXTRACTABLE_TEXT: "Không trích xuất được văn bản. Hệ thống chưa hỗ trợ tệp scan/ảnh.",
  UNSUPPORTED_TEXT_ENCODING: "Văn bản trích xuất không đọc được hoặc dùng mã/font chưa hỗ trợ.",
  NOT_LABOR_CONTRACT: "Tài liệu không được nhận diện là hợp đồng lao động trong phạm vi hệ thống.",
  TOO_MANY_CLAUSES: "Hợp đồng có quá nhiều điều khoản để xử lý trong bản demo.",
  AI_TIMEOUT: "Dịch vụ phân tích tạm thời gặp lỗi. Bạn có thể thử lại nếu phiên cho phép.",
  AI_PROVIDER_ERROR: "Dịch vụ phân tích tạm thời gặp lỗi. Bạn có thể thử lại nếu phiên cho phép.",
  AI_OUTPUT_INVALID: "Kết quả AI không đúng định dạng kỹ thuật. Bạn có thể thử lại nếu phiên cho phép.",
  REJECTED: "Tệp đã bị từ chối; muốn thử tệp khác cần mở phiên mới.",
  INSUFFICIENT_EVIDENCE: "Chưa đủ căn cứ pháp lý trong kho luật.",
  NO_RISK: "Không phát hiện rủi ro trong phạm vi phân tích. Kết quả không đồng nghĩa hợp đồng an toàn.",
  EXPIRED: "Phiên đã kết thúc và dữ liệu phiên đã được xóa.",
  // Ngoài catalog Phụ lục E — đề xuất, nhóm duyệt:
  ROLE_REQUIRED: "Vui lòng chọn vai trò trước khi tải hợp đồng.",
  NETWORK_ERROR: "Không kết nối được tới máy chủ. Vui lòng kiểm tra mạng và thử lại.",
};

export function messageFor(code: string | null | undefined): string {
  return (code && MESSAGES[code]) || "Đã có lỗi xảy ra. Vui lòng thử lại.";
}
