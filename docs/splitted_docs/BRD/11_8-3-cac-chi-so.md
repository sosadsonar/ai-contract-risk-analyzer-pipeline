<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_v0.6.md | mục: BRD: AI Labor Contract Risk Analyzer > 8. Đo lường chất lượng và nghiệm thu > 8.3 Các chỉ số | 4338 ký tự | trước: 10_8-2-du-lieu-danh-gia.md | sau: 12_8-4-danh-gia-false-negative-bang-loi-chen.md -->

### 8.3 Các chỉ số

Một "output" là một bản ghi rủi ro gồm điều khoản, nhãn, giải thích và citation. Chỉ số về dữ liệu cá nhân nằm ở §7.3.

| ID | Chỉ số | Ngưỡng | Đơn vị so khớp | Nhãn gold | Tập | Cách đo |
|---|---|---|---|---|---|---|
| M1 | Clause segmentation F1 | ≥ 0.85 | Khoảng văn bản của một điều khoản; khớp khi IoU ký tự ≥ 0.80, ghép tham lam theo IoU giảm dần | Người sửa tay | T1 | Tự động |
| M2 | Risk classification macro-F1 | ≥ 0.80 | Bộ ba (điều khoản, vai trò, risk label) | LLM khác họ gán, người xác minh | T1 | Tự động; báo per-class; macro chỉ tính nhãn có ≥ 5 mẫu |
| M3a | Citation tồn tại và hợp lệ | 100% | Mỗi điều luật được trích | Kho luật | T1, T2 | Tự động: nằm trong candidate, thuộc kho, đúng phiên bản hiệu lực tại ngày phân tích |
| M3b | Citation liên quan đến rủi ro | ≥ 85% | Mỗi điều luật được trích | Người chấm | T1 (mẫu 40 output) | Chấm tay theo rubric relevance; dùng judge nếu M6 đạt. Báo thêm số citation LLM chọn ngoài candidate trước khi lọc |
| M4 | Trích nguyên văn và vị trí | 100% | Mỗi rủi ro | Văn bản trích xuất | T1, T2 | Tự động: đoạn trích là chuỗi con nguyên văn, offset đúng |
| M5 | Recall trên lỗi chèn | ≥ 90%, với ≥ 30 lỗi chèn | Mỗi lỗi chèn | Lỗi chèn do nhóm tạo | T2 | Tự động: đúng điều khoản, đúng vai trò, đúng nhãn |
| M6 | Judge và người trùng nhau | ≥ 80% và Cohen's kappa ≥ 0.6 | Kết quả mỗi output | Hai người chấm | T1 (mẫu 40 output) | Tỷ lệ judge trùng nhãn với người; đạt cả hai thì dùng judge cho phần còn lại |
| M7 | Clause classification macro-F1 | ≥ 0.80 | Cặp (điều khoản, clause label) | Gold T1 đã khóa, người xác minh | T1 | Báo song song 747 span toàn văn và 340 điều khoản thực `[GENUINE_CLAUSE]` của lát cắt 9 tài liệu; macro chỉ tính nhãn có ≥ 5 mẫu; ghi rõ cách căn chỉnh trước khi so điểm |
| M8 | Retrieval recall@5 | ≥ 90% | Mỗi lỗi chèn | Điều luật gold của lỗi chèn | T2 | Tự động: điều luật gold nằm trong 5 candidate đầu. Chỉ số chẩn đoán. Báo thêm recall@5 khi tắt mở rộng qua Data Graph để thấy đóng góp của Graph (BR-17); không có ngưỡng riêng |
| M2b | Độ chính xác loại căn cứ (basis_type) | Báo cáo kèm khoảng tin cậy; ngưỡng đặt sau số đo dev (OI-09) | Bộ ba đã khớp ở M2 | LLM khác họ gán, người xác minh | T1 | Tự động. Severity không có chỉ số riêng vì do bảng taxonomy tra từ (nhãn, loại căn cứ, vai trò) |
| M9 | Giải thích đúng | ≥ 80% (tạm, đặt lại theo OI-09) | Mỗi output | Người chấm; judge nếu M6 đạt | T1 (cùng mẫu 40 output của M3b) | Chấm Đúng, Đúng một phần hoặc Sai: giải thích đúng căn cứ và đúng vai trò |
| M10 | Phát hiện mâu thuẫn trong hợp đồng | Báo cáo, không ngưỡng | Cặp điều khoản có cạnh trong Clause Graph | Cặp cài do nhóm tạo, kèm cặp đối chứng nhất quán | D3 | Tự động: phát hiện khi rủi ro của một trong hai điều có related_clause_ids chứa điều còn lại. Báo recall và tỷ lệ báo nhầm, so Graph tắt và mở |
| BL-1 | So với LLM thông dụng | Tỷ lệ citation sai của hệ thống ≤ một nửa của baseline | Mỗi điều luật được trích | Người đối chiếu văn bản luật thật | T1 (cùng mẫu 40) | "Sai" = không tồn tại hoặc nội dung không khớp. Cùng hợp đồng đã che, cùng vai trò, cùng yêu cầu. Baseline: LLM thông dụng chọn ở OI-07, cấu hình cụ thể ghi trong báo cáo. |

\* Ngưỡng M2, M7 và M3b được đặt lại sau số đo dev đầu tiên (OI-09). Mọi con số báo kèm khoảng tin cậy (bootstrap) và số mẫu mỗi nhãn. Bộ M1, M2, M3a, M4, M5, M7, M8 và privacy §7.3 trên D1/D2/T1/T2 là **đường đánh giá cơ sở**, dùng Gold và quy tắc đã khóa; không dùng nhãn T1/T2 làm đầu vào dự đoán hoặc tuning. M3b và M6 cần gói chấm tay/hiệu chuẩn riêng; D3, P1, M2b, M9 và M10 là **hạng mục mở rộng/chẩn đoán giai đoạn 2** cho đến khi có Gold hoặc gói đánh giá tương ứng. Thiếu gói mở rộng không xóa hoặc sửa điểm cơ sở, và cũng không được ghi hạng mục chưa chạy là đạt.

Quy đổi Gold sang đầu ra pipeline (M2, M2b, M7) cho **lần đánh giá mới có dự đoán span khác Gold**: ghép một-một tham lam theo span với IoU ≥ 0.5 (riêng M1 giữ ngưỡng 0.80); clause dự đoán thừa hưởng nhãn của clause Gold khớp; Gold không khớp tính là sót, clause dự đoán không khớp tính là báo thừa; Gold một nhãn tính trúng khi nằm trong tập 1 đến 3 nhãn dự đoán, đồng thời báo F1 theo từng nhãn. Báo cáo baseline đã khóa dùng dự đoán nhãn trên chính các span tham chiếu phải ghi rõ phạm vi đó; không diễn giải điểm baseline ấy thành điểm end-to-end sau căn chỉnh.
