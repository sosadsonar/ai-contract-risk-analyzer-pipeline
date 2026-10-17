<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 1. Mục đích và nguyên tắc thiết kế | 2638 ký tự | trước: 01_kiem-soat-tai-lieu.md | sau: 03_2-system-context.md -->

# 1. Mục đích và nguyên tắc thiết kế

SDD chuyển các yêu cầu nghiệp vụ và yêu cầu phần mềm thành một kiến trúc có thể triển khai, đồng thời giữ nguyên các invariant và giới hạn đã chốt trong BRD/SRS.

## 1.1 Nguyên tắc kiến trúc

* Modular Monolith: một backend triển khai duy nhất, chia module rõ ràng thay vì microservices. Lý do: nhóm 5 người, 8 tuần xây dựng, ngân sách hạn chế và chỉ một phiên xử lý tại một thời điểm.
* Privacy by design: canonical text không rời trusted backend; chỉ masked text được gửi tới LLM bên thứ ba.
* Backend authoritative: backend sở hữu session, span, quote, citation validation và final assembly; LLM chỉ trả structured analysis theo ID.
* Ephemeral session data: nội dung hợp đồng, kết quả và Clause Graph chỉ tồn tại trong bộ nhớ/kho tạm theo phiên, không ghi vào kho bền vững.
* Closed-corpus grounding: mọi citation phải xuất phát từ kho luật nội bộ, đúng phiên bản hiệu lực tại ngày phân tích.
* Graph as augmentation, not authority: Data Graph chỉ mở rộng retrieval; Clause Graph chỉ hỗ trợ Validation & Reasoning, không được sửa quote/span.
* Graceful fallback: Data Graph bị tắt/lỗi thì dùng retrieval nền; các tính năng cắt theo BRD không được phá luồng chính.

## 1.2 Các quyết định SDD bổ sung

| ID | Quyết định SDD | Lý do / nguồn |
|---|---|---|
| SDD-01 | Backend dùng kiến trúc Modular Monolith với một Analysis Orchestrator trung tâm. | Phù hợp giới hạn 5 người, 8 tuần, một phiên xử lý. |
| SDD-02 | Session store mặc định ở bộ nhớ tiến trình; file upload chỉ dùng temp storage nếu parser yêu cầu và bị xóa theo session. | Tuân NFR-DATA-04; codebase hiện tại cần bỏ lưu contract trong PostgreSQL. |
| SDD-03 | Retrieval nền = bảng ánh xạ clause/risk label sang provision + lexical search; embedding chưa thuộc baseline. | Theo giá trị tạm OI-07; embedding chỉ cân nhắc nếu M8 trên D2 không đạt. |
| SDD-04 | Data Graph được load thành adjacency index trong backend; không dùng graph database cho demo. | Giảm phạm vi; graph là dữ liệu corpus, không cần hạ tầng riêng. |
| SDD-05 | Data Graph mở rộng tối đa 1 hop từ seed candidate; seed được ưu tiên trước neighbor; trọng số chi tiết để TDD chốt. | Theo giá trị tạm OI-09; kiểm soát chi phí/độ trễ. |
| SDD-06 | Clause Graph được dùng làm Context Resolver cho Risk stage: lấy các clause liên quan trực tiếp để cung cấp masked context, không tạo thêm LLM call. | Hiện thực mục tiêu Validation & Reasoning mà không đổi pipeline hai LLM call. |
| SDD-07 | Operational metadata (RunLog, quota/rate counters) có thể lưu bền vững nhưng tuyệt đối không chứa contract content. | NFR-DATA-04 chỉ cấm nội dung phiên; NFR-COST cần log chi phí. |
