<!-- nguồn: SRS_AI_Labor_Contract_Risk_Analyzer_1_4.md | mục: SRS: AI Labor Contract Risk Analyzer (phiên bản 1.4) > 8. Chất lượng AI và đánh giá | 2229 ký tự | trước: 09_7-yeu-cau-phi-chuc-nang-cho-demo.md | sau: 11_9-giao-dien-thuc-thi-toi-thieu.md -->

## 8. Chất lượng AI và đánh giá

Ngưỡng, tập dữ liệu và cách đo của mọi chỉ số nằm ở BRD 8 (DEC-06). SRS không lặp số; bảng dưới cho biết chỉ số nào kiểm tra yêu cầu nào và ID cũ ở SRS 1.1 chuyển thành ID nào.

| ID cũ (SRS 1.1) | ID trong BRD 8 | Yêu cầu SRS liên quan |
|---|---|---|
| AIQ-01 | M1 | FR-09 |
| AIQ-02 | M7 | FR-11 |
| AIQ-03 | M2 | FR-13, FR-14 |
| AIQ-04 | M3a, M3b | FR-15, FR-16 |
| AIQ-05 | M4 | FR-19, 4.2 |
| AIQ-06 | M5 | FR-13, FR-18 |
| AIQ-07 | M6 | BRD 8.5 |
| AIQ-08 | BL-1 (cắt số 1) | FR-15 (log citation trước khi lọc) |
| Mới | M8 | FR-12, FR-30 |
| NFR-SEC-01 | BRD 7.3 | FR-10 |

Yêu cầu hỗ trợ đánh giá:

* EV-01: harness đánh giá chạy pipeline như thư viện ngoại tuyến, không đi qua API và session, xuất JSON; output đánh giá lưu ngoài đường session nên không bị FR-23 xóa.
* EV-02: hợp đồng dev và test được de-identify thủ công trước khi đưa vào kho mã (BRD 7.6).
* EV-03: hệ thống ghi số citation LLM chọn ngoài candidate trước khi lọc, phục vụ M3b và BL-1.
* EV-04: mọi output ghi các trường version (FR-29) để biết mỗi phép đo dùng cấu hình nào.
* EV-05: mỗi lỗi chèn có điều luật gold, nhãn, vai trò và vị trí điều khoản được chèn; định dạng file gold cho M1, M2, M5, M7, M8 do TDD định nghĩa.
* EV-06: judge chạy ngoại tuyến và chỉ nhận dữ liệu đã che hoặc đã de-identify (BRD 7.5); sản phẩm không có API judge.
* EV-07: phiên bản hệ thống được khóa ở MS-3 và ghi commit hash vào báo cáo; không tuning trên T1 và T2.
* EV-08: harness chạy M8 ở hai cấu hình Data Graph enabled/disabled với **cùng final candidate budget**, cùng corpus/config/input ngoài graph flag. Primary M8 dùng predicted clause labels từ pipeline; có thể báo thêm oracle-label diagnostic nhưng phải tách tên. Log số candidate graph thêm.
* EV-09: harness/demo evidence xuất ContextResolutionTrace cho Clause Graph: target clause_id, related clause_ids, relation và graph flag; không contract text. Dùng fixture xác nhận context đã thực sự được đưa vào Risk stage, và graph on/off không làm đổi span.
* EV-10: evaluation harness chạy ngoài runtime admission quota/rate-limit của product, nhưng mọi provider request/token/cost được ghi vào evaluation cost ledger riêng; không được dùng eval để né ngân sách đánh giá.
