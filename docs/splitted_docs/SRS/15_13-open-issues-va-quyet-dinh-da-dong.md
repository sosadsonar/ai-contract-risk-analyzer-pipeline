<!-- nguồn: SRS_AI_Labor_Contract_Risk_Analyzer_1_4.md | mục: SRS: AI Labor Contract Risk Analyzer (phiên bản 1.4) > 13. Open Issues và quyết định đã đóng | 2441 ký tự | trước: 14_12-tieu-chi-nghiem-thu-he-thong.md | sau: 16_phu-luc-c-thay-doi-can-lam-o-codebase-hien-tai-ghi.md -->

## 13. Open Issues và quyết định đã đóng

Open Issues của BRD nằm ở BRD 11 và vẫn có hiệu lực. Bảng dưới theo dõi riêng các OI kỹ thuật của SRS; `CLOSED` nghĩa là SDD/TDD đã khóa cách làm, còn giá trị cấu hình vẫn có thể tune trên D1 nếu tài liệu cho phép.

| ID | Trạng thái | Vấn đề / quyết định | Chịu trách nhiệm | Hạn / ghi chú |
|---|---|---|---|---|
| OI-01 | CLOSED | Runtime pipeline đã refine ở SDD 0.1/TDD 0.2; mọi thay đổi tiếp theo phải giữ invariant 2.2/4.2. | Cả nhóm | Đóng 13/10/2026 |
| OI-02 | CLOSED | Placeholder cùng số Unicode code point; tag ASCII theo loại + padding `_` theo TDD 0.2; không reverse mapping. | Cả nhóm | Đóng 13/10/2026 |
| OI-03 | OPEN | Exact keyword/score threshold của local HĐLĐ precheck và bộ test dương/âm. SRS 1.4 đã khóa: strong-title chỉ tính ở vùng đầu, body mention đơn lẻ không đủ. | Cả nhóm | MS-2; tune trên D1 |
| OI-04 | CLOSED | Default TDD: clause batch 20, risk batch 6, LLM parallelism 2; được benchmark/tune trên D1 và phải version config. | Cả nhóm | Đóng về contract; tuning trước MS-2 |
| OI-05 | OPEN | Daily LLM quota và session reserve phải chốt từ D1 + giá model + ngân sách $5; rate-limit default TDD 5 upload/10 phút có thể tune. | Cả nhóm | MS-2 |
| OI-06 | CLOSED | EXPIRED tombstone mặc định 24 giờ, chỉ metadata, sau đó SESSION_NOT_FOUND. | Cả nhóm | Đóng 13/10/2026 |
| OI-07 | CLOSED | Baseline retrieval = label map + BM25; embedding disabled mặc định, chỉ cân nhắc nếu D2/M8 cho thấy cần; Data Graph là augmentation. | Cả nhóm | Đóng 13/10/2026 |
| OI-08 | CLOSED | Clause Graph dùng NEXT/PARENT_OF/REFERS_TO làm Context Resolver cho Risk stage; max context/candidate chi tiết ở TDD; có ContextResolutionTrace/optional related_clause_ids. | Cả nhóm | Đóng 13/10/2026 |
| OI-09 | CLOSED | Data Graph adjacency in-memory, tối đa 1 hop; seed/final candidate và neighbor cap cấu hình ở TDD; graph on/off cùng final_k cho EV-08. | Cả nhóm + Người phụ trách dữ liệu | Đóng 13/10/2026; weights tune D1/D2 |
| OI-10 | OPEN | Chính sách đa nhãn clause: 1 đến 3 nhãn, ưu tiên một nhãn; cần freeze chính thức cùng annotation guideline. | Người phụ trách dữ liệu, Clause AI | MS-1 |
| OI-11 | OPEN | Phạm vi kiểu đánh số tự động DOCX theo hợp đồng thực có trong D1/T1. | Cả nhóm | MS-2 |
| OI-12 | NARROWED | PII masking local: regex/anchor + heuristic trước; local NER chỉ thêm nếu D1 không đạt BRD 7.3. Placeholder format đã đóng ở OI-02. | Cả nhóm | MS-2, dựa số đo D1 |
