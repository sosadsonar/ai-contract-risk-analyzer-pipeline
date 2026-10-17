<!-- nguồn: DATA_PLAN.md | mục: Data Plan — Contract Risk Analyzer > 4. Dùng dataset này trong pipeline mới (cần nhóm chốt) | 619 ký tự | trước: 03_3-annotation-guideline-giu-lai-dong-bang-o-ms-1.md | sau: 05_5-versioning-du-lieu.md -->

## 4. Dùng dataset này trong pipeline mới (cần nhóm chốt)

- Dataset là gold **nhãn clause**. Gold **segmentation** cho M1 vẫn do người sửa tay ranh giới (BRD 8.2 quy tắc 3) vì dataset bỏ heading và tách trong Điều, không phải partition không chồng lấn của `canonical_text`.
- Quy đổi single-label (dataset) ↔ 1–3 nhãn/clause (pipeline, SRS OI-10) khi tính M2/M7 chưa có chính sách → cần chốt cùng annotation guideline trước MS-1.
- `ai_pipeline/eval/fixtures/build_golden_v0_3.py` còn đọc `clauses_v02` không có offset: cần Evaluation Lead cập nhật adapter v06, masks và policy `CONTEXT` trước khi tính F1 (TDD §18.3).
