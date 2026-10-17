<!-- nguồn: CLAUSE_TAXONOMY.md | mục: Clause Taxonomy — Contract Risk Analyzer (12 nhãn) > 4. Quy trình đổi taxonomy | 469 ký tự | trước: 03_3-cau-hoi-con-mo-can-nhom-chot-truoc-ms-1.md | sau: - -->

## 4. Quy trình đổi taxonomy

1. Mở PR mô tả thay đổi; bắt buộc review của Người 1 (Clause AI), Người 2 (Data), Người 3 (Risk AI).
2. Sửa `LABEL_DEFINITIONS` trong `taxonomy.py`; cập nhật enum trong schema bằng cách sinh từ code hoặc test đối chiếu (DEC-20), tăng `TAXONOMY_VERSION`.
3. Cập nhật `test_pipeline.py` / `mock_clause_service.py` / fixture nếu dùng nhãn cũ.
4. Không xóa/đổi tên nhãn khi đã có dữ liệu annotate theo bản trước mà chưa thống nhất với Người 2.
