<!-- nguồn: SRS_AI_Labor_Contract_Risk_Analyzer_1_4.md | mục: SRS: AI Labor Contract Risk Analyzer (phiên bản 1.4) > 12. Tiêu chí nghiệm thu hệ thống | 2014 ký tự | trước: 13_11-truy-vet-brd-va-srs.md | sau: 15_13-open-issues-va-quyet-dinh-da-dong.md -->

## 12. Tiêu chí nghiệm thu hệ thống

* Toàn bộ FR-01 đến FR-31 có test case hoặc minh chứng demo tương ứng.
* Luồng end-to-end chạy trọn vẹn cho cả NLĐ và NSDLĐ trên T1; năm ca mẫu ở BRD 3.3 cho kết quả đúng theo từng vai trò.
* Pipeline tuân đúng invariant ở 4.2: masked_text cùng độ dài canonical_text, span code-point áp dụng cho canonical_text, clause spans non-overlap, outbound LLM chỉ có masked text, join bằng clause_id.
* Không có missing-clause risk trong output; mọi risk có clause_id.
* Clause taxonomy và risk taxonomy là hai artifact riêng đã đóng băng cho đánh giá.
* Severity tuân rubric 2.3 và là null khi thiếu căn cứ.
* Không có citation ngoài candidate hoặc closed corpus (M3a = 100%).
* REJECTED và FAILED được phân biệt đúng; các input reject sau session creation xuất hiện qua Get Status; REJECTED không retry. FAILED local/process retry về đúng state, SYSTEM_BUSY không tăng counter, lần thứ 3 mới RETRY_LIMIT_EXCEEDED.
* Phiên thứ hai bị từ chối khi đang có phiên xử lý (FR-26); trần chi phí hoạt động (FR-27).
* NFR về bảo mật, dữ liệu, chi phí, hiệu năng có bằng chứng đo được trong môi trường demo.
* Các chỉ số ở BRD 7.3 và 8.3 (M1 đến M8, BL-1 nếu chưa bị cắt) được báo theo ngưỡng, hoặc có giải trình rõ nếu chưa đạt.
* Không tuning hệ thống trên T1 và T2 (EV-07).
* Data Graph dựng được từ corpus fixture; build lỗi bị chặn; không đưa citation ngoài kho/hết hiệu lực; M8 graph on/off dùng cùng final_k và primary run dùng predicted labels (FR-30, EV-08).
* Clause Graph dựng cho mọi phiên COMPLETED, chỉ chứa ID, xóa cùng phiên, không làm đổi span; fixture loại trừ dẫn chiếu luật và ContextResolutionTrace chứng minh context đã được cấp cho Risk stage (FR-31, EV-09).
* `risk_basis` trong final result khớp risk taxonomy; Clause Classification request không có role; export chứa cả disclaimer và data notice.
* Demo chạy một backend worker/process; evaluation cost ledger tách khỏi runtime quota (NFR-SCALE-01, EV-10).
* Không có nội dung hợp đồng trong kho bền vững (NFR-DATA-04).
