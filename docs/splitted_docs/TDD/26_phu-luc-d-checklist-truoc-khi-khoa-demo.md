<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: Phụ lục D. Checklist trước khi khóa demo | 1411 ký tự | trước: 25_phu-luc-c-prompt-contract.md | sau: 27_phu-luc-e-catalog-thong-bao-ui-toi-thieu.md -->

# Phụ lục D. Checklist trước khi khóa demo

| Hạng mục | Điều kiện |
|---|---|
| Schema | clause_output_v3/risk_output_v1/final_result_v1 pass; risk_basis derive đúng. |
| Privacy | BRD 7.3 đạt; outbound no raw PII; placeholder same length. |
| Span | M4=100%; non-overlap partition; Unicode code-point offset; browser non-BMP test. |
| Corpus | Build legal corpus/Data Graph pass; suggestions chưa verify không load. |
| Graph | M8 graph on/off same final_k; Clause Graph build/cleanup/context trace đúng. |
| LLM | Explicit Gemini model, response schema, timeout 30s, retry matrix, token/cost log. |
| State | Async REJECTED, lease race, local/process retry target, retry limit pass. |
| Performance | D1 p50/p90 đo và NFR-PERF-01/NFR-PERF-02 có evidence. |
| Cost | DAILY_LLM_CALL_QUOTA + SESSION_CALL_RESERVE chốt từ D1/cost model; eval ledger riêng. |
| Deployment | 1 worker, no autoscale/serverless; CPU-heavy local work dùng threadpool. |
| No persistence | Restart xóa session content; ops DB/log no contract content. |
| Export | DOCX đủ quote, risk/basis, disclaimer, **data notice**, citation; PDF nếu enabled. |
| Frontend | Polling <=2s status visibility; no-risk/insufficient/error catalog/highlight rules pass. |
| Eval | M1-M8 + privacy + annotation kappa + BL-1(if enabled); M8 primary dùng predicted labels. |
| Locked test | T1/T2 run ghi commit/version pins; không tuning sau test result. |
