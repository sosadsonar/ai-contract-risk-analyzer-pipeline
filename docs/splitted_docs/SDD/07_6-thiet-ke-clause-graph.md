<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 6. Thiết kế Clause Graph | 1315 ký tự | trước: 06_5-thiet-ke-data-graph.md | sau: 08_7-kien-truc-du-lieu-va-luu-tru.md -->

# 6. Thiết kế Clause Graph

Clause Graph là đồ thị tạm thời của một session, dựng ngay sau segmentation. Graph chỉ chứa ID và quan hệ; mọi text được truy xuất từ session store khi cần.

## 6.1 Mô hình Clause Graph

| Edge | Nguồn | Ý nghĩa |
|---|---|---|
| NEXT | Thứ tự span | Clause kế tiếp trong canonical text. |
| PARENT_OF | Đánh số cấu trúc | Điều chứa khoản/điểm con. |
| REFERS_TO | Luật cục bộ/regex trên masked clause | Điều khoản dẫn chiếu rõ tới clause khác trong cùng hợp đồng. |

## 6.2 Cách dùng cho Validation & Reasoning

SDD chốt Clause Graph là một Context Resolver, không phải nguồn dữ liệu phân tích độc lập và không tạo thêm LLM stage.

* Đối với mỗi target clause, Context Resolver lấy các clause liên quan trực tiếp qua REFERS_TO và PARENT_OF; NEXT có thể dùng làm ngữ cảnh lân cận khi cần.
* Backend lấy masked text của các related_clause_ids từ cùng session và truyền dưới dạng context bổ sung cho Risk LLM.
* Risk LLM vẫn phải trả kết quả cho target clause_id; related clauses chỉ hỗ trợ phát hiện điều kiện, mâu thuẫn hoặc phụ thuộc.
* Clause Graph không được thay đổi segmentation, original_text, span hoặc quote.
* Nếu không có cạnh liên quan, Risk stage chạy như pipeline bình thường với target clause.
* Số related clauses/context limit được cấu hình ở TDD để kiểm soát token/cost.
