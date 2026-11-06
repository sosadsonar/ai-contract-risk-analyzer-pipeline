<!-- nguồn: CLAUSE_TAXONOMY_FREEZE.md | mục: Clause Taxonomy — hồ sơ đóng băng MS-1 và chính sách đa nhãn (OI-10) > 1. Phần đã đóng băng | 1810 ký tự | trước: 00_clause-taxonomy-ho-so-dong-bang-ms-1-va-chinh-sach.md | sau: 02_2-chinh-sach-da-nhan-oi-10-de-xuat-n1.md -->

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
