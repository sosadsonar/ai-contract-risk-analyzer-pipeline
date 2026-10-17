<!-- nguồn: CLAUSE_TAXONOMY.md | mục: Clause Taxonomy — Contract Risk Analyzer (12 nhãn) > 1. Nguồn chân lý | 791 ký tự | trước: 00_clause-taxonomy-contract-risk-analyzer-12-nhan.md | sau: 02_2-phien-ban.md -->

## 1. Nguồn chân lý

| Cần gì | Ở đâu |
|---|---|
| Danh sách 12 nhãn + semantics | data repo `docs/clause_taxonomy_v03.md` (qua submodule `ai_pipeline/data`, ghim `c325b43`) và annotation guideline v1.0 |
| Nhãn + định nghĩa dùng trong prompt | `ai_pipeline/config/taxonomy.py` (`LABEL_DEFINITIONS`, `TAXONOMY_VERSION = v04`); prompt tự sinh từ đây |
| Quy tắc đóng băng, đa nhãn | BRD 0.5 §8.2 quy tắc 5–6; SRS DEC-10, OI-10 (freeze ở MS-1, 25/10/2026) |
| Risk taxonomy, severity | **tách biệt** với clause taxonomy (BRD OI-01); không đặt trong file này |

12 nhãn: `JOB_INFO`, `CONTRACT_TERM`, `COMPENSATION_BENEFITS`, `WORKING_TIME`, `LEAVE`, `INSURANCE_SAFETY`, `WORKING_CONDITIONS`, `TRAINING`, `EMPLOYEE_OBLIGATIONS_DISCIPLINE`, `EMPLOYER_RIGHTS_OBLIGATIONS`, `TERMINATION`, `OTHER`.
