# Clause Taxonomy v1 — Contract Risk Analyzer

Owner: Người 1 – Clause AI Lead
Trạng thái: v1 (chốt Tuần 1, có thể mở rộng nhãn ở Tuần 3–4 sau khi thấy dữ liệu thật)
Nguồn chân lý (source of truth) trong code: `ai_pipeline/config/thresholds.py` (`RISK_TAXONOMY_MAP`). File này là bản giải thích/lý do đi kèm — nếu hai bên lệch nhau, code là bản đúng, tài liệu này cần cập nhật theo.

## 1. Nguyên tắc thiết kế

- **Đa nhãn (multi-label):** một điều khoản có thể vừa là `COMPENSATION` vừa là `TERMINATION` (ví dụ: "nếu chấm dứt trước hạn, người lao động phải bồi hoàn chi phí đào tạo"). Không ép mỗi clause chỉ 1 nhãn.
- **Phân loại theo nội dung trước, rủi ro tính sau:** `clause_type` trả lời "điều khoản này nói về cái gì", còn `max_content_risk_tier` / `review_zone` (tính từ `compute_clause_routing`) trả lời "có cần con người xem lại không". Hai tầng này tách biệt để không lẫn lộn giữa nhãn nội dung và mức độ tin cậy của model.
- **8 nhãn ở v1, không cố phủ hết mọi trường hợp.** Nhãn `OTHER` là van an toàn cho các điều khoản không khớp 7 nhãn còn lại (hiệu lực hợp đồng, số bản hợp đồng, cam kết chung...), không dùng để "nhét bừa" các clause khó — nếu `OTHER` chiếm >15% dữ liệu ở lần review giữa kỳ, cần bổ sung nhãn mới.

## 2. Bảng nhãn v1

| Nhãn | Tier rủi ro | Định nghĩa | Ví dụ điển hình |
|---|---|---|---|
| `JOB_DUTIES` | BOILERPLATE | Chức danh, mô tả công việc, địa điểm làm việc, cấp trên trực tiếp | "Người lao động đảm nhận vị trí Lập trình viên, làm việc tại trụ sở chính." |
| `WORKING_HOURS_LEAVE` | MEDIUM | Thời giờ làm việc, thời giờ nghỉ ngơi, ca kíp, tăng ca, phép năm | "Làm việc 8 tiếng/ngày, từ thứ 2 đến thứ 6; nghỉ phép 12 ngày/năm." |
| `COMPENSATION` | MEDIUM | Lương, phụ cấp, thưởng, hoa hồng, thời hạn/hình thức trả lương | "Mức lương cơ bản 10.000.000 VNĐ, trả vào ngày 5 hàng tháng." |
| `BENEFITS_INSURANCE` | MEDIUM | Bảo hiểm xã hội/y tế/thất nghiệp, phúc lợi khác (ăn trưa, xe đưa đón, khám sức khỏe) | "Công ty đóng BHXH, BHYT, BHTN theo quy định pháp luật." |
| `CONFIDENTIALITY_IP` | HIGH | Bảo mật thông tin, sở hữu trí tuệ, cam kết không cạnh tranh (non-compete) | "Không được làm việc cho đối thủ cạnh tranh trong vòng 24 tháng sau khi nghỉ việc." |
| `TERMINATION` | HIGH | Điều kiện/thủ tục chấm dứt hợp đồng, thời hạn báo trước, bồi thường khi chấm dứt trái luật, thử việc | "Mỗi bên có quyền đơn phương chấm dứt hợp đồng nếu báo trước 30 ngày." |
| `DISPUTE_RESOLUTION` | MEDIUM | Luật áp dụng, cơ quan giải quyết tranh chấp (hòa giải, tòa án, trọng tài) | "Mọi tranh chấp được giải quyết tại Tòa án nhân dân có thẩm quyền." |
| `OTHER` | BOILERPLATE | Điều khoản chung không thuộc 7 nhóm trên: hiệu lực hợp đồng, số bản, cam kết thực hiện | "Hợp đồng có hiệu lực kể từ ngày ký, lập thành 02 bản có giá trị như nhau." |

## 3. Vì sao xếp tier như vậy (rationale cho phần bảo vệ đồ án)

- **HIGH (`CONFIDENTIALITY_IP`, `TERMINATION`):** hai nhóm này có khả năng gây hậu quả pháp lý/tài chính lớn và khó đảo ngược nhất cho người lao động (mất việc, bị ràng buộc không cạnh tranh, tranh chấp bồi thường). Ngưỡng tin cậy yêu cầu (t_low=0.70, t_high=0.90 trong `thresholds.py`) cao nhất — model phải rất chắc chắn mới được xanh (GREEN), nếu không sẽ đẩy sang review thủ công. Đây là lựa chọn "tấm khiên bi quan": thà báo động nhầm còn hơn bỏ sót điều khoản bất lợi nghiêm trọng.
- **MEDIUM (`COMPENSATION`, `WORKING_HOURS_LEAVE`, `BENEFITS_INSURANCE`, `DISPUTE_RESOLUTION`):** ảnh hưởng trực tiếp quyền lợi kinh tế/thời gian nhưng thường có căn cứ pháp luật lao động rõ ràng để đối chiếu, sai sót ít khi nghiêm trọng bằng nhóm HIGH.
- **BOILERPLATE (`JOB_DUTIES`, `OTHER`):** mang tính mô tả/thủ tục, hiếm khi tự thân gây bất lợi, nên ngưỡng tin cậy yêu cầu thấp nhất (t_low=0.50, t_high=0.65).

## 4. Quy tắc gán nhãn khi mơ hồ (áp dụng khi annotate tay lẫn khi review output LLM)

1. Một câu vừa mô tả công việc vừa có ràng buộc cạnh tranh → gán cả `JOB_DUTIES` và `CONFIDENTIALITY_IP`, không chỉ chọn 1.
2. Điều khoản nói về "bồi thường khi đơn phương chấm dứt trái luật" → luôn có `TERMINATION`; nếu số tiền cụ thể được nêu, thêm cả `COMPENSATION`.
3. Nếu không chắc giữa `OTHER` và một nhãn cụ thể, ưu tiên nhãn cụ thể; chỉ dùng `OTHER` khi thực sự không khớp nhãn nào.
4. Ranh giới clause (span) lấy theo đơn vị "Điều" nếu văn bản có đánh số; nếu không đánh số rõ, lấy theo đoạn (paragraph) có chung một ý.

## 5. Kế hoạch mở rộng (không làm ở Tuần 1)

- Theo dõi tỷ lệ nhãn `OTHER` và các trường hợp multi-label >2 nhãn trong Weekly Note; nếu một cụm chủ đề lặp lại nhiều (ví dụ "đào tạo/bồi hoàn chi phí đào tạo") xuất hiện ≥10% dữ liệu, cân nhắc tách thành nhãn riêng ở v2.
- Không đổi tên/xóa nhãn giữa kỳ khi đã có dữ liệu gán nhãn theo v1 — chỉ thêm nhãn mới để tránh phải làm lại toàn bộ annotation.
