<!-- nguồn: DATA_PLAN.md | mục: Data Plan — Contract Risk Analyzer > 3. Annotation guideline (giữ lại; đóng băng ở MS-1) | 1152 ký tự | trước: 02_2-hien-trang-dataset-kiem-ngay-12-17-10-2026.md | sau: 04_4-dung-dataset-nay-trong-pipeline-moi-can-nhom-cho.md -->

## 3. Annotation guideline (giữ lại; đóng băng ở MS-1)

Guideline đầy đủ: data repo (annotation guideline v1.0 + `clause_taxonomy_v03.md`). Tóm tắt phần ảnh hưởng tới pipeline:

1. Một **Điều** có thể chứa nhiều clause; câu/bullet đa chủ đề được **tách** thành nhiều clause thay vì gán đa nhãn. Một dòng dataset = **một nhãn**.
2. `clause_text` **không** gồm heading "Điều X. …" và không gồm phần hành chính (Rule 5, 6).
3. Offset tính theo **Unicode code point**, `[start, end)`, trên đúng raw text đã hash (không tính theo dòng).
4. `offset_quality`: `EXACT` = đoạn khớp nguyên văn sau gom khoảng trắng; `CONTEXT` = annotation lặp ngữ cảnh sau khi tách nên không có đoạn nguyên văn. `CONTEXT` giữ `span = null` ở consumer, **không** ép `_locate_span` tìm đoạn giả và **không** chấm như gold span chính xác; có thể dùng source-reference span riêng để highlight.
5. Không bịa mức/điều kiện vào chỗ trống trong hợp đồng; không dùng định nghĩa nhãn để suy ra mức rủi ro pháp lý.
6. Hợp đồng thật: bắt buộc de-identify thủ công; hợp đồng mới nên có ít nhất 1 clause "khó"; cần ≥ 20% item do hai người gán độc lập để tính Cohen's kappa (BRD 8.2 quy tắc 4).
