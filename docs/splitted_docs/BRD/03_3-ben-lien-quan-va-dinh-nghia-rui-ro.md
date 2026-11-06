<!-- nguồn: BRD_AI_Labor_Contract_Risk_Analyzer_v0.6.md | mục: BRD: AI Labor Contract Risk Analyzer > 3. Bên liên quan và định nghĩa rủi ro | 5901 ký tự | trước: 02_2-pham-vi.md | sau: 04_4-quy-trinh-nguoi-dung.md -->

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

Một điều khoản là rủi ro đối với một vai trò khi thuộc một trong ba loại. Phân tích giả định điều khoản có hiệu lực (như thể hợp đồng đã được ký) để thấy tác hại của nó.

- Trái luật (LEGAL_VIOLATION): xung đột quy định cấm hoặc bắt buộc, hoặc vượt ngưỡng pháp luật rõ ràng có trong kho luật. Điều khoản hạ quyền lợi của NLĐ xuống dưới mức pháp luật bảo vệ thuộc loại này, không thuộc UNFAVORABLE.
- Bất lợi hợp pháp (UNFAVORABLE): hợp pháp, không thấp hơn mức sàn của pháp luật, nhưng gây bất lợi đáng kể cho vai trò đó, theo một trong các dấu hiệu sau.
  - Với NLĐ: (N1) giá trị định lượng nằm đúng tại cận pháp luật bất lợi cho NLĐ (ví dụ 48 giờ mỗi tuần, thử việc ở mức tối đa, hợp đồng 36 tháng); (N2) NSDLĐ được quyền đơn phương hoặc quyền quyết định rộng mà không có điều kiện, giới hạn, thời hạn báo trước hay bù đắp (điều chuyển, đổi ca, đổi địa điểm); (N3) chuyển chi phí hoặc rủi ro sang NLĐ trong biên pháp luật cho phép nhưng phạm vi rộng (không cạnh tranh, bảo mật, hoàn trả chi phí đào tạo, bồi thường).
  - Với NSDLĐ: (E1) NSDLĐ mất hoặc bị hạn chế quyền mà pháp luật cho, hoặc mất bảo vệ về quy trình (ví dụ NLĐ chỉ phải báo trước rất ngắn); (E2) trách nhiệm không có mức trần hoặc một chiều đè lên NSDLĐ; (E3) cam kết tài chính hoặc phúc lợi cố định, dài hạn hoặc không kỳ hạn, không điều kiện, không gắn kết quả, không có cơ chế điều chỉnh (ví dụ không giảm lương trong 5 năm). Việc NSDLĐ chọn trả cao hơn mức tối thiểu trong thời hạn ngắn (ví dụ lương thử việc 100%) không phải rủi ro.
- Mơ hồ (AMBIGUOUS): thiếu số liệu hoặc điều kiện đáng lẽ phải có (ví dụ cam kết "tăng lương hằng năm" không nêu căn cứ, tiêu chí hay mức), hoặc hai điều khoản trong cùng hợp đồng nói khác nhau.

Điều khoản có lợi hơn mức pháp luật yêu cầu cho một bên không phải rủi ro của bên đó. Cùng một điều khoản có thể không là rủi ro với bên này, hoặc là rủi ro với cả hai bên nhưng khác loại, khác mức độ và khác giải thích. Mức độ nghiêm trọng (HIGH, MEDIUM, LOW) tra theo bảng trong risk taxonomy (nhãn, loại căn cứ, vai trò); rubric ở SRS 2.3 chỉ để đọc. Mọi loại căn cứ đều được kỳ vọng có điều luật liên quan; khi kho luật không đủ căn cứ thì áp dụng BR-15. Danh sách nhãn rủi ro và bảng mức độ nằm ở tài liệu risk taxonomy (docs/RISK_TAXONOMY_v0.1.md); định nghĩa chi tiết và ví dụ neo nằm ở annotation guideline.

### 3.3 Sáu điều khoản mẫu theo vai trò

Bảng dưới minh họa cách hai vai trò cho kết quả khác nhau trên cùng một điều khoản. Đây là ca nghiệm thu BO-3 (§8.6). Kết quả kỳ vọng chỉ mang tính minh họa; người phụ trách dữ liệu phải xác minh lại với văn bản luật gốc trong kho trước khi đưa vào bộ test.

| STT | Điều khoản mẫu | Căn cứ (Bộ luật Lao động 2019) | Với NLĐ | Với NSDLĐ |
|---|---|---|---|---|
| 1 | "Mỗi lần đi làm muộn, NLĐ bị phạt 100.000 đồng, trừ trực tiếp vào lương tháng." | Điều 127: cấm phạt tiền, cắt lương thay việc xử lý kỷ luật | Trái luật (PENALTY_DEDUCTION_DAMAGES), HIGH: lương bị trừ không có căn cứ | Trái luật (PENALTY_DEDUCTION_DAMAGES), HIGH: vi phạm điều cấm, có nguy cơ bị xử phạt |
| 2 | "Lương thử việc bằng 70% mức lương chính thức." | Điều 26: ít nhất 85% mức lương của công việc đó | Trái luật (PROBATION), HIGH: bị trả thấp hơn mức tối thiểu | Trái luật (PROBATION), HIGH: có nguy cơ bị xử phạt |
| 3 | "NLĐ giao bản chính bằng tốt nghiệp để công ty giữ trong suốt thời gian làm việc." | Điều 17 khoản 1: cấm giữ bản chính giấy tờ tùy thân, văn bằng, chứng chỉ | Trái luật (DEPOSIT_DOCUMENT_HELD), HIGH: mất quyền kiểm soát giấy tờ, bị ràng buộc khi muốn nghỉ việc | Trái luật (DEPOSIT_DOCUMENT_HELD), HIGH: vi phạm điều cấm |
| 4 | "Hợp đồng 24 tháng; NLĐ chỉ cần báo trước 3 ngày làm việc khi nghỉ việc." | Điều 35 khoản 1 điểm b: báo trước ít nhất 30 ngày với hợp đồng từ 12 đến 36 tháng | Không rủi ro: điều khoản có lợi hơn mức pháp luật yêu cầu cho NLĐ | Bất lợi hợp pháp (TERMINATION_GROUNDS_NOTICE), MEDIUM: NSDLĐ mất bảo vệ báo trước 30 ngày, khó chủ động nhân sự |
| 5 | "Lương thử việc bằng 100% mức lương chính thức." | Điều 26: ít nhất 85% mức lương của công việc đó | Không rủi ro | Không rủi ro pháp lý: cao hơn mức tối thiểu hợp pháp |
| 6 | "Thời giờ làm việc bình thường là 48 giờ mỗi tuần." | Điều 105: không quá 08 giờ mỗi ngày và 48 giờ mỗi tuần | Bất lợi hợp pháp (WORKING_HOURS_OVERTIME), MEDIUM: ở mức trần pháp luật cho phép | Không rủi ro |

Ca 4 và ca 6: kết quả kỳ vọng cần được người phụ trách dữ liệu xác minh với Điều 35, Điều 49 và Điều 105 trước khi vào bộ test; không xác minh được thì loại khỏi nghiệm thu BO-3.

*\* Nguồn đối chiếu: trang [Doanh nghiệp có được phạt tiền nhân viên không?](https://thuvienphapluat.vn/lao-dong-tien-luong/doanh-nghiep-co-duoc-phat-tien-nhan-vien-khong-63945.html) cho Điều 124 và Điều 127. Điều 25 và 26 ([CareerLink](https://www.careerlink.vn/cam-nang-viec-lam/luat-lao-dong/luong-thu-viec-toi-thieu-bao-nhieu-phan-tram)), Điều 17 ([Thư Viện Pháp Luật](https://thuvienphapluat.vn/hoi-dap-phap-luat/dang-thu-viec-cong-ty-co-duoc-giu-cmnd-ban-goc-khong-357958.html)), Điều 35 ([LuatVietnam](https://luatvietnam.vn/tin-tuc-doanh-nghiep/co-phai-nguoi-lao-dong-duoc-don-phuong-cham-dut-hop-dong-khong-can-ly-do-2767-85777-legal.html)).*
