<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_0_5.md | mục: BRD: AI Labor Contract Risk Analyzer > 8. Đo lường chất lượng và nghiệm thu | 7943 ký tự | trước: 07_7-du-lieu-ca-nhan-va-bao-mat.md | sau: 09_9-rang-buoc-gia-dinh-phu-thuoc.md -->

## 8. Đo lường chất lượng và nghiệm thu

Đây là nguồn duy nhất cho mọi chỉ số chất lượng. SRS chỉ dẫn ID ở đây, không lặp số.

### 8.1 Nguyên tắc và giới hạn

Nhóm không có luật sư và nhãn gold hiện có do LLM tạo. Vì vậy:

* Tầng nào kiểm tra tự động được bằng quy tắc xác định thì kiểm tự động, không dùng LLM.

* Mọi con số báo cáo phải kèm nguồn nhãn gold (người sửa, LLM gán rồi người xác minh, lỗi chèn) và kích thước tập test.

* LLM-as-a-judge chỉ dùng khi có bằng chứng trong tay (văn bản hợp đồng đã che, điều luật trong kho) và phải được hiệu chuẩn bằng người trước khi tin kết quả (M6). Judge không được dùng để quyết định false negative và không tham gia tính M5.

* Gold của taxonomy là sự đồng thuận của nhóm không có chuyên môn pháp lý, không phải chân lý pháp lý. Báo cáo phải nói rõ điều này.

Ngoài phạm vi: không đo false positive riêng. Precision nằm trong F1 của M1, M2 và M7.

### 8.2 Dữ liệu đánh giá

| Tập | Nội dung | Dùng cho |
|---|---|---|
| D1 | 4 hợp đồng dev hiện có (183 điều khoản) | Phát triển, tuning prompt, few-shot; không báo số nghiệm thu |
| D2 | D1 kèm lỗi chèn riêng cho dev, câu chữ và quy định không dùng chung với T2 (tốt nhất tách quy định) | Phát triển |
| T1 | Tối thiểu 10 hợp đồng gốc, tách hoàn toàn khỏi dữ liệu dev, few-shot, prompt; đa dạng định dạng (PDF, DOCX), kiểu đánh số điều khoản, ngành và độ dài | M1, M2, M3a, M3b, M4, M6, M7, BL-1 |
| T2 | Bản sao T1 đã chèn tối thiểu 30 lỗi (8.4) | M5, M8 |

Quy tắc:

1. Số hợp đồng của T1 hiện là 10 và có thể đổi sau; khi đổi, xem lại ngưỡng và cỡ mẫu.

2. Chèn lỗi đổi văn bản, ranh giới và nhãn, nên T1 và T2 không dùng chung một bộ gold; gold segmentation của T2 được sửa lại sau khi chèn.

3. Gold segmentation: người sửa tay ranh giới điều khoản, không cần chuyên môn pháp lý.

4. Gold clause taxonomy và risk taxonomy: một LLM khác họ với LLM trong pipeline (Claude) gán trước; toàn bộ item của T1 được một thành viên xác minh độc lập theo annotation guideline và văn bản luật trong kho; chỗ bất đồng thì thảo luận và chốt. Ít nhất 20% item do hai thành viên gán độc lập để đo Cohen's kappa.

5. Clause taxonomy, risk taxonomy, severity rubric và annotation guideline phải đóng băng trước khi gán nhãn T1 (mốc MS-1). Đổi sau đó làm mất giá trị mọi số đo. Model id và phiên bản prompt được ghi lại nhưng không đóng băng.

6. Một điều khoản có thể có nhiều nhãn khác nhau.

7. Không chỉnh hệ thống dựa trên kết quả T1 và T2. Mọi chỉnh sửa làm trên D1 và D2.

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
| M7 | Clause classification macro-F1 | ≥ 0.80 | Cặp (điều khoản, clause label) | LLM khác họ gán, người xác minh | T1 | Tự động; báo per-class; macro chỉ tính nhãn có ≥ 5 mẫu |
| M8 | Retrieval recall@5 | ≥ 90% | Mỗi lỗi chèn | Điều luật gold của lỗi chèn | T2 | Tự động: điều luật gold nằm trong 5 candidate đầu. Chỉ số chẩn đoán. Báo thêm recall@5 khi tắt mở rộng qua Data Graph để thấy đóng góp của Graph (BR-17); không có ngưỡng riêng |
| BL-1 | So với LLM thông dụng | Tỷ lệ citation sai của hệ thống ≤ một nửa của baseline | Mỗi điều luật được trích | Người đối chiếu văn bản luật thật | T1 (cùng mẫu 40) | "Sai" = không tồn tại hoặc nội dung không khớp. Cùng hợp đồng đã che, cùng vai trò, cùng yêu cầu. Baseline: LLM thông dụng chọn ở OI-07, cấu hình cụ thể ghi trong báo cáo. |

\* Ngưỡng M2, M7 và M3b được đặt lại sau số đo dev đầu tiên (OI-09). Mọi con số báo kèm khoảng tin cậy (bootstrap) và số mẫu mỗi nhãn.

### 8.4 Đánh giá false negative bằng lỗi chèn

Mục tiêu là ước lượng hệ thống bỏ sót bao nhiêu rủi ro mà không cần luật sư và không dùng judge.

1. Chọn các quy định trong kho luật có ngưỡng hoặc cấm đoán rõ ràng, mà người đọc văn bản luật tự kiểm chứng được. Ví dụ: lương thử việc thấp hơn mức luật cho phép, thời gian thử việc vượt mức tối đa, phạt tiền người lao động.

2. Mỗi quy định tạo ít nhất một điều khoản vi phạm, gắn với nhãn (risk taxonomy), một điều luật gold và vai trò chịu rủi ro. Tối thiểu 30 lỗi chèn cho T2, mỗi vai trò tối thiểu 10. D2 có bộ lỗi chèn riêng.

3. Hai thành viên xác minh từng lỗi chèn với văn bản luật trước khi dùng.

4. Chèn vào hợp đồng sạch (không chứa lỗi tương ứng), ở các vị trí khác nhau.

5. M5 = số lỗi chèn bị phát hiện đúng (đúng điều khoản, đúng vai trò, đúng nhãn) / tổng số lỗi chèn. Khớp tự động. Lỗi chèn bị gắn "chưa đủ căn cứ" vẫn tính là phát hiện nếu khớp; báo riêng tỷ lệ thiếu citation.

Với 30 lỗi chèn, ngưỡng 90% cho phép sót tối đa 3. Giới hạn: lỗi tự chèn rõ ràng hơn rủi ro thực tế và chỉ bao phủ các quy định có ngưỡng rõ. M5 là recall trên rủi ro có căn cứ rõ, không phải tỷ lệ bỏ sót trên mọi rủi ro.

Judge không tham gia tính M5. Có thể dùng judge để gợi ý các điều khoản nghi bị bỏ sót cho người rà soát, nhưng kết quả đó không tính vào chỉ số.

### 8.5 LLM-as-a-judge và M6

Judge dùng để chấm hai việc trên các bản ghi rủi ro của T1: giải thích có đúng theo căn cứ và đúng vai trò không, và citation có liên quan không. Judge không chấm recall.

* Model: Claude. chỉ nhận dữ liệu đã che hoặc đã de-identify của bộ test, kèm điều khoản và điều luật trong kho làm bằng chứng.

* Hiệu chuẩn: lấy 40 output; hai thành viên chấm độc lập theo ba mức Đúng, Đúng một phần, Sai, rồi thảo luận chốt nhãn. Cho judge chấm đúng 40 output đó. Tính tỷ lệ judge trùng nhãn đã chốt (32/40 là 80%) và Cohen's kappa; báo thêm kappa giữa hai người chấm.

* Quyết định: đạt cả hai ngưỡng ở M6 thì tin judge cho phần còn lại của T1. Không đạt thì không báo số của judge; chấm tay một mẫu nhỏ hơn và nêu rõ cỡ mẫu. Với 40 mẫu, tỷ lệ trùng 80% có khoảng tin cậy 95% rộng (xấp xỉ ±12 điểm phần trăm), nên phải báo kèm khoảng tin cậy.

* M6 đo độ tin cậy của judge, không phải độ chính xác của hệ thống. Độ chính xác của hệ thống là tỷ lệ output được chấm Đúng trên cả tập.

* Chi phí judge nằm trong ngân sách đánh giá (§6). Chọn model Claude cụ thể ở OI-11.

### 8.6 Tiêu chí nghiệm thu

* Luồng chính chạy trọn vẹn cho cả hai vai trò trên toàn bộ T1: mỗi hợp đồng đạt trạng thái hoàn thành sau tối đa 2 lần thử lại thủ công mỗi phiên.

* BO-3: năm ca mẫu ở §3.3 cho kết quả khác nhau giữa hai vai trò đúng như kỳ vọng đã được người phụ trách dữ liệu xác minh (đạt hoặc không đạt, không tính tỷ lệ).

* Đạt các ngưỡng M1 đến M8 và ngưỡng ở §7.3, hoặc có giải trình nếu chưa đạt. BL-1 nếu chưa bị cắt theo §9.5.

* Mọi yêu cầu BR-01 đến BR-16 được kiểm tra và có kết quả.

* Báo cáo đánh giá nêu rõ phương pháp, nguồn gold, cỡ tập và giới hạn của phép đo.

* Không chỉnh hệ thống dựa trên kết quả T1 và T2.
