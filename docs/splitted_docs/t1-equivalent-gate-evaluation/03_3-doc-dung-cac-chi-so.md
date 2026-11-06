<!-- nguồn: T1_EQUIVALENT_GATE_EVALUATION_GUIDE.md | mục: Hướng dẫn cổng T1 tương đương và đọc kết quả đánh giá > 3. Đọc đúng các chỉ số | 1573 ký tự | trước: 02_2-ba-lat-cat-bat-buoc-trong-bao-cao-t1.md | sau: 04_4-trang-thai-diem-ky-thuat-da-co.md -->

## 3. Đọc đúng các chỉ số

- **M1:** F1 phân đoạn theo span, IoU tối thiểu 0.80. Điểm M1 không suy ra từ kiểm tra offset đúng của CSV.
- **M2:** macro-F1 rủi ro theo bộ ba điều khoản, vai trò và nhãn. Chỉ có điểm khi có Gold T1 tương ứng và dự đoán độc lập.
- **M3a:** citation có trong tập ứng viên, corpus và đúng hiệu lực. M3a 100% không chứng minh citation liên quan với rủi ro; M3b cần người chấm.
- **M4:** câu trích rủi ro phải là chuỗi con nguyên văn với offset đúng. Nếu không có đầu ra rủi ro, M4 là *không ước lượng được*, không phải 100%. Chỉ số privacy §7.3 được báo riêng.
- **M5:** recall trên 30 lỗi chèn T2, khớp span, vai trò và nhãn. Lỗi không phát hiện vẫn nằm trong mẫu số.
- **M7:** macro-F1 trên cả 747 span và 340 điều khoản thực của T1 real 9. Ghi rõ nếu baseline gán nhãn trên span tham chiếu; kết quả ấy chưa phải điểm end-to-end sau căn chỉnh dự đoán span với Gold.
- **M8:** Recall@5 trên 30 ca T2, đo cả bật và tắt mở rộng Data Graph cùng một tập ca và cùng `final_k`.
- **Privacy §7.3:** báo recall PII nhạy cảm cao, PII còn lại và tỷ lệ giữ trường trên Gold D1/T1. T2 privacy hiện có tham chiếu suy ra từ T1 và lỗi chèn nên chỉ là chẩn đoán, chưa có Gold T2 phân xử độc lập.

M3b và M6 cần mẫu chấm tay/hiệu chuẩn riêng. D3, P1, M2b, M9 và M10 là nhánh mở rộng giai đoạn 2 khi có Gold/gói đánh giá tương ứng. Chưa chạy phải ghi `NOT_RUN` hoặc trạng thái tương đương; không suy diễn là đạt. Quy tắc căn chỉnh IoU 0.5 trong BRD 0.6 dùng cho lần đánh giá mới có span dự đoán khác Gold, không sửa lại cách tính của báo cáo baseline đã phát hành.
