<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 17. Rủi ro kiến trúc và biện pháp | 850 ký tự | trước: 17_16-cac-diem-de-tdd-chot.md | sau: 19_18-ket-luan-thiet-ke.md -->

# 17. Rủi ro kiến trúc và biện pháp

| Rủi ro | Tác động | Thiết kế giảm thiểu |
|---|---|---|
| Graph làm phình scope | Trễ retrieval/pipeline | Baseline retrieval độc lập graph; max 1 hop; non-structural edges là cut item. |
| Parser/PII làm lệch span | Highlight sai | Same-length masking + invariant + backend-authoritative span. |
| LLM output sai schema | Pipeline fail/merge sai | Structured validation + one auto-retry + AI_OUTPUT_INVALID. |
| Provider chậm/lỗi | Không đạt 120s | Batch, timeout 30s, manual retry, stage resume nếu giữ. |
| PII leak | Rủi ro bảo mật | Local masking, HTTPS, privacy tests, no content logs. |
| Corpus/version lỗi | Citation sai | Fail-fast corpus validator + effectivity filter + closed corpus. |
| Codebase lệch tài liệu | Rework | TDD/API schemas trước khi triển khai; traceability; update docs cùng code. |
