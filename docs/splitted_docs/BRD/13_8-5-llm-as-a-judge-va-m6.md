<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_v0.6.md | mục: BRD: AI Labor Contract Risk Analyzer > 8. Đo lường chất lượng và nghiệm thu > 8.5 LLM-as-a-judge và M6 | 1089 ký tự | trước: 12_8-4-danh-gia-false-negative-bang-loi-chen.md | sau: 14_8-6-tieu-chi-nghiem-thu.md -->

### 8.5 LLM-as-a-judge và M6

Judge dùng để chấm hai việc trên các bản ghi rủi ro của T1: giải thích có đúng theo căn cứ và đúng vai trò không, và citation có liên quan không. Judge không chấm recall.

* Model: Claude. chỉ nhận dữ liệu đã che hoặc đã de-identify của bộ test, kèm điều khoản và điều luật trong kho làm bằng chứng.

* Hiệu chuẩn: lấy 40 output; hai thành viên chấm độc lập theo ba mức Đúng, Đúng một phần, Sai, rồi thảo luận chốt nhãn. Cho judge chấm đúng 40 output đó. Tính tỷ lệ judge trùng nhãn đã chốt (32/40 là 80%) và Cohen's kappa; báo thêm kappa giữa hai người chấm.

* Quyết định: đạt cả hai ngưỡng ở M6 thì tin judge cho phần còn lại của T1. Không đạt thì không báo số của judge; chấm tay một mẫu nhỏ hơn và nêu rõ cỡ mẫu. Với 40 mẫu, tỷ lệ trùng 80% có khoảng tin cậy 95% rộng (xấp xỉ ±12 điểm phần trăm), nên phải báo kèm khoảng tin cậy.

* M6 đo độ tin cậy của judge, không phải độ chính xác của hệ thống. Độ chính xác của hệ thống là tỷ lệ output được chấm Đúng trên cả tập.

* Chi phí judge nằm trong ngân sách đánh giá (§6). Chọn model Claude cụ thể ở OI-11.
