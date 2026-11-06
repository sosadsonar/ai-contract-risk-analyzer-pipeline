<!-- nguồn: RISK_TAXONOMY_v0.1.md | mục: Risk Taxonomy - Contract Risk Analyzer > Cách đọc bảng | 775 ký tự | trước: 02_quy-trinh-gan-nhan-theo-vai-tro-cua-phien.md | sau: 04_xu-ly-khi-gap-o.md -->

## Cách đọc bảng

- `risk_id`: nhãn rủi ro.
- `Clause label tham khảo`: clause thường mang nhãn clause này (cross-reference). Chỉ để người đọc; không có trong code, không đưa vào prompt, không dùng để lọc hay giới hạn nhãn rủi ro. LLM tự phán đoán nhãn rủi ro.
- `Gom từ (expression)`: dấu hiệu trong clause dẫn đến nhãn này.
- `EMPLOYEE` / `EMPLOYER`: severity theo thứ tự `LV / UF / AM` của vai trò đó. `H` = HIGH, `M` = MEDIUM, `L` = LOW.
- `-`: tổ hợp đó KHÔNG phải rủi ro của vai trò này (ví dụ điều khoản có lợi hơn luật cho một bên thì không phải rủi ro của bên đó, BRD 3.2).
- `Căn cứ (candidate)`: điều luật có thể liên quan, chỉ là gợi ý. Căn cứ chính xác phải truy xuất trong corpus theo nội dung clause; LLM chỉ được trích citation nằm trong candidate của clause.
