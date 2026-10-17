<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 18. Kết luận thiết kế | 341 ký tự | trước: 18_17-rui-ro-kien-truc-va-bien-phap.md | sau: - -->

# 18. Kết luận thiết kế

Kiến trúc đề xuất giữ hệ thống ở mức vừa sức cho demo: một modular monolith, session data tạm thời, hai LLM calls bắt buộc, retrieval cục bộ với Data Graph là lớp mở rộng và Clause Graph là lớp context cho reasoning. Thiết kế ưu tiên privacy, khả năng truy vết, kiểm thử và khả năng fallback hơn độ phức tạp hạ tầng.
