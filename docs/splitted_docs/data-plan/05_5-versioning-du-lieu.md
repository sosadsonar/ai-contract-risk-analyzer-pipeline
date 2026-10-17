<!-- nguồn: DATA_PLAN.md | mục: Data Plan — Contract Risk Analyzer > 5. Versioning dữ liệu | 348 ký tự | trước: 04_4-dung-dataset-nay-trong-pipeline-moi-can-nhom-cho.md | sau: 06_6-con-mo.md -->

## 5. Versioning dữ liệu

- `golden_v0.1.json`, `golden_v0.2.json` (Tuần 1; taxonomy 8 nhãn cũ): **giữ làm lịch sử**, không dùng cho KPI.
- Data repo: các bản `clauses_v0x.csv` tăng version khi đổi đáng kể số lượng/taxonomy/offset; không sửa đè bản cũ. Report audit ghi cả hash file đọc thực tế và hash Git blob (khác nhau do CRLF/LF trên Windows).
