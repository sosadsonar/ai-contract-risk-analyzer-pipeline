<!-- nguồn: T1_EQUIVALENT_GATE_EVALUATION_GUIDE.md | mục: Hướng dẫn cổng T1 tương đương và đọc kết quả đánh giá > 5. Quy trình khi cập nhật dữ liệu hoặc đánh giá | 774 ký tự | trước: 04_4-trang-thai-diem-ky-thuat-da-co.md | sau: 06_6-gioi-han-trach-nhiem.md -->

## 5. Quy trình khi cập nhật dữ liệu hoặc đánh giá

1. Chốt ID tài liệu và chế độ nguồn trong metadata; kiểm hash và trạng thái Gold trước khi chạy. Giữ văn bản gốc/PII trong vùng cục bộ hạn chế truy cập.
2. Đóng băng cấu hình dự đoán từ Dev D1/D2 trước khi nạp nhãn T1/T2. Ghi các phiên bản và hash vào kết quả.
3. Xuất ba lát cắt T1 và T2 riêng; với M7, luôn xuất hai phạm vi 747/340 của T1 real 9. Dùng bootstrap 95% CI với 1.000 lượt, seed 0 cho biên nhận tương ứng.
4. Đối chiếu từng điểm với ngưỡng BRD; ghi `PASS`, `FAIL`, `NOT_RUN` hoặc `NOT_ESTIMABLE` cùng lý do. Không chuyển kết quả chẩn đoán thành nghiệm thu.
5. Khi thay đổi Gold, thành phần T1, quy tắc căn chỉnh hoặc mô hình, tạo phiên bản báo cáo mới. Không ghi đè biên nhận cũ và không tune trên điểm T1/T2.
