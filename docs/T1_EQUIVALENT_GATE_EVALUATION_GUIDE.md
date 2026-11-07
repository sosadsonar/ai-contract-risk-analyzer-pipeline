# Hướng dẫn cổng T1 tương đương và đọc kết quả đánh giá

**Phiên bản:** 1.0 · **Ngày:** 06/11/2026 · **Phạm vi:** BRD 0.6 §7.3, §8.2–8.3 và đánh giá kỹ thuật Data Lead.
**Quyết định nhóm:** `DucAnh_N2` (Owner/Annotator), `argon` (Reviewer), `Minh_N1` (Adjudicator).
**Tài liệu nguồn:** `docs/BRD_AI_Labor_Contract_Risk_Analyzer_v0.6.md`; biên nhận và ADR kỹ thuật ở repo Data.

## 1. Quyết định cần nhớ

`D1 = HDLD001–004`, gồm 4 hợp đồng và 183 điều khoản đã REVIEWED. HDLD005 thuộc T1 trong mọi bước: không đưa vào few-shot, train hay tuning Dev. D2 gồm 4 tài liệu Dev HDLD001–004, 236 span phân đoạn và 30 lỗi chèn riêng (8 + 8 + 7 + 7). T2 mới gồm 9 tài liệu HDLD005–013, 872 span và 30 lỗi chèn. Không sử dụng Gold T1/T2 làm đầu vào dự đoán hoặc để điều chỉnh mô hình.

T1 được tiếp nhận theo `T1_EQUIVALENT_GATE_V1`, gồm 10 **tài liệu**, không phải 10 hợp đồng đã ký độc lập. Đây là quyết định nghiệm thu nội bộ của nhóm để có một tập đánh giá khả dụng trong điều kiện dữ liệu hợp đồng đã ký chứa PII cần hạn chế truy cập. Kết quả phải công bố cấu trúc mẫu và giới hạn của nó; không suy ra quyền công bố dữ liệu từ việc cổng đã đạt.

| Nhóm | ID | Số lượng | Cách xác minh và cách dùng |
|---|---|---:|---|
| `REAL_EXECUTED_RESTRICTED` | HDLD010–013 | 4 | File lưu cục bộ có SHA-256 và Gold privacy khoanh vùng PII. Không đẩy văn bản gốc hoặc Gold chứa nội dung nhạy cảm lên Git công khai. Hash chứng minh danh tính byte của bản lưu, không chứng minh giấy phép, chữ ký hay quyền xử lý dữ liệu. |
| `PUBLIC_TEMPLATE_VERIFIED` | HDLD005–009 | 5 | Mẫu công khai; HDLD005 và HDLD006 cùng họ mẫu, được ghi là cặp đối chứng độ mịn phân đoạn. HDLD007 là phép thử dẫn chiếu ngoài corpus hiện có. |
| `SYNTHETIC_CALIBRATION_CONTROL` | HDLD014 | 1 | Đối chứng tổng hợp 10 điều khoản, 7 trường cần giữ, 0 PII thật. Chỉ dùng để hiệu chuẩn kỹ thuật; không trình bày như hợp đồng thật. |

## 2. Ba lát cắt bắt buộc trong báo cáo T1

| Tên lát cắt | Thành phần | Mục đích | Phạm vi nhãn M7 |
|---|---|---|---|
| `slice_unique_8` | HDLD005, HDLD007–013 | Loại một thành viên của cặp mẫu gần trùng để thấy độ nhạy theo họ nguồn | Báo cỡ mẫu và CI riêng; không thay thế điểm T1 real 9. |
| `slice_t1_real_9` | HDLD005–013 | Điểm trên chín tài liệu thực/mẫu không tổng hợp | 747 span toàn văn và 340 dòng `[GENUINE_CLAUSE]` được báo song song. |
| `slice_composite_10` | HDLD005–014 | Xác nhận đủ 10 tài liệu của cổng tương đương, có đối chứng tổng hợp | Báo riêng đóng góp của HDLD014; không gọi là điểm mười hợp đồng thật. |

T2 hiện dùng 9 tài liệu HDLD005–013 sau khi chèn lỗi, gồm 872 span và 30 ca lỗi chèn. HDLD014 không có bản T2 trong Gold hiện hành. Mọi điểm phải kèm số đơn vị so khớp, phiên bản Gold/corpus/graph, hash đầu vào, cấu hình dự đoán, số lượt bootstrap và seed.

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

## 4. Trạng thái điểm kỹ thuật đã có

Biên nhận đánh giá trước khi chỉnh tài liệu: Pipeline commit `440a3cd`, Data commit `1bf817d`. Báo cáo nằm ở `reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/result.json` và `acceptance_readout.md` trên nhánh Data Lead; PR tài liệu này chưa mang các file đó. T1 real 9: M1 0.3713, M7 0.3377 trên 747 span và 0.5442 trên 340 điều khoản thực. T2: M5 12/30; M8 graph-off 15/30 và graph-on 14/30. M4 T1 chưa ước lượng được vì baseline không phát ra rủi ro; M4 T2 đúng 19/19 đầu ra đã phát. M2, M3b và M6 chưa có điểm hợp lệ trong báo cáo này. Do đó cổng dữ liệu tương đương 10/10 **không đồng nghĩa** các chỉ số chất lượng đã đạt ngưỡng.

## 5. Quy trình khi cập nhật dữ liệu hoặc đánh giá

1. Chốt ID tài liệu và chế độ nguồn trong metadata; kiểm hash và trạng thái Gold trước khi chạy. Giữ văn bản gốc/PII trong vùng cục bộ hạn chế truy cập.
2. Đóng băng cấu hình dự đoán từ Dev D1/D2 trước khi nạp nhãn T1/T2. Ghi các phiên bản và hash vào kết quả.
3. Xuất ba lát cắt T1 và T2 riêng; với M7, luôn xuất hai phạm vi 747/340 của T1 real 9. Dùng bootstrap 95% CI với 1.000 lượt, seed 0 cho biên nhận tương ứng.
4. Đối chiếu từng điểm với ngưỡng BRD; ghi `PASS`, `FAIL`, `NOT_RUN` hoặc `NOT_ESTIMABLE` cùng lý do. Không chuyển kết quả chẩn đoán thành nghiệm thu.
5. Khi thay đổi Gold, thành phần T1, quy tắc căn chỉnh hoặc mô hình, tạo phiên bản báo cáo mới. Không ghi đè biên nhận cũ và không tune trên điểm T1/T2.

## 6. Giới hạn trách nhiệm

Quyết định `T1_EQUIVALENT_GATE_V1` là thay thế học thuật do nhóm dự án phê duyệt. Việc chỉ giữ hash và Gold privacy không xác minh độc lập sự đồng ý, quyền phân phối hay thẩm quyền của bên kiểm soát dữ liệu. Các nhận định pháp lý từ tập luật hữu hạn và Gold do nhóm sinh/duyệt phải được mô tả đúng phạm vi đó trong báo cáo cuối.
