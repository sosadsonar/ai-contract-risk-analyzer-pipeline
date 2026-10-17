<!-- nguồn: SRS_AI_Labor_Contract_Risk_Analyzer_1_4.md | mục: SRS: AI Labor Contract Risk Analyzer (phiên bản 1.4) > 11. Truy vết BRD và SRS | 2853 ký tự | trước: 12_10-quy-tac-nghiep-vu-bat-buoc.md | sau: 14_12-tieu-chi-nghiem-thu-he-thong.md -->

## 11. Truy vết BRD và SRS

### 11.1 Từ BRD sang SRS

| BRD | SRS liên quan | Ghi chú |
|---|---|---|
| BO-1 | FR-01 đến FR-25; NFR-PERF-01 | Luồng chính và thời gian; nghiệm thu ở BRD 8.6 |
| BO-2 | FR-12, FR-15, FR-16, FR-18, FR-30 | M3a, M3b, M4, M8 |
| BO-3 | FR-13, FR-14 | Ca mẫu BRD 3.3 làm test case |
| BO-4 | FR-10; NFR-SEC-01 | Ngưỡng ở BRD 7.3 |
| BO-5 | FR-30, FR-31; EV-08, EV-09 | Data Graph có M8 graph on/off; Clause Graph có context trace/fixture làm bằng chứng Validation & Reasoning |
| BR-01 | FR-01, FR-02 | Vai trò, phiên |
| BR-02 | FR-03, FR-22 | Input và export |
| BR-03 | FR-04, FR-05, FR-06, FR-09; R-12 | Từ chối file không hỗ trợ, scan, ngoài phạm vi, quá nhiều clause |
| BR-04 | FR-10; NFR-SEC-01 đến NFR-SEC-05 | Che dữ liệu cá nhân và bảo mật |
| BR-05a, BR-05b | FR-07, FR-09, FR-19; R-20; M4 | Canonical text, code-point span, non-overlap, quote |
| BR-05c | 4.3 và TDD | Schema |
| BR-06 | FR-13, FR-17 | Risk và giải thích theo vai trò |
| BR-07 | FR-12, FR-15, FR-16 | Căn cứ pháp lý, citation |
| BR-08 | FR-14 | Severity |
| BR-09 | FR-19 | Highlight trên canonical text (DEC-04) |
| BR-10 | FR-25 | Disclaimer |
| BR-11 | FR-17; R-11 | Không đưa lời khuyên |
| BR-12 | FR-25; NFR-SEC | Thông báo dữ liệu |
| BR-13 | FR-23; NFR-DATA-01 | Xóa dữ liệu phiên |
| BR-14 | FR-24; NFR-MAINT-01 | Quản lý kho luật |
| BR-15 | FR-18; R-10 | Thiếu căn cứ |
| BR-16 | FR-27; NFR-COST-02 | Trần chi phí |
| BR-17 | FR-12, FR-24, FR-30 | Data Graph |
| BR-18 | FR-31; EV-09 | Clause Graph + Context Resolver/trace |
| BRD 6, đồng thời | FR-26; NFR-SCALE-01 | Một phiên xử lý tại một thời điểm |
| BRD 8 | SRS 8; EV-01 đến EV-10 | Evaluation Plan nằm ở BRD; SRS bổ sung protocol/evidence kỹ thuật |
| BRD 10 | FR-09 (fixture ca dị thường), FR-27, FR-28 | Hard cases, giới hạn lượt, giảm chi phí và độ trễ |

### 11.2 Từ SRS sang BRD

Mỗi yêu cầu SRS có nguồn gốc nghiệp vụ trong BRD, hoặc phải ghi lý do. Các yêu cầu không phải bản dịch trực tiếp của một BR:

| SRS | Nguồn trong BRD | Lý do |
|---|---|---|
| FR-02 (session_id ngẫu nhiên), NFR-SEC-03 | BR-01; BRD 7 | Bảo mật phiên khi không có tài khoản |
| FR-21 (hạn mức retry) | BRD 4.2, 6 | Kiểm soát chi phí khi LLM lỗi |
| NFR-REL-03 (stage resume) | BRD 10 (lưu đệm kết quả trung gian) | Giảm chi phí; hạng mục cắt số 2 |
| FR-28 (xử lý theo lô) | BRD 6 hiệu năng và chi phí | Đạt 2 phút và giữ ngân sách |
| FR-29, NFR-REPRO-01 | BRD 8.1 | Mọi con số phải kèm nguồn và cấu hình đo |
| NFR-DATA-03 | BR-03 | Từ chối text rác thay vì đưa vào AI |
| NFR-DATA-04 | BR-13 | Dữ liệu hợp đồng không tồn tại ngoài phiên |
| NFR-SEC-06 | BRD 7.5 | Nhà cung cấp LLM và cấu hình model |
| NFR-MAINT-03 | BR-14, BR-17 | Dữ liệu graph cập nhật không sửa mã |
| EV-01 đến EV-10 | BRD 7.6, 8; BR-17, BR-18 | Hỗ trợ đánh giá, fair graph A/B, Clause Graph trace và cost isolation |
