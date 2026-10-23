<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 5. Thiết kế Data Graph | 1592 ký tự | trước: 05_4-pipeline-xu-ly-end-to-end.md | sau: 07_6-thiet-ke-clause-graph.md -->

# 5. Thiết kế Data Graph

Data Graph là lớp kiến thức bổ sung trên closed legal corpus, phục vụ Retrieval & Fact-finding. Nó không thay thế retriever nền và không có quyền tạo citation ngoài corpus.

![](/docs/diagrams/graphs.png)

*Hình 4. Data Graph và Clause Graph trong pipeline*

## 5.1 Mô hình Data Graph

| Thành phần | Thiết kế SDD |
|---|---|
| Node | LegalProvision, định danh bởi citation_id. |
| PARENT_OF | Sinh tự động từ parent_path; phải acyclic. |
| REFERS_TO | Dữ liệu corpus do người phụ trách dữ liệu xác minh; có thể được gợi ý tự động nhưng không dùng trực tiếp khi chưa xác minh. |
| GUIDES | Dữ liệu corpus mô tả văn bản hướng dẫn thi hành; được người phụ trách dữ liệu xác minh. |
| Storage | Artifact dữ liệu cùng legal corpus; khi backend khởi động/reload sẽ validate rồi tạo adjacency index trong memory. |
| Validation | Mọi endpoint của edge phải tồn tại; PARENT_OF không có cycle; conflict làm build/reload fail fast. |
| Lifecycle | Persistent như corpus, nhưng không chứa dữ liệu hợp đồng. |

## 5.2 Retrieval + Graph Expansion

![](/docs/diagrams/retrieval.png)

* Seed candidate luôn được ưu tiên hơn candidate chỉ xuất hiện do graph expansion.
* Expansion mặc định tối đa 1 hop; số seed/top candidate và số candidate cuối cấu hình ở TDD.
* Neighbor hết hiệu lực tại analysis date bị bỏ qua.
* Exact scoring/weight theo edge type để TDD chốt sau số đo D1/D2; SDD không khóa số trọng số.
* Embedding không thuộc baseline. Chỉ thêm nếu M8 trên D2 cho thấy mapping + lexical + graph chưa đủ.
* EV-08 chạy cùng pipeline với Data Graph bật và tắt để báo M8 ở hai cấu hình.
