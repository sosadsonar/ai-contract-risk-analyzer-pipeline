# Clause Taxonomy — hồ sơ đóng băng MS-1 và chính sách đa nhãn (OI-10)

Owner: Người 1 (Clause AI). Đồng review: Người 2 (dữ liệu/guideline), Người 3 (risk taxonomy). Ngày: 25/10/2026.
Nguồn: `PROGRESS.md` tuần 2, SRS DEC-10 / OI-10, BRD §8.2 quy tắc 5–6. Tài liệu này **bổ sung** `CLAUSE_TAXONOMY.md` (con trỏ); không thay nó.

> **Trạng thái:** §1 (đóng băng kỹ thuật) **đã có hiệu lực** — test khóa chạy trong CI. §2–§3 là **[Đề xuất N1]**, cần N2 và N3 xác nhận (§4) trước khi đưa vào annotation guideline. Chưa xác nhận thì **không** đổi `LABEL_DEFINITIONS`; xác nhận mà phải đổi định nghĩa thì tăng version (§1.3).

## 1. Phần đã đóng băng

### 1.1 Nội dung bị khóa

| Hạng mục | Giá trị khóa |
|---|---|
| Taxonomy nguồn của data (`taxonomy_version` trong `clause_output_v3`) | `clause_taxonomy_v03` |
| Revision định nghĩa dùng trong prompt (`clause_prompt_version`) | `v04` |
| Số nhãn mỗi clause | 1 đến 3, nhãn đầu là nhãn chính, không trùng (`validate_labels`) |
| 12 nhãn | `JOB_INFO`, `CONTRACT_TERM`, `COMPENSATION_BENEFITS`, `WORKING_TIME`, `LEAVE`, `INSURANCE_SAFETY`, `WORKING_CONDITIONS`, `TRAINING`, `EMPLOYEE_OBLIGATIONS_DISCIPLINE`, `EMPLOYER_RIGHTS_OBLIGATIONS`, `TERMINATION`, `OTHER` |
| Fingerprint (sha256: dòng version + min/max, rồi từng `nhãn\|định nghĩa` theo thứ tự) | `2449733fe397438f4aa9ebee9bf2568c8f7708c2a10f837fbb46283b889390c2` |

Khóa bằng `tests/unit/test_clause_taxonomy_freeze.py` (cùng kiểu với `test_risk_taxonomy_freeze.py` của N3). Hai test cũ `tests/unit/test_clause_taxonomy.py`, `tests/test_data_lead_review.py` vẫn giữ.

### 1.2 Không đổi (đã đối chiếu)

- 12 nhãn của `taxonomy.py` = 12 nhãn data repo `v06-rc1` (đối chiếu 20/10/2026).
- Enum nhãn trong `ai_pipeline/schemas/clause_output_v3.json` có test đối chiếu với `taxonomy.py` (DEC-20).
- Clause taxonomy **tách biệt** risk taxonomy (`risk_taxonomy_v01`, N3); hai bên không dùng chung nhãn.

### 1.3 Cách đổi sau MS-1 (hiếm, có chủ đích)

1. Sửa `backend/app/clause/taxonomy.py`, tăng `TAXONOMY_VERSION` (đổi chữ định nghĩa) hoặc `DATA_TAXONOMY_VERSION` (đổi từ vựng/semantics nguồn — phải có bản data tương ứng của N2).
2. Sửa hằng `FROZEN_*` trong test khóa; cập nhật bảng §1.1 ở đây; ghi lý do vào `PROGRESS.md` §9.
3. Review bắt buộc N1 + N2 + N3. Báo N2 trước nếu đã có gold gán theo bản cũ (không đổi tên/xóa nhãn khi còn dữ liệu annotate).
4. Mọi số đo M7 lấy trước đó không còn so sánh được — ghi rõ trong báo cáo.

## 2. Chính sách đa nhãn (OI-10) — [Đề xuất N1]

**Quy tắc cho người gán nhãn và cho prompt (một nguồn: guideline ↔ `taxonomy.py` ↔ prompt):**

1. **Mặc định 1 nhãn.** Chỉ thêm nhãn phụ khi clause có ít nhất một ý trọn vẹn (một câu hoặc một mệnh đề có chủ đề riêng) thuộc nhãn khác. Nhắc thoáng qua một từ khóa không đủ.
2. Tối đa 3 nhãn. Nhãn đầu = nhãn chính = chủ đề chiếm nhiều nội dung nhất; khi hòa, lấy chủ đề xuất hiện đầu clause. Không trùng nhãn.
3. `OTHER` chỉ dùng một mình (nếu có nhãn cụ thể thì không thêm `OTHER`). **Chưa được code ép** (`validate_labels` hiện cho phép); nếu nhóm đồng ý, thêm vào `validate_labels` kèm test và tăng `TAXONOMY_VERSION`.
4. Clause chỉ gồm tiêu đề (ví dụ `Điều 5. Tiền lương` khi các khoản con là clause riêng — TDD §11.2) gán theo chủ đề của tiêu đề, không bỏ trống. Hệ thống không có "nhãn rỗng".
5. Phân loại **không nhận role** (INV-05); nhãn không phụ thuộc NLĐ/NSDLĐ.

**Quy đổi dataset single-label ↔ dự đoán đa nhãn (cho harness M7, C-18 — N2 xác nhận):**

- Dataset `clauses_v06.csv` có một dòng cho một nhãn và không phải partition của `canonical_text` (xem `DATA_PLAN.md` §4). Mỗi clause dự đoán `p` nhận **tập nhãn vàng** = hợp nhãn của các dòng `EXACT` có span giao với `p`. Dòng `CONTEXT` (span null / không chính xác) **không** dùng để chấm.
- M7 (BRD §8.3) chấm theo cặp (clause, nhãn): mỗi nhãn dự đoán của `p` là một cặp; đúng nếu nằm trong tập nhãn vàng của `p`. Cặp vàng không có dự đoán tính là bỏ sót.
- Báo thêm chỉ số chẩn đoán "nhãn chính đúng" (nhãn đầu ∈ tập vàng), **không** thay M7. Số nhãn trung bình mỗi clause dự đoán phải được báo cùng M7 để thấy việc "gán thừa nhãn kéo recall".
- Gold T1/T2 gán trực tiếp theo quy tắc §2 (1–3 nhãn, có nhãn chính), không dùng quy đổi này.

## 3. Ba topic chưa có nhãn riêng — [Đề xuất N1, chờ N2/N3]

12 nhãn đã đóng băng nên **không thêm nhãn**. Đề xuất gán vào nhãn hiện có để annotation guideline có quy tắc thống nhất. Không dùng các gán này để suy ra mức rủi ro pháp lý (risk taxonomy của N3 là nơi quyết định rủi ro).

| Topic | Đề xuất | Lý do / điểm cần N2, N3 xác nhận |
|---|---|---|
| Bảo mật thông tin, không cạnh tranh, sở hữu trí tuệ của NLĐ (nhãn `CONFIDENTIALITY_IP` v1 đã mất) | Nhãn chính `EMPLOYEE_OBLIGATIONS_DISCIPLINE`; thêm `TERMINATION` làm nhãn phụ **chỉ khi** clause tự nêu hậu quả/điều kiện sau chấm dứt hợp đồng | Là nghĩa vụ của NLĐ. **Khớp** `RISK_TAXONOMY_v0.1.md` của N3: `POST_EMPLOYMENT_RESTRICTION` (bảo mật, không cạnh tranh, chuyển giao SHTT) tham chiếu clause label `EMPLOYEE_OBLIGATIONS_DISCIPLINE`; N3 xác nhận lại. Nếu cần tách nhóm này để đo, thêm nhãn ở bản taxonomy sau (version mới), không "phân biệt ngầm" trong guideline |
| Giải quyết tranh chấp / luật áp dụng (`DISPUTE_RESOLUTION` v1 đã mất) | `OTHER` (một nhãn) | Không thuộc nhãn nào trong 11 nhãn nội dung; gần "điều khoản thi hành". Nếu clause trộn với điều khoản thi hành/số bản thì vẫn `OTHER` |
| Quyền được bồi thường của NLĐ | Hai hướng theo chủ thể câu: câu viết từ **nghĩa vụ NSDLĐ** ("NSDLĐ phải bồi thường…") → `EMPLOYER_RIGHTS_OBLIGATIONS`; **quyền chung của NLĐ** không có chủ thể NSDLĐ rõ ("NLĐ được bồi thường…", ví dụ HDLD004_C027) → `OTHER` theo data v0.3 §4.6 | Định nghĩa hiện tại của hai nhãn **chồng nhau** ở điểm này (`EMPLOYER_RIGHTS_OBLIGATIONS` có "phải bồi thường cho NLĐ", `OTHER` có "quyền được bồi thường của NLĐ"). Quy tắc theo chủ thể là cách đọc nhất quán với v0.3 §4.6; cần N2 ghi vào guideline và kiểm lại 1–2 mẫu |

Nếu N2/N3 chọn khác: sửa bảng này, sửa `LABEL_DEFINITIONS` nếu cần (tăng `TAXONOMY_VERSION` lên `v05`, mục §1.3), rồi mới đưa vào guideline.

## 4. Sign-off

| Người | Việc xác nhận | Trạng thái |
|---|---|---|
| N1 | §1 đóng băng kỹ thuật + §2 chính sách đa nhãn | Đề xuất xong (25/10/2026) |
| N2 | §2 quy đổi dataset ↔ M7; §3 ba topic; ghi vào annotation guideline | **Chờ** |
| N3 | §3 topic bảo mật/không cạnh tranh có khớp risk taxonomy | **Chờ** |
