<!-- nguồn: T1_EQUIVALENT_GATE_EVALUATION_GUIDE.md | mục: Hướng dẫn cổng T1 tương đương và đọc kết quả đánh giá > 2. Ba lát cắt bắt buộc trong báo cáo T1 | 890 ký tự | trước: 01_1-quyet-dinh-can-nho.md | sau: 03_3-doc-dung-cac-chi-so.md -->

## 2. Ba lát cắt bắt buộc trong báo cáo T1

| Tên lát cắt | Thành phần | Mục đích | Phạm vi nhãn M7 |
|---|---|---|---|
| `slice_unique_8` | HDLD005, HDLD007–013 | Loại một thành viên của cặp mẫu gần trùng để thấy độ nhạy theo họ nguồn | Báo cỡ mẫu và CI riêng; không thay thế điểm T1 real 9. |
| `slice_t1_real_9` | HDLD005–013 | Điểm trên chín tài liệu thực/mẫu không tổng hợp | 747 span toàn văn và 340 dòng `[GENUINE_CLAUSE]` được báo song song. |
| `slice_composite_10` | HDLD005–014 | Xác nhận đủ 10 tài liệu của cổng tương đương, có đối chứng tổng hợp | Báo riêng đóng góp của HDLD014; không gọi là điểm mười hợp đồng thật. |

T2 hiện dùng 9 tài liệu HDLD005–013 sau khi chèn lỗi, gồm 872 span và 30 ca lỗi chèn. HDLD014 không có bản T2 trong Gold hiện hành. Mọi điểm phải kèm số đơn vị so khớp, phiên bản Gold/corpus/graph, hash đầu vào, cấu hình dự đoán, số lượt bootstrap và seed.
