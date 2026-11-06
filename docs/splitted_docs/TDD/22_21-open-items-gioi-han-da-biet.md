<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.3.md | mục: 21. Open items / giới hạn đã biết | 2086 ký tự | trước: 21_20-traceability-va-ke-hoach-migration-codebase.md | sau: 23_phu-luc-a-json-schema-mau.md -->

# 21. Open items / giới hạn đã biết

| ID | Mục | Xử lý | Ảnh hưởng |
|---|---|---|---|
| O-01 | Risk taxonomy v0.1 đã có nhưng chưa freeze (còn rà severity, đổi tên nhãn) | TDD dùng placeholder; phải đóng băng MS-1. | Block prompt/eval final. |
| O-02 | DOCX numbering/textbox cases phụ thuộc D1/T1 | Chỉ support fixture chốt; ghi known limitation. | FR-08/OI-11. |
| O-03 | PII local rules có thể chưa đạt recall tên/địa chỉ/pháp nhân | Đo D1 sớm; thêm local NER nếu cần. | OI-12. |
| O-04 | Daily quota + session call reserve chưa có số cost thực | Đo D1, chốt trước demo/MS-2. TDD 0.2 cố ý không giữ số 120 tùy ý. | FR-27/NFR-COST. |
| O-05 | Batch/parallelism/graph weight/neighbor cap cần benchmark | Tune D1/D2, version config. | PERF/M8. |
| O-06 | REFERS_TO/GUIDES legal edges cần người dữ liệu xác minh | Trễ thì cut item 5, giữ structural edges. | BRD 9.5. |
| O-07 | PDF export có thể bị cắt | DOCX vẫn đầy đủ. | Cut item 4. |
| O-08 | Stage resume có thể bị cắt | Retry từ đầu, max 2. | Cut item 2. |
| O-09 | API-state codes của §5.8 chưa backport SRS 6.2 | Không đổi state semantics; đề xuất cập nhật SRS để trace. | Documentation consistency. |
| O-10 | `related_clause_ids` trong RiskResult product | Đã có ở SRS 1.4 (DEC-24) và FR-32; TDD đưa vào risk_output_v2 và final_result_v1 dưới dạng trường tùy chọn. | Đóng. |
| O-11 | SDD sơ đồ state chưa vẽ VALIDATING -> FAILED; Cleanup Scheduler/component và startup numbering có lỗi trình bày | Không sửa SDD trong TDD; cần cập nhật SDD ở revision kế tiếp. | Doc consistency. |
| O-12 | Không có luật sư xác minh legal correctness toàn diện | Disclaimer, closed corpus, evaluation limitations. | BRD 8/10. |
| O-13 | Mức hạt corpus là Khoản; hậu tố citation_id cho khoản | N2 chốt định dạng và ngưỡng tách điểm cho khoản quá dài | 14.2. |
| O-14 | Khóa chữ ký hàm và schema | Dự kiến 05/11/2026, sau khi taxonomy freeze | SKELETON 13. |

Các DEC-16..21 trong SRS vẫn có mục “đề xuất/chờ nhóm duyệt” ở một số dòng. Nếu nhóm đổi các quyết định đó, SDD/TDD phải được version lại; TDD 0.2 không tự coi chúng đã được phê duyệt.
