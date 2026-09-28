# Clause Taxonomy v2 — Contract Risk Analyzer (12 nhãn)

Owner: Người 1 – Clause AI Lead
Trạng thái: **v2 – ĐỀ XUẤT, chờ Người 2 (Data) và Người 3 (Risk AI) review** trước khi merge.

**Nguồn chân lý (source of truth):**
- Danh sách nhãn + định nghĩa nội dung: `ai_pipeline/data/docs/clause_taxonomy_v03.md` (repo `data`, Người 2 sở hữu).
- Nhãn + định nghĩa dùng trong code, rule multi-label: `ai_pipeline/config/taxonomy.py` (`LABEL_DEFINITIONS`) và `ai_pipeline/config/labeling.py` (`MultiLabelRule`, `resolve_multi_labels`) — của Người 1, đóng băng.
- Tier rủi ro + ngưỡng: `ai_pipeline/config/risk_routing.py` (`RISK_TAXONOMY_MAP`, `TIER_THRESHOLDS`) — của Người 3, tự chốt khi sign-off.
- Prompt của LLM **tự sinh** từ `LABEL_DEFINITIONS` trong `taxonomy.py`, không sửa tay trong `clause_extraction_service.py`.

Nếu file này lệch với code, code là bản đúng và file này cần cập nhật.

## 1. Vì sao đổi từ 8 nhãn (v1) sang 12 nhãn (v2)

v1 (8 nhãn) do Người 1 tự đặt ở Tuần 1 khi chưa có dữ liệu thật. Sau khi Người 2 annotate 140 clause của 3 hợp đồng pilot (HDLD001–003) thì bộ nhãn thực tế là 12 nhãn khác tên. Để test pipeline trên dữ liệu thật, hai bên phải dùng **cùng một bộ nhãn**, nên `ai_pipeline` đổi theo data (dữ liệu đã annotate, đắt hơn để làm lại).

## 2. Bảng nhãn v2

| Nhãn | Tier (đề xuất) | Định nghĩa | SL trong data v0.2 |
|---|---|---|---:|
| `TERMINATION` | HIGH | Căn cứ, điều kiện, thủ tục, báo trước và hậu quả của việc chấm dứt HĐLĐ | 15 |
| `TRAINING` | HIGH | Đào tạo, bồi dưỡng, cam kết sau đào tạo, hoàn trả chi phí đào tạo | 9 |
| `EMPLOYEE_OBLIGATIONS_DISCIPLINE` | HIGH | Nghĩa vụ, kỷ luật, trách nhiệm vật chất, bồi thường, nghĩa vụ thuế của NLĐ | 20 |
| `COMPENSATION_BENEFITS` | MEDIUM | Lương, phụ cấp, thưởng, nâng lương, công tác phí, chế độ/quyền lợi tài chính | 24 |
| `WORKING_TIME` | MEDIUM | Giờ làm, lịch làm, ca làm, làm thêm giờ | 7 |
| `LEAVE` | MEDIUM | Nghỉ hằng tuần, phép năm, lễ/Tết, nghỉ bù | 9 |
| `INSURANCE_SAFETY` | MEDIUM | BHXH/BHYT/BHTN, an toàn và vệ sinh lao động | 7 |
| `EMPLOYER_RIGHTS_OBLIGATIONS` | MEDIUM | Quyền và nghĩa vụ quản lý, điều hành của NSDLĐ | 16 |
| `JOB_INFO` | BOILERPLATE | Công việc, chức danh, địa điểm, nhiệm vụ | 15 |
| `CONTRACT_TERM` | BOILERPLATE | Loại và thời hạn HĐLĐ, ngày bắt đầu/kết thúc | 3 |
| `WORKING_CONDITIONS` | BOILERPLATE | Công cụ, thiết bị, điều kiện vật chất phục vụ công việc | 3 |
| `OTHER` | BOILERPLATE | Điều khoản thi hành, sửa đổi/phụ lục và nội dung không thuộc nhóm nào | 12 |

## 3. Vì sao xếp tier như vậy — VÀ những chỗ cần Người 3 chốt

Tier là quyết định **chính sách rủi ro**, không chỉ đổi tên nhãn. Người 1 đề xuất, Người 3 quyết định.

- **HIGH (`TERMINATION`, `TRAINING`, `EMPLOYEE_OBLIGATIONS_DISCIPLINE`):** hậu quả pháp lý/tài chính lớn, khó đảo ngược (mất việc, phải hoàn trả chi phí đào tạo, bị kỷ luật/bồi thường). Ngưỡng tin cậy cao nhất (t_low=0.70, t_high=0.90) theo nguyên tắc "tấm khiên bi quan": thà báo nhầm còn hơn bỏ sót.
- **MEDIUM:** ảnh hưởng quyền lợi kinh tế/thời gian nhưng có căn cứ pháp luật rõ để đối chiếu.
- **BOILERPLATE:** mô tả/thủ tục, hiếm khi tự thân bất lợi → ngưỡng thấp nhất.

**Câu hỏi mở cần chốt trong PR:**

1. **Mất nhãn `CONFIDENTIALITY_IP` (v1 xếp HIGH) và `DISPUTE_RESOLUTION` (v1 xếp MEDIUM).** Bộ 12 nhãn không có 2 nhãn này (3 hợp đồng pilot không có clause nào thuộc loại này). Đề xuất tạm: bảo mật/không cạnh tranh → `EMPLOYEE_OBLIGATIONS_DISCIPLINE` (đã xếp HIGH để không hạ mức rủi ro so với v1); giải quyết tranh chấp → `OTHER`. **Người 2 xác nhận** guideline sẽ gán như vậy, hoặc thêm nhãn riêng khi data mở rộng (Tuần 3+).
2. **`EMPLOYEE_OBLIGATIONS_DISCIPLINE` = HIGH** kéo tỉ lệ clause HIGH lên khoảng 31% (44/140) → nhiều clause vào diện review hơn. Người 3 cân nhắc giữa "không bỏ sót" và "khối lượng review".
3. **`EMPLOYER_RIGHTS_OBLIGATIONS` = MEDIUM**: có thể chứa điều chuyển/đơn phương thay đổi — Người 3 xem có cần HIGH không.
4. **`CONTRACT_TERM` = BOILERPLATE**: chỉ 3 clause, chưa đủ dữ liệu để đánh giá.

## 4. Quy tắc gán nhãn

Dùng nguyên quy tắc trong `ai_pipeline/data/docs/clause_taxonomy_v02.md` (Rule 1–6 và mục "phân biệt class dễ nhầm"). Tóm tắt những điểm ảnh hưởng trực tiếp tới pipeline:

- Một **Điều** có thể chứa nhiều clause; câu multi-topic được tách (Rule 1, 2, 4).
- `clause_text` **không gồm heading** "Điều X. Tên điều" (Rule 6) và không gồm phần hành chính (Rule 5).
- Một dòng dữ liệu = một nhãn (CSV hiện là single-label); multi-label thể hiện bằng cách tách clause.

## 5. Quy trình đổi taxonomy

1. Mở PR `docs/...` hoặc `ai/...` mô tả thay đổi; **bắt buộc review của Người 1, 2, 3**.
2. Sửa `LABEL_DEFINITIONS` trong `taxonomy.py` (của Người 1) **và** `RISK_TAXONOMY_MAP` trong `risk_routing.py` (của Người 3) — import `risk_routing.py` sẽ lỗi ngay nếu hai bảng lệch nhau.
3. Cập nhật file này và `test_pipeline.py`/`mock_clause_service.py` nếu có dùng nhãn cũ (`compute_clause_routing` báo lỗi khi gặp nhãn lạ).
4. Không xóa/đổi tên nhãn khi đã có dữ liệu annotate theo bản trước mà chưa thống nhất với Người 2.