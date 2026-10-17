<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 3. Kiến trúc tổng thể | 2816 ký tự | trước: 03_2-system-context.md | sau: 05_4-pipeline-xu-ly-end-to-end.md -->

# 3. Kiến trúc tổng thể

Backend được thiết kế thành các module độc lập theo trách nhiệm nhưng chạy trong cùng một deployment. Analysis Orchestrator điều phối state machine và pipeline; các module local không phụ thuộc LLM.

![](/diagrams/system_overall.png)

*Hình 2. Component Architecture*

## 3.1 Phân rã component

| Component | Trách nhiệm | Ràng buộc |
|---|---|---|
| Web Frontend | Upload, chọn role, polling status, hiển thị canonical text/highlight, kết quả và export. | Không tự merge AI result hay tính span. |
| API / Session Controller | Nhận operation, tạo session_id, enforce SYSTEM_BUSY/rate/quota, expose status/result/retry/end. | Không chứa logic AI. |
| Analysis Orchestrator | Điều phối stage, state transition, retry, batch, version pinning và error mapping. | Nguồn điều phối duy nhất. |
| Ephemeral Session Store | Giữ session, canonical/masked text, clauses, Clause Graph, AI outputs tạm thời. | Không lưu bền vững; TTL 60 phút. |
| Document Processing | PDF/DOCX extraction, NFC normalization, reading order, header/footer/table handling. | Sinh canonical_text + extraction_version. |
| Scope Precheck | Luật cục bộ xác nhận tài liệu thuộc HĐLĐ. | Không gọi LLM. |
| PII Masker | Che PII trên toàn canonical text bằng placeholder cùng độ dài. | Không lưu mapping ngược. |
| Clause Segmenter | Tách clause bằng rule structural + paragraph fallback, backend tính span. | LLM segmentation chỉ là optional/cut item. |
| Clause Graph Builder | Dựng NEXT/PARENT_OF/REFERS_TO chỉ bằng clause_id. | Ephemeral, không chứa text. |
| Clause Classification Adapter | Batch masked clauses tới LLM, validate structured output. | LLM call #1. |
| Legal Corpus Manager | Load/validate corpus, version/effective dates, index và LegalEdge. | Fail fast khi corpus conflict. |
| Baseline Retriever | Label mapping + lexical search tạo seed candidates. | Hoạt động độc lập Data Graph. |
| Data Graph Service | Mở rộng/rank candidates tối đa 1 hop. | Có thể tắt; không sinh citation mới. |
| Risk Analysis Adapter | Risk labels, severity, explanation, citation selection từ candidates. | LLM call #2. |
| Citation Validator | Existence/version/candidate validation; log citation ngoài candidate. | Backend authoritative. |
| Result Assembler | Join theo clause_id với original_text/span, dựng final response. | Không dùng masked text làm quote. |
| Report Exporter | Xuất DOCX/PDF theo khả năng đã chốt. | Không lưu report sau session. |
| LLM Client | Timeout 30s, auto-retry 1, model id bắt buộc, token/cost logging. | Gemini Flash paid tier demo/eval. |
| RunLog / Quota / Rate Limit | Metadata stage/call/token/cost/error; daily quota; rate limit theo IP. | Không log content/PII. |
| Evaluation Harness | Chạy pipeline như thư viện, không đi qua API/session; M1-M8/EV-08. | Dữ liệu dev/test de-identify. |
