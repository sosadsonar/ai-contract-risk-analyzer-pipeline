# Clause Taxonomy — Contract Risk Analyzer (12 nhãn)

Owner: Clause AI Lead (Người 1); semantics nguồn do Data Lead (Người 2) sở hữu. Cập nhật: 17/10/2026.
Trạng thái: **con trỏ** (SRS Phụ lục C, C-19). File này không còn chứa tier rủi ro, ngưỡng tin cậy hay thống kê nhãn cũ.

## 1. Nguồn chân lý

| Cần gì | Ở đâu |
|---|---|
| Danh sách 12 nhãn + semantics | data repo `docs/clause_taxonomy_v03.md` (qua submodule `ai_pipeline/data`, ghim `c325b43`) và annotation guideline v1.0 |
| Nhãn + định nghĩa dùng trong prompt | `ai_pipeline/config/taxonomy.py` (`LABEL_DEFINITIONS`, `TAXONOMY_VERSION = v04`); prompt tự sinh từ đây |
| Quy tắc đóng băng, đa nhãn | BRD 0.5 §8.2 quy tắc 5–6; SRS DEC-10, OI-10 (freeze ở MS-1, 25/10/2026) |
| Risk taxonomy, severity | **tách biệt** với clause taxonomy (BRD OI-01); không đặt trong file này |

12 nhãn: `JOB_INFO`, `CONTRACT_TERM`, `COMPENSATION_BENEFITS`, `WORKING_TIME`, `LEAVE`, `INSURANCE_SAFETY`, `WORKING_CONDITIONS`, `TRAINING`, `EMPLOYEE_OBLIGATIONS_DISCIPLINE`, `EMPLOYER_RIGHTS_OBLIGATIONS`, `TERMINATION`, `OTHER`.

## 2. Phiên bản

- `v03` = taxonomy nguồn của data (bộ nhãn + semantics).
- `v04` = revision **định nghĩa prompt** trong `taxonomy.py` (12/10/2026): chỉ làm rõ ranh giới nhãn, **không** thêm/bớt nhãn, **không** đổi semantics nguồn. Chi tiết đối chiếu: `DATA_LEAD_REVIEW_V03.md`.
- `ai_pipeline/schemas/clause_output_v2.json` còn cứng `taxonomy_version = v02` và `contract_id`: sẽ được thay bằng `clause_output_v3` (SRS C-04).
- Đổi 12 nhãn hoặc nội dung định nghĩa ⇒ tăng version và sửa test khóa (`tests/test_data_lead_review.py`) có chủ đích; sau MS-1 mọi đổi taxonomy làm mất giá trị số đo (BRD 8.2 quy tắc 5).

## 3. Câu hỏi còn mở (cần nhóm chốt trước MS-1)

1. Nhãn v1 `CONFIDENTIALITY_IP` và `DISPUTE_RESOLUTION` đã mất; mapping bảo mật/không cạnh tranh và giải quyết tranh chấp **chưa** được data v0.3 chốt. Prompt không gán mặc định hai topic này; cần quy định trong annotation guideline khi gặp mẫu có chúng. Không dùng một mapping đề xuất để suy ra mức rủi ro pháp lý.
2. Quyền được bồi thường của NLĐ hiện thuộc `OTHER` (theo v0.3 §4.6, ví dụ HDLD004_C027) vì chưa có class chuyên biệt.
3. Chính sách đa nhãn 1–3 nhãn/clause (SRS OI-10) so với dataset single-label — xem `DATA_PLAN.md` §4.

## 4. Quy trình đổi taxonomy

1. Mở PR mô tả thay đổi; bắt buộc review của Người 1 (Clause AI), Người 2 (Data), Người 3 (Risk AI).
2. Sửa `LABEL_DEFINITIONS` trong `taxonomy.py`; cập nhật enum trong schema bằng cách sinh từ code hoặc test đối chiếu (DEC-20), tăng `TAXONOMY_VERSION`.
3. Cập nhật `test_pipeline.py` / `mock_clause_service.py` / fixture nếu dùng nhãn cũ.
4. Không xóa/đổi tên nhãn khi đã có dữ liệu annotate theo bản trước mà chưa thống nhất với Người 2.
