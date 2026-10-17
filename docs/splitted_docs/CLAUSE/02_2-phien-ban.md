<!-- nguồn: CLAUSE_TAXONOMY.md | mục: Clause Taxonomy — Contract Risk Analyzer (12 nhãn) > 2. Phiên bản | 613 ký tự | trước: 01_1-nguon-chan-ly.md | sau: 03_3-cau-hoi-con-mo-can-nhom-chot-truoc-ms-1.md -->

## 2. Phiên bản

- `v03` = taxonomy nguồn của data (bộ nhãn + semantics).
- `v04` = revision **định nghĩa prompt** trong `taxonomy.py` (12/10/2026): chỉ làm rõ ranh giới nhãn, **không** thêm/bớt nhãn, **không** đổi semantics nguồn. Chi tiết đối chiếu: `DATA_LEAD_REVIEW_V03.md`.
- `ai_pipeline/schemas/clause_output_v2.json` còn cứng `taxonomy_version = v02` và `contract_id`: sẽ được thay bằng `clause_output_v3` (SRS C-04).
- Đổi 12 nhãn hoặc nội dung định nghĩa ⇒ tăng version và sửa test khóa (`tests/test_data_lead_review.py`) có chủ đích; sau MS-1 mọi đổi taxonomy làm mất giá trị số đo (BRD 8.2 quy tắc 5).
