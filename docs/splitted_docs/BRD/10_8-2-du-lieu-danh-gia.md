<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_v0.6.md | mục: BRD: AI Labor Contract Risk Analyzer > 8. Đo lường chất lượng và nghiệm thu > 8.2 Dữ liệu đánh giá | 4160 ký tự | trước: 09_8-1-nguyen-tac-va-gioi-han.md | sau: 11_8-3-cac-chi-so.md -->

### 8.2 Dữ liệu đánh giá

| Tập | Nội dung | Dùng cho |
|---|---|---|
| D1 | HDLD001–004: 4 hợp đồng Dev, 183 điều khoản đã REVIEWED; HDLD005 không thuộc D1 | Phát triển, tuning prompt, few-shot; kiểm tra theo nhóm mẫu giống nhau khi cần; không báo số nghiệm thu |
| D2 | 4 tài liệu Dev HDLD001–004, 236 span phân đoạn và 30 lỗi chèn đã duyệt (8 + 8 + 7 + 7), tách khỏi T2 | Phát triển và đo lỗi chèn Dev |
| D3 | Bản sao hợp đồng D1 cài tối thiểu 10 cặp điều khoản mâu thuẫn (cặp có cạnh trong Clause Graph) và 10 cặp đối chứng nhất quán | M10 |
| T1 | Cổng tương đương `T1_EQUIVALENT_GATE_V1`: HDLD005–014, gồm 4 tài liệu thực/nội bộ hạn chế truy cập, 5 biểu mẫu công khai và 1 đối chứng tổng hợp; HDLD005 luôn thuộc T1 | M1, M2, M3a, M4, M7; M3b/M6 và các chỉ số mở rộng khi có gói đánh giá tương ứng |
| T2 | 9 tài liệu phát sinh từ T1 thực/mẫu HDLD005–013, 872 span và 30 lỗi chèn (8.4); HDLD014 không nằm trong T2 hiện hành | M3a, M4, M5, M8 |
| P1 (mở rộng) | PII giả sinh bằng script, chèn vào hợp đồng đã de-identify tại vị trí đã biết; tối thiểu 100 mẫu mỗi loại nhóm recall 99% và 50 mẫu mỗi loại nhóm 90%; có mẫu âm và lỗi trích PDF; bộ sinh tách khỏi regex masker | Chẩn đoán bổ sung cho §7.3 khi gói P1 sẵn sàng |

#### Cổng tiếp nhận tương đương T1 — `T1_EQUIVALENT_GATE_V1

Nhóm (`DucAnh_N2`, `argon`, `Minh_N1`) phê duyệt cổng đa tầng để đánh giá trong điều kiện không thể đưa hợp đồng đã ký chứa dữ liệu cá nhân vào Git công khai. Việc quản lý dữ liệu cá nhân chịu ràng buộc của Nghị định 13/2023/NĐ-CP; biên nhận này là quyết định nghiệm thu **trong dự án**, không tự chứng minh quyền phân phối, sự đồng ý của chủ thể dữ liệu hay tuân thủ pháp luật cho từng nguồn. Văn bản gốc hạn chế truy cập và Gold có nội dung nhạy cảm chỉ lưu cục bộ. File băm SHA-256 chứng minh tính đồng nhất của bản lưu, không chứng minh chữ ký hoặc nguồn gốc pháp lý.

| Chế độ | Tài liệu | Bằng chứng và mục đích |
|---|---|---|
| `REAL_EXECUTED_RESTRICTED` | HDLD010–013 (4) | Bản lưu cục bộ có SHA-256 và vùng PII được khoanh trong `T1_privacy_gold_v01`; không yêu cầu URL công khai hoặc giấy phép phân phối mở. |
| `PUBLIC_TEMPLATE_VERIFIED` | HDLD005–009 (5) | Biểu mẫu công khai; HDLD005–006 là `GRANULARITY_ABLATION_PAIR` cùng họ mẫu, dùng để khảo sát độ mịn tách đoạn. |
| `SYNTHETIC_CALIBRATION_CONTROL` | HDLD014 (1) | Đối chứng tổng hợp 10 điều khoản, 7 trường cần giữ và 0 PII thật; không được gọi là hợp đồng thực đã ký. |

Cổng trả `10/10 ACCEPTED_UNDER_EQUIVALENT_GATE_V1` khi đủ ba chế độ, 10 tài liệu, phiên bản Gold và manifest được ghim. Không dùng HDLD014 để làm tăng cỡ mẫu thực hoặc để huấn luyện/tune. Báo cáo luôn tách ba lát cắt: `slice_unique_8` = HDLD005, 007–013 (8 tài liệu không trùng họ mẫu); `slice_t1_real_9` = HDLD005–013 (9 tài liệu, 747 span toàn văn và 340 điều khoản thực `[GENUINE_CLAUSE]`); `slice_composite_10` = HDLD005–014 (10 tài liệu gồm đối chứng tổng hợp). Điểm của ba lát cắt phải được ghi riêng với cỡ mẫu, CI bootstrap và giới hạn suy rộng; không gộp điểm tổng hợp thành điểm của 10 hợp đồng thực.

Quy tắc:

1. T1 gồm 10 tài liệu theo cổng tương đương, trong đó chỉ 9 tài liệu thuộc lát cắt thực/mẫu và 8 tài liệu thuộc lát cắt không trùng họ mẫu; khi đổi thành phần phải version lại cổng, Gold và báo cáo.

2. Chèn lỗi đổi văn bản, ranh giới và nhãn, nên T1 và T2 không dùng chung một bộ gold; gold segmentation của T2 được sửa lại sau khi chèn.

3. Gold segmentation: người sửa tay ranh giới điều khoản, không cần chuyên môn pháp lý.

4. Gold clause taxonomy và risk taxonomy: một LLM khác họ với LLM trong pipeline (Claude) gán trước; toàn bộ item của T1 được một thành viên xác minh độc lập theo annotation guideline và văn bản luật trong kho; chỗ bất đồng thì thảo luận và chốt. Ít nhất 20% item do hai thành viên gán độc lập để đo Cohen's kappa.

5. Clause taxonomy, risk taxonomy, severity rubric và annotation guideline phải đóng băng trước khi gán nhãn T1 (mốc MS-1). Đổi sau đó làm mất giá trị mọi số đo. Model id và phiên bản prompt được ghi lại nhưng không đóng băng.

6. Một điều khoản có thể có nhiều nhãn khác nhau.

7. Không chỉnh hệ thống dựa trên kết quả T1 và T2. Mọi chỉnh sửa làm trên D1 và D2.
