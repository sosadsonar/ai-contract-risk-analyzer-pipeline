<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_v0.6.md | mục: BRD: AI Labor Contract Risk Analyzer > 8. Đo lường chất lượng và nghiệm thu > 8.4 Đánh giá false negative bằng lỗi chèn | 1315 ký tự | trước: 11_8-3-cac-chi-so.md | sau: 13_8-5-llm-as-a-judge-va-m6.md -->

### 8.4 Đánh giá false negative bằng lỗi chèn

Mục tiêu là ước lượng hệ thống bỏ sót bao nhiêu rủi ro mà không cần luật sư và không dùng judge.

1. Chọn các quy định trong kho luật có ngưỡng hoặc cấm đoán rõ ràng, mà người đọc văn bản luật tự kiểm chứng được. Ví dụ: lương thử việc thấp hơn mức luật cho phép, thời gian thử việc vượt mức tối đa, phạt tiền người lao động.

2. Mỗi quy định tạo ít nhất một điều khoản vi phạm, gắn với nhãn (risk taxonomy), một điều luật gold và vai trò chịu rủi ro. Tối thiểu 30 lỗi chèn cho T2, mỗi vai trò tối thiểu 10. D2 có bộ lỗi chèn riêng.

3. Hai thành viên xác minh từng lỗi chèn với văn bản luật trước khi dùng.

4. Chèn vào hợp đồng sạch (không chứa lỗi tương ứng), ở các vị trí khác nhau.

5. M5 = số lỗi chèn bị phát hiện đúng (đúng điều khoản, đúng vai trò, đúng nhãn) / tổng số lỗi chèn. Khớp tự động. Lỗi chèn bị gắn "chưa đủ căn cứ" vẫn tính là phát hiện nếu khớp; báo riêng tỷ lệ thiếu citation.

Với 30 lỗi chèn, ngưỡng 90% cho phép sót tối đa 3. Giới hạn: lỗi tự chèn rõ ràng hơn rủi ro thực tế và chỉ bao phủ các quy định có ngưỡng rõ. M5 là recall trên rủi ro có căn cứ rõ, không phải tỷ lệ bỏ sót trên mọi rủi ro.

Judge không tham gia tính M5. Có thể dùng judge để gợi ý các điều khoản nghi bị bỏ sót cho người rà soát, nhưng kết quả đó không tính vào chỉ số.
