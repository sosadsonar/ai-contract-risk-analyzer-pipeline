<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 10. Legal Corpus và Citation Validation | 724 ký tự | trước: 10_9-llm-integration-design.md | sau: 12_11-security-va-privacy-architecture.md -->

# 10. Legal Corpus và Citation Validation

* Legal corpus là nguồn đóng duy nhất. Mỗi LegalProvision có citation_id deterministic, version, effective_from/effective_to.
* Corpus build/reload chạy validator trước khi publish index; overlap version hoặc edge invalid -> LEGAL_CORPUS_CONFLICT và fail fast.
* Analysis date là ngày hệ thống phân tích, vì hợp đồng trong phạm vi là hợp đồng chưa ký.
* Citation Validator kiểm tra: candidate membership -> existence -> version/effectivity -> structured metadata.
* Relevance là quality property được đánh giá bằng M3b; runtime không tự tuyên bố relevance chỉ vì citation tồn tại.
* Nếu không đủ căn cứ: giữ RiskResult với INSUFFICIENT_EVIDENCE, citation_ids rỗng và severity null.
