<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 11. Security và Privacy Architecture | 786 ký tự | trước: 11_10-legal-corpus-va-citation-validation.md | sau: 13_12-reliability-performance-va-cost.md -->

# 11. Security và Privacy Architecture

| Kiểm soát | Thiết kế |
|---|---|
| Transport | HTTPS Browser->Backend và Backend->Gemini trong deployment. |
| Session identity | session_id opaque/random (UUID v4 hoặc tương đương). |
| PII boundary | Chỉ masked text ra ngoài trusted backend. |
| PII preservation | Placeholder cùng độ dài; không lưu mapping ngược. |
| Secrets | Environment/secret configuration; model id bắt buộc. |
| Logging | Chỉ ID/stage/timing/error/token/cost; không raw/canonical/masked text đầy đủ. |
| Retention | End Session hoặc 60 phút inactivity; session content bị xóa. |
| Persistent storage | Không lưu file/canonical/masked/result/Clause Graph vào DB hoặc durable storage. |
| Abuse control | Daily LLM-call quota + IP rate limit; không dùng demo password. |
