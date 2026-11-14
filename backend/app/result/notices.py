"""Disclaimer + data notice (BRD Phụ lục A, FR-25). Chữ PHẢI trùng `frontend/src/lib/notices.ts`
(test `tests/unit/test_pipeline.py::test_notices_match_frontend` khóa). Câu missing-clause theo TDD §16.1."""

DISCLAIMER = (
    "Kết quả do AI tạo ra chỉ mang tính tham khảo, không phải tư vấn pháp lý và không thay thế ý kiến của luật sư. "
    "Hệ thống có thể bỏ sót hoặc đánh giá chưa chính xác một số điều khoản. "
    "Hệ thống không kiểm tra rủi ro do điều khoản bị thiếu trong hợp đồng."
)

DATA_NOTICE = (
    "Hệ thống tự động ẩn thông tin cá nhân nhận dạng được (họ tên, số giấy tờ, địa chỉ, thông tin liên lạc) "
    "trước khi gửi nội dung đi phân tích. Dữ liệu được xóa khi kết thúc phiên. "
    "Việc ẩn tự động có thể không đạt tuyệt đối."
)
