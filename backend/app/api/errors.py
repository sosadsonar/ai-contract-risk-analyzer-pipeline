"""Uniform error envelope for the development HTTP contract."""

from fastapi.responses import JSONResponse


MESSAGES = {
    "ROLE_REQUIRED": "Vui lòng chọn vai trò hợp lệ.",
    "SESSION_NOT_FOUND": "Không tìm thấy phiên phân tích.",
    "SESSION_EXPIRED": "Phiên đã hết hạn.",
    "SESSION_NOT_READY": "Kết quả phiên chưa sẵn sàng.",
    "SESSION_REJECTED": "Tệp tải lên đã bị từ chối.",
    "INVALID_SESSION_STATE": "Trạng thái phiên không cho phép thao tác này.",
    "RETRY_LIMIT_EXCEEDED": "Đã vượt quá số lần thử lại.",
    "FEATURE_NOT_ENABLED": "Tính năng xuất PDF chưa được bật.",
    "UNSUPPORTED_FILE_TYPE": "Định dạng tệp không được hỗ trợ.",
    "FILE_TOO_LARGE": "Tệp vượt quá giới hạn dung lượng.",
    "SYSTEM_BUSY": "Hệ thống đang xử lý phiên khác.",
    "RATE_LIMITED": "Đã vượt giới hạn số lần tải lên.",
    "QUOTA_EXCEEDED": "Đã hết hạn mức phân tích trong ngày.",
    "INTERNAL_ERROR": "Đã xảy ra lỗi xử lý nội bộ.",
}


def api_error(status: int, code: str, *, details: dict | None = None) -> JSONResponse:
    payload = {"code": code, "message": MESSAGES.get(code, MESSAGES["INTERNAL_ERROR"]),
               "retryable": code in {"SYSTEM_BUSY", "RATE_LIMITED", "QUOTA_EXCEEDED", "INTERNAL_ERROR"}}
    if details is not None:
        payload["details"] = details
    return JSONResponse(status_code=status, content={"error": payload})
