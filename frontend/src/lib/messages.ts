// Catalog thông báo tiếng Việt theo error_code (TDD Phụ lục E + SRS 6.2). Không hiển thị mã kỹ thuật một mình.
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
  // Các mã bổ sung từ SRS 6.2 & TDD §5.8:
  ROLE_REQUIRED: "Vui lòng chọn vai trò trước khi tải hợp đồng.",
  NETWORK_ERROR: "Không kết nối được tới máy chủ. Vui lòng kiểm tra mạng và thử lại.",
  RETRY_LIMIT_EXCEEDED: "Phiên đã vượt quá số lần thử lại cho phép (tối đa 2 lần).",
  INVALID_SESSION_STATE: "Trạng thái phiên hiện tại không cho phép thực hiện thao tác này.",
  SESSION_NOT_READY: "Kết quả phân tích chưa sẵn sàng. Vui lòng chờ hoàn tất.",
  SESSION_REJECTED: "Tệp hợp đồng đã bị từ chối trong phiên này.",
  SESSION_EXPIRED: "Phiên làm việc đã hết hạn và dữ liệu đã được xóa.",
  SESSION_NOT_FOUND: "Không tìm thấy phiên làm việc hoặc phiên đã bị xóa.",
  FEATURE_NOT_ENABLED: "Tính năng này hiện chưa được bật trong bản demo.",
  INTERNAL_ERROR: "Hệ thống gặp sự cố nội bộ trong quá trình xử lý. Bạn có thể thử lại nếu phiên cho phép.",
};

export function messageFor(code: string | null | undefined): string {
  return (code && MESSAGES[code]) || "Đã có lỗi xảy ra. Vui lòng thử lại.";
}