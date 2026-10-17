<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_0_5.md | mục: BRD: AI Labor Contract Risk Analyzer > 3. Bên liên quan và định nghĩa rủi ro | 3743 ký tự | trước: 02_2-pham-vi.md | sau: 04_4-quy-trinh-nguoi-dung.md -->

## 3. Bên liên quan và định nghĩa rủi ro

### 3.1 Bên liên quan

| Bên liên quan | Vai trò | Mối quan tâm chính |
|---|---|---|
| Người lao động (NLĐ) | Người dùng cuối | Hợp đồng sắp ký có điều khoản nào bất lợi hoặc trái luật. |
| Người sử dụng lao động (NSDLĐ) | Người dùng cuối | Hợp đồng đã soạn có điều khoản nào trái luật hoặc dễ phát sinh tranh chấp, xử phạt. |
| Người phụ trách dữ liệu | Thành viên nhóm phát triển | Xây dựng và cập nhật kho luật. |
| Giảng viên hướng dẫn | Người yêu cầu và nghiệm thu | Yêu cầu có Data Graph và Clause Graph (BR-17, BR-18). |

\* Rủi ro phụ thuộc vai trò: hệ thống phải nêu đúng loại rủi ro theo góc nhìn của vai trò đã chọn, không dùng chung một danh sách cho cả hai bên.

### 3.2 Định nghĩa rủi ro

Một điều khoản là rủi ro đối với một vai trò khi thuộc một trong ba loại:

- Trái luật (LEGAL_VIOLATION): xung đột quy định cấm hoặc bắt buộc, hoặc vượt ngưỡng pháp luật rõ ràng có trong kho luật.
- Bất lợi hợp pháp (UNFAVORABLE): không trái luật nhưng gây bất lợi đáng kể cho vai trò đó.
- Mơ hồ (AMBIGUOUS): câu chữ không rõ, có khả năng dẫn đến tranh chấp.

Điều khoản có lợi hơn mức pháp luật yêu cầu cho một bên không phải rủi ro của bên đó. Cùng một điều khoản có thể không là rủi ro với bên này, hoặc là rủi ro với cả hai bên nhưng khác loại, khác mức độ và khác giải thích. Mức độ nghiêm trọng (HIGH, MEDIUM, LOW) theo rubric ở SRS 2.3. Danh sách nhãn rủi ro thuộc risk taxonomy (BRD 8.2).

### 3.3 Năm điều khoản mẫu theo vai trò

Bảng dưới minh họa cách hai vai trò cho kết quả khác nhau trên cùng một điều khoản. Đây là ca nghiệm thu BO-3 (§8.6). Kết quả kỳ vọng chỉ mang tính minh họa; người phụ trách dữ liệu phải xác minh lại với văn bản luật gốc trong kho trước khi đưa vào bộ test.

| STT | Điều khoản mẫu | Căn cứ (Bộ luật Lao động 2019) | Với NLĐ | Với NSDLĐ |
|---|---|---|---|---|
| 1 | "Mỗi lần đi làm muộn, NLĐ bị phạt 100.000 đồng, trừ trực tiếp vào lương tháng." | Điều 127: cấm phạt tiền, cắt lương thay việc xử lý kỷ luật | Trái luật, HIGH: lương bị trừ không có căn cứ | Trái luật, HIGH: vi phạm điều cấm, có nguy cơ bị xử phạt |
| 2 | "Lương thử việc bằng 70% mức lương chính thức." | Điều 26: ít nhất 85% mức lương của công việc đó | Trái luật, HIGH: bị trả thấp hơn mức tối thiểu | Trái luật, HIGH: có nguy cơ bị xử phạt |
| 3 | "NLĐ giao bản chính bằng tốt nghiệp để công ty giữ trong suốt thời gian làm việc." | Điều 17 khoản 1: cấm giữ bản chính giấy tờ tùy thân, văn bằng, chứng chỉ | Trái luật, HIGH: mất quyền kiểm soát giấy tờ, bị ràng buộc khi muốn nghỉ việc | Trái luật, HIGH: vi phạm điều cấm |
| 4 | "Hợp đồng 24 tháng; NLĐ chỉ cần báo trước 3 ngày làm việc khi nghỉ việc." | Điều 35 khoản 1 điểm b: báo trước ít nhất 30 ngày với hợp đồng từ 12 đến 36 tháng | LOW: không bất lợi trực tiếp, nhưng điều khoản trái luật nên không đáng tin cậy làm căn cứ nghỉ sớm | Trái luật, HIGH: dễ phát sinh tranh chấp khi NLĐ nghỉ đột xuất |
| 5 | "Lương thử việc bằng 100% mức lương chính thức." | Điều 26: ít nhất 85% mức lương của công việc đó | Không rủi ro | Không rủi ro pháp lý: cao hơn mức tối thiểu hợp pháp |

*\* Nguồn đối chiếu: trang [Doanh nghiệp có được phạt tiền nhân viên không?](https://thuvienphapluat.vn/lao-dong-tien-luong/doanh-nghiep-co-duoc-phat-tien-nhan-vien-khong-63945.html) cho Điều 124 và Điều 127. Điều 25 và 26 ([CareerLink](https://www.careerlink.vn/cam-nang-viec-lam/luat-lao-dong/luong-thu-viec-toi-thieu-bao-nhieu-phan-tram)), Điều 17 ([Thư Viện Pháp Luật](https://thuvienphapluat.vn/hoi-dap-phap-luat/dang-thu-viec-cong-ty-co-duoc-giu-cmnd-ban-goc-khong-357958.html)), Điều 35 ([LuatVietnam](https://luatvietnam.vn/tin-tuc-doanh-nghiep/co-phai-nguoi-lao-dong-duoc-don-phuong-cham-dut-hop-dong-khong-can-ly-do-2767-85777-legal.html)).*
