# Clause Taxonomy v2 — Contract Risk Analyzer (12 nhãn)

Owner: Người 1 – Clause AI Lead
Trạng thái: **v2 – ĐỀ XUẤT, chờ Người 2 (Data) và Người 3 (Risk AI) review** trước khi merge.

Data review ngày 12/10/2026 được lưu tại `DATA_LEAD_REVIEW_V03.md` cùng
`data_lead_span_audit.json`. Nhánh review sửa định nghĩa prompt thành revision
`TAXONOMY_VERSION=v04`, giữ nguyên 12 nhãn/semantics data v0.3; submodule pin
main data `c325b43` (v06, 234 clause). Risk tier và ngưỡng vẫn chờ Risk AI chốt.

**Nguồn chân lý (source of truth):**
- Danh sách nhãn + định nghĩa nội dung: `ai_pipeline/data/docs/clause_taxonomy_v03.md` (repo `data`, Người 2 sở hữu).
- Nhãn + định nghĩa dùng trong code, rule multi-label: `ai_pipeline/config/taxonomy.py` (`LABEL_DEFINITIONS`) và `ai_pipeline/config/labeling.py` (`MultiLabelRule`, `resolve_multi_labels`) — của Người 1, đóng băng.
- Tier rủi ro + ngưỡng: `ai_pipeline/config/risk_routing.py` (`RISK_TAXONOMY_MAP`, `TIER_THRESHOLDS`) — của Người 3, tự chốt khi sign-off.
- Prompt của LLM **tự sinh** từ `LABEL_DEFINITIONS` trong `taxonomy.py`, không sửa tay trong `clause_extraction_service.py`.

Semantics nhãn phải theo source data v0.3. Nếu code hoặc tài liệu này lệch
source đó, cần sửa qua PR review có chủ đích; version code là bằng chứng
phiên bản triển khai, không thay thế nguồn semantics. Tier/ngưỡng vẫn thuộc
quyết định được Risk AI sign-off.

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
- **LOW:** mô tả/thủ tục, hiếm khi tự thân bất lợi → ngưỡng thấp nhất.

**Câu hỏi mở cần chốt trong PR:**

1. **Mất nhãn `CONFIDENTIALITY_IP` và `DISPUTE_RESOLUTION` của v1.** Đề xuất mapping bảo mật/không cạnh tranh và giải quyết tranh chấp chưa được source data v0.3 chốt. Nhánh Data review bỏ gán mặc định các topic đó khỏi định nghĩa prompt; nhóm vẫn cần chốt guideline khi nhận mẫu có các topic này. Không dùng một mapping đề xuất để suy ra mức rủi ro pháp lý.
2. **`EMPLOYEE_OBLIGATIONS_DISCIPLINE` = HIGH** kéo tỉ lệ clause HIGH lên khoảng 31% (44/140) → nhiều clause vào diện review hơn. Người 3 cân nhắc giữa "không bỏ sót" và "khối lượng review".
3. **`EMPLOYER_RIGHTS_OBLIGATIONS` = MEDIUM**: có thể chứa điều chuyển/đơn phương thay đổi — Người 3 xem có cần HIGH không.
4. **`CONTRACT_TERM` = BOILERPLATE**: chỉ 3 clause, chưa đủ dữ liệu để đánh giá.

## 4. Quy tắc gán nhãn

Dùng taxonomy `ai_pipeline/data/docs/clause_taxonomy_v03.md` và annotation guideline v1.0, đặc biệt mục phân biệt class dễ nhầm. Tóm tắt những điểm ảnh hưởng trực tiếp tới pipeline:

- Một **Điều** có thể chứa nhiều clause; câu multi-topic được tách (Rule 1, 2, 4).
- `clause_text` **không gồm heading** "Điều X. Tên điều" (Rule 6) và không gồm phần hành chính (Rule 5).
- Một dòng dữ liệu = một nhãn (CSV hiện là single-label); multi-label thể hiện bằng cách tách clause.

## 5. Quy trình đổi taxonomy

1. Mở PR `docs/...` hoặc `ai/...` mô tả thay đổi; **bắt buộc review của Người 1, 2, 3**.
2. Sửa `LABEL_DEFINITIONS` trong `taxonomy.py` (của Người 1) **và** `RISK_TAXONOMY_MAP` trong `risk_routing.py` (của Người 3) — import `risk_routing.py` sẽ lỗi ngay nếu hai bảng lệch nhau.
3. Cập nhật file này và `test_pipeline.py`/`mock_clause_service.py` nếu có dùng nhãn cũ (`compute_clause_routing` báo lỗi khi gặp nhãn lạ).
4. Không xóa/đổi tên nhãn khi đã có dữ liệu annotate theo bản trước mà chưa thống nhất với Người 2.
