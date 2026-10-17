<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 4. Configuration, secret và startup | 3174 ký tự | trước: 04_3-stack-trien-khai-va-cau-truc-repository.md | sau: 06_5-http-api-contract.md -->

# 4. Configuration, secret và startup

## 4.1 Biến cấu hình

| Tên | Kiểu | Default | Ghi chú |
|---|---|---|---|
| APP_ENV | `dev`, `demo`, `eval` | dev | `eval` bypass runtime quota/rate-limit, nhưng ghi eval cost ledger. |
| GEMINI_API_KEY | secret | - | Bắt buộc ở demo/eval; không log. |
| GEMINI_MODEL_ID | string | - | Bắt buộc ở demo/eval; startup fail nếu thiếu. |
| DEV_LLM_PROVIDER | `gemini` or `local` | gemini | `local` chỉ ở dev với dữ liệu de-identified. |
| LLM_TIMEOUT_SECONDS | int | 30 | Theo NFR-REL-02. |
| LLM_AUTO_RETRY | int | 1 | Không vượt 1. |
| CLAUSE_BATCH_SIZE | int | 20 | Tune D1. |
| RISK_BATCH_SIZE | int | 6 | Tune D1. |
| LLM_PARALLELISM | int | 2 | Trong một session; benchmark D1. |
| MAX_PDF_PAGES | int | 30 | FR-04. |
| MAX_UPLOAD_MB | int | 10 | FR-04. |
| MAX_DOCX_CHARS | int | 100000 | FR-04. |
| MAX_CLAUSES | int | 150 | FR-09. |
| SESSION_TTL_MINUTES | int | 60 | FR-23. |
| EXPIRED_TOMBSTONE_HOURS | int | 24 | TDD-15. |
| DAILY_LLM_CALL_QUOTA | int | **required in demo** | Chốt từ D1 + cost model; không dùng default 120. |
| SESSION_CALL_RESERVE | int | **required in demo** | p95 planned calls/contract trên D1, dùng admission control. |
| RATE_LIMIT_UPLOADS | int | 5 | Default, tune trước demo. |
| RATE_LIMIT_WINDOW_SECONDS | int | 600 | 10 phút. |
| DATA_GRAPH_ENABLED | bool | true | EV-08 chạy true/false. |
| CLAUSE_GRAPH_ENABLED | bool | true | Demo bắt buộc true; false chỉ dev/eval/test. |
| RETRIEVAL_SEED_K | int | 3 | Top baseline seeds để mở rộng graph. |
| RETRIEVAL_FINAL_K | int | 8 | Cả graph on/off đều trả tối đa 8. |
| GRAPH_MAX_NEIGHBORS_PER_SEED | int | 4 | Chống fan-out. |
| GRAPH_MAX_CHILDREN_PER_SEED | int | 2 | Cap PARENT_OF child expansion. |
| CLAUSE_GRAPH_MAX_RELATED | int | 3 | TDD-07. |
| CLAUSE_GRAPH_MAX_CONTEXT_CHARS | int | 6000 | Unicode code point. |
| SCOPE_TITLE_SCAN_CHARS | int | 1000 | Strong-title chỉ tính ở vùng đầu. |
| TEMPERATURE | float | 0.0 | Cố định/reproducible. |

## 4.2 Startup sequence

1. Load config; validate numeric limits. Ở `demo/eval`, thiếu Gemini model/key hoặc daily quota/session reserve thì startup fail. Ở `dev`, local provider chỉ được phép với dữ liệu de-identified.
2. Load clause taxonomy, risk taxonomy (gồm `basis_type`), severity rubric; validate version metadata.
3. Load legal corpus manifest/provisions/edges; validate citation IDs, version overlap, edge endpoints, PARENT_OF acyclic.
4. Build BM25 index + weighted label map; build Data Graph adjacency index nếu enabled.
5. Open operational metadata SQLite; migration chỉ cho metadata.
6. Khởi tạo InMemorySessionStore, cleanup scheduler và non-blocking global processing lease capacity=1.
7. Khởi tạo threadpool cho PyMuPDF/DOCX parsing, regex/CPU-heavy local preprocessing.
8. Chỉ expose readiness=true sau khi thành công. `LEGAL_CORPUS_CONFLICT` làm service fail-fast.

## 4.3 Deployment constraint

Demo chạy **một Uvicorn worker/process duy nhất**. Không dùng multiple worker, autoscale hoặc serverless scale-out vì session store và processing lease là in-memory/process-local. Nếu sau này cần nhiều worker thì phải đổi SDD/TDD sang shared session/lock store; ngoài phạm vi demo.
