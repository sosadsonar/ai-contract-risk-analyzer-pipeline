# ARCHITECTURE.md — Kiến trúc tổng quan & Tech stack

> Nguồn: SDD 0.1 + TDD 0.2 (đối chiếu BRD 0.5, SRS 1.4). Mục đích file: nhìn một lần hiểu hệ thống chia thành gì, dữ liệu đi đâu, chạy ở đâu.
> Hàm/API chi tiết: `SKELETON.md`. Kế hoạch: `PROGRESS.md`. Invariant: `AI_CONTEXT.md` §3.
> Những chỗ **không** có trong tài liệu gốc (đề xuất của file này) được đánh dấu **[Đề xuất]**.

## 1. Nguyên tắc kiến trúc

| # | Nguyên tắc | Hệ quả |
|---|---|---|
| 1 | **Modular monolith**, 1 backend, 1 process | Không microservice, không graph DB; module tách theo trách nhiệm. |
| 2 | **Backend sở hữu sự thật** (span, quote, state, citation) | LLM chỉ trả nhãn/giải thích theo `clause_id`; backend ghép lại. |
| 3 | **Chỉ masked text ra ngoài** | PII mask trước segmentation; trust boundary ở backend. |
| 4 | **Closed corpus** | Citation chỉ từ candidate ∈ kho luật ∈ hiệu lực tại ngày phân tích. |
| 5 | **Không lưu bền vững nội dung hợp đồng** | Session RAM; SQLite chỉ metadata. |
| 6 | **Graph là lớp mở rộng** | Tắt Data Graph/Clause Graph vẫn chạy (demo bắt buộc bật Clause Graph). |
| 7 | **Schema-first, version pin** | Mỗi output ghi model/prompt/taxonomy/corpus/extraction version + commit. |

## 2. Bối cảnh hệ thống & trust boundary

```mermaid
---
config:
  layout: elk
---
%%{init: {"flowchart": {"nodeSpacing": 60, "rankSpacing": 70}}}%%
flowchart TB
  U["Người dùng<br/>Trình duyệt"]

  subgraph BE["Backend tin cậy (1 process, 1 worker)"]
    SHELL["Vỏ web (Web shell)<br/>API, phiên, quota, xuất DOCX"]
    CORE["Lõi phân tích (Analysis core)<br/>che PII, cắt điều khoản,<br/>truy xuất luật, 2 lượt AI, lắp ráp"]
    GATE{{"Cổng gọi LLM duy nhất<br/>chỉ nhận văn bản đã che"}}
    MEM[("Phiên và kết quả<br/>RAM, 60 phút")]
    SQL[("SQLite metadata<br/>không chứa nội dung hợp đồng")]
    COR[("Kho căn cứ pháp lý<br/>chỉ đọc, nạp vào RAM")]
  end

  G["Gemini<br/>(LLM bên ngoài)"]
  EV["Evaluation harness<br/>(ngoại tuyến)"]
  J["Claude judge<br/>(ngoại tuyến)"]

  U -->|"file + vai trò"| SHELL
  SHELL -->|"kết quả cuối + DOCX"| U
  SHELL -->|"giao việc"| CORE
  CORE -->|"final_result đã kiểm tra"| SHELL
  CORE -->|"văn bản đã che"| GATE
  GATE -->|"JSON có cấu trúc từ LLM"| CORE
  GATE <-->|"Lần 1: phân loại"| G
  GATE <-->|"Lần 2: rủi ro"| G
  SHELL <--> MEM
  SHELL <--> SQL
  COR -->|"đọc"| CORE
  EV -.-> CORE
  EV -.-> J

  linkStyle 0,1,2,3 stroke:#c0392b,stroke-width:2px
  linkStyle 4,5,6,7 stroke:#2e7d32,stroke-width:2px

  classDef gate stroke:#2e7d32,stroke-width:3px
  classDef ext stroke:#1565c0
  classDef store stroke:#f9a825
  classDef offline stroke:#6a1b9a,stroke-dasharray:5 5
  class GATE gate
  class G ext
  class MEM,SQL,COR store
  class EV,J offline
```

Chú giải: đường đỏ là dữ liệu gốc (có PII), đường xanh là dữ liệu đã che, nét đứt là ngoại tuyến. Giao diện tạm được phục vụ từ chính backend (cùng origin); hosting chưa chọn.

| Lượt gọi Gemini | Gửi (đã che) | Nhận |
|---|---|---|
| Lần 1: phân loại điều khoản | Các điều khoản theo lô, kèm `clause_id`, không gửi vai trò | 1 đến 3 nhãn clause cho mỗi điều |
| Lần 2: phân tích rủi ro | Điều đích, các điều liên quan, điều luật ứng viên, vai trò | Loại căn cứ, nhãn rủi ro, giải thích, `citation_id`, trạng thái căn cứ, `related_clause_ids` (mức độ do backend tra bảng, không lấy từ LLM) |

| Ranh giới | Được phép đi qua |
|---|---|
| Browser → Backend | File gốc (có PII), qua HTTPS. |
| Backend → Gemini | **Chỉ** masked text + `clause_id` + metadata cần thiết. Không canonical/original/start/end. Không gửi role ở bước classification. |
| Eval → Claude judge | Chỉ dữ liệu đã che/de-identify; judge không nằm trong sản phẩm. |

### 2.1 Pipeline chi tiết (cho dev)

```mermaid
---
config:
  layout: elk
---
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 50}}}%%
flowchart TB
  IN["Request: file + vai trò<br/>(sau cổng nhận: khóa xử lý, quota, tần suất)"]

  subgraph LOC["Giai đoạn cục bộ: VALIDATING"]
    S1["1. UPLOAD<br/>kiểm loại file, dung lượng, số trang<br/>vượt giới hạn: REJECTED"]
    S2["2. EXTRACTION<br/>PDF/DOCX thành canonical_text<br/>NFC, offset theo code point<br/>không đọc được: REJECTED"]
    S3["3. SCOPE_PRECHECK<br/>có phải hợp đồng lao động?<br/>không phải: REJECTED"]
    S4["4. PII_MASKING<br/>che PII, giữ nguyên độ dài<br/>ra: masked_text + pii_spans<br/>lỗi thì dừng"]
    S5["5. SEGMENTATION<br/>cắt điều khoản cục bộ<br/>ra: clauses (id, span, text đã che)<br/>quá 150 điều: REJECTED"]
    S6["6. CLAUSE_GRAPH<br/>cạnh NEXT, PARENT_OF, REFERS_TO"]
    S1 --> S2 --> S3 --> S4 --> S5 --> S6
  end

  subgraph AI["Giai đoạn AI: PROCESSING"]
    S7["7. CLAUSE_CLASSIFICATION<br/>LLM lần 1, lô 20 điều<br/>ra: 1 đến 3 nhãn clause mỗi điều"]
    S8["8. LEGAL_RETRIEVAL<br/>label_map + BM25 chọn seed<br/>mở rộng Data Graph 1 hop<br/>ra: 8 ứng viên mỗi điều"]
    S9["9. RISK_ANALYSIS<br/>gom điều liên quan (Clause Graph)<br/>LLM lần 2, lô 6 điều, theo vai trò<br/>ra: loại căn cứ, nhãn, giải thích, citation"]
    S10["10. CITATION_VALIDATION<br/>citation phải thuộc ứng viên và corpus<br/>hết citation hợp lệ: hạ INSUFFICIENT<br/>kiểm nhãn, loại căn cứ, vai trò<br/>sai: retry 1 lần, vẫn sai: thẻ cần xem xét<br/>tra severity, lọc lời khuyên"]
    S11["11. ASSEMBLY<br/>trích dẫn từ canonical_text, offset highlight<br/>ra: final_result"]
    S7 --> S8 --> S9 --> S10 --> S11
  end

  OUT["COMPLETED<br/>final_result lưu trong phiên (RAM)"]
  EXPORT["EXPORT (theo yêu cầu)<br/>final_result thành DOCX"]

  GW{{"Cổng gọi LLM duy nhất<br/>chỉ nhận văn bản đã che"}}
  GEM["Gemini"]
  COR[("Kho căn cứ pháp lý<br/>chỉ đọc")]
  TAX[("Bảng taxonomy trong mã<br/>nhãn, loại căn cứ, vai trò thành severity")]

  REJ["REJECTED<br/>kết thúc, phải tạo phiên mới"]
  FL["FAILED cục bộ<br/>retry tối đa 2 lần, chạy lại từ EXTRACTION"]
  FA["FAILED AI<br/>retry tối đa 2 lần, resume từ bước AI lỗi"]

  IN --> S1
  S6 --> S7
  S11 --> OUT
  OUT --> EXPORT

  S7 --> GW
  S9 --> GW
  GW <--> GEM
  COR --> S8
  TAX --> S10

  S1 -.-> REJ
  S2 -.-> REJ
  S3 -.-> REJ
  S5 -.-> REJ
  LOC -.->|"lỗi nội bộ"| FL
  AI -.->|"AI_TIMEOUT, AI_PROVIDER_ERROR, AI_OUTPUT_INVALID"| FA
  FL -.->|"retry"| LOC
  FA -.->|"retry"| AI

  classDef raw stroke:#c0392b
  classDef cut stroke:#b8860b
  classDef masked stroke:#2e7d32
  classDef gate stroke:#2e7d32,stroke-width:3px
  classDef store stroke:#f9a825
  classDef ext stroke:#1565c0
  classDef term stroke:#616161
  class S1,S2,S3,S11 raw
  class S4 cut
  class S5,S6,S7,S8,S9,S10 masked
  class GW gate
  class GEM ext
  class COR,TAX store
  class REJ,FL,FA,OUT,EXPORT term
```

Chú giải: đỏ nhạt là bước làm việc trên văn bản gốc, vàng là bước chuyển (che PII), xanh là bước trên văn bản đã che. Bước 11 màu đỏ vì dựng trích dẫn từ canonical text.

### 2.2 Vì sao corpus là file có cấu trúc, không phải vector DB

- Đơn vị lưu là điều luật (nút Khoản, cha là Điều) để citation chính xác đến Điều, Khoản; backend kiểm mọi `citation_id` LLM trả về có nằm trong ứng viên và trong corpus. Cắt đoạn theo cửa sổ cố định sẽ phá khả năng trích dẫn đúng.
- Có phần quan hệ mà vector DB không thay được: hiệu lực theo thời gian (trùng hiệu lực thì dừng khởi động), cạnh REFERS_TO và GUIDES do người phụ trách dữ liệu xác minh tay, PARENT_OF suy từ đường dẫn.
- Dữ liệu nhỏ, chỉ đọc, nạp vào RAM lúc khởi động; BM25 và Data Graph dựng trong RAM từ chính các file này. Không thêm dịch vụ nào cần hosting.
- Tái lập: file text so sánh được trong git, có checksum trong manifest và khóa phiên bản vào kết quả (FR-29).
- Embedding đang tắt (SDD-03). Chỉ cân nhắc khi M8 recall@5 trên D2 không đạt; khi đó giữ JSONL làm nguồn sự thật và thêm một chỉ mục vector dẫn xuất dựng lúc khởi động.

## 3. Thành phần (component)

| Component | Package đích (TDD §3.2) | Trách nhiệm | Gọi LLM? |
|---|---|---|---|
| Web Frontend | `frontend/` **[Đề xuất]** | Upload, chọn role, polling, hiển thị canonical text + highlight, kết quả, export, disclaimer/data notice. Không tự merge AI result, không tự tính span. | — |
| API / Session Controller | `backend/app/api/` | 6 operation, validate request, pre-admission gate, map lỗi → HTTP. Không có logic AI. | — |
| Analysis Orchestrator | `session/orchestrator.py` | **Nơi duy nhất đổi state**; điều phối stage, batch, retry/resume, version pin, error mapping, cancel. | — |
| Session Store / Lease / Cleanup | `session/` | `InMemorySessionStore`, processing lease (capacity=1), TTL cleanup 60s, tombstone. | — |
| Document Processing | `document/` | PDF (PyMuPDF), DOCX (python-docx+lxml), canonicalize NFC, quality gate (gồm legacy-font TCVN3/VNI). | — |
| Scope Precheck | `document/scope_precheck.py` | Luật từ khóa/cấu trúc xác nhận là HĐLĐ. | Không (DEC-11) |
| PII Masker | `privacy/` | Regex + heuristic; placeholder cùng số code point. | Không |
| Clause Segmenter | `clause/segmenter.py`, `structure_parser.py` | Rule cấu trúc + fallback paragraph; backend tính span. | Không (LLM-assist là cut item 3) |
| Clause Graph | `clause/graph_builder.py`, `context_resolver.py` | NEXT/PARENT_OF/REFERS_TO bằng ID; resolve context ≤3 clause/≤6000 code point. | Không |
| Clause Classification Adapter | `ai/clause_adapter.py` | Batch masked clause → 1–3 nhãn. | **LLM #1** |
| Legal Corpus Manager | `legal/corpus_loader.py`, `corpus_validator.py` | Load/validate, hiệu lực, fail-fast `LEGAL_CORPUS_CONFLICT`. | Không |
| Baseline Retriever | `legal/baseline_retriever.py` | label_map + BM25 (`0.70*label + 0.30*bm25`). | Không |
| Data Graph Service | `legal/data_graph.py` | Mở rộng 1 hop quanh top-3 seed, cap, ranking seed-first; có thể tắt/fallback. | Không |
| Risk Analysis Adapter | `ai/risk_adapter.py` | Risk label, basis_type, explanation, chọn citation trong candidate, related_clause_ids; nhận related context; không trả severity (backend tra bảng). | **LLM #2** |
| Citation Validator | `legal/citation_validator.py` | Candidate ⊂ corpus ⊂ hiệu lực; log số bị loại. | Không |
| Result Assembler | `result/assembler.py` | Join `clause_id`; dựng `risk_basis` từ `basis_type`, tra severity; publish nguyên tử. | Không |
| Report Exporter | `result/exporter.py` | DOCX (bắt buộc), PDF (cut item 4); cùng `ReportModel`. | Không |
| LLM Client | `ai/provider.py`, `gemini_client.py` | `LLMProvider`; timeout 30s; retry matrix; ghi call/token/cost; key qua header. | — |
| Ops | `ops/` | RunLog, daily quota + session reserve, IP rate limit (HMAC), metadata SQLite. | — |
| Evaluation Harness | `ai_pipeline/eval/` | M1–M8, privacy, kappa, BL-1; M8 graph on/off; context trace; eval ledger. | Gọi Gemini (pipeline) + Claude (judge) offline |

## 4. Pipeline & state

```text
UPLOAD → EXTRACTION → SCOPE_PRECHECK → PII_MASKING → SEGMENTATION → CLAUSE_GRAPH      ← status VALIDATING
       → CLAUSE_CLASSIFICATION (LLM#1) → LEGAL_RETRIEVAL (baseline + Data Graph)
       → RISK_ANALYSIS (LLM#2 + Clause Graph context) → CITATION_VALIDATION → ASSEMBLY ← status PROCESSING → COMPLETED
```

```mermaid
---
config:
  layout: elk
---
stateDiagram-v2
  [*] --> UPLOADED: Create/Upload được nhận
  UPLOADED --> VALIDATING
  VALIDATING --> PROCESSING: qua kiểm tra cục bộ
  VALIDATING --> REJECTED: file, phạm vi hoặc giới hạn không đạt
  VALIDATING --> FAILED: lỗi nội bộ cục bộ
  PROCESSING --> COMPLETED
  PROCESSING --> FAILED: lỗi AI
  FAILED --> VALIDATING: retry thủ công tối đa 2 lần, lỗi cục bộ
  FAILED --> PROCESSING: retry thủ công tối đa 2 lần, lỗi AI
  VALIDATING --> EXPIRED: End Session, hủy tác vụ, giải phóng slot
  PROCESSING --> EXPIRED: End Session, hủy tác vụ, giải phóng slot
  COMPLETED --> EXPIRED: hết 60 phút hoặc End Session
  FAILED --> EXPIRED
  REJECTED --> EXPIRED
  EXPIRED --> [*]
  note right of REJECTED
    Kết thúc. Phải tạo phiên mới.
  end note
  note right of FAILED
    Không giữ slot xử lý.
  end note
```

- Retry: `try_acquire(lease)` → mới `manual_retry_count += 1`; bận → `409 SYSTEM_BUSY`, không tăng counter. Resume chỉ ở giai đoạn AI, so khớp bộ version pin lưu trong phiên (giai đoạn VALIDATING luôn chạy lại từ EXTRACTION); cut item 2 → chạy lại giai đoạn PROCESSING từ đầu nhưng vẫn giới hạn 2 lần.
- Data Graph lỗi runtime → fallback baseline (`graph_fallback=true` trong RunLog), **không** fail phiên.
- Graph không thêm LLM call. Số call/hợp đồng ≈ `ceil(n/20) + ceil(n/6)` trước retry (40–60 clause ≈ 9–13 call).

## 5. Kiến trúc dữ liệu

| Dữ liệu | Nơi | Vòng đời |
|---|---|---|
| File gốc | Temp dir ngẫu nhiên theo session (chỉ khi parser cần path) | Xóa khi cleanup/end |
| canonical/masked text, clauses, Clause Graph, AI output, `pii_spans` (start/end/type) | `InMemorySessionStore` | TTL 60' không hoạt động hoặc End Session; restart = mất |
| RunLog, usage/quota, rate counter (key IP = HMAC-SHA256 có salt), EXPIRED tombstone (24h) | SQLite (`sqlite3`) | Metadata thuần, **cấm** nội dung/PII |
| Legal corpus + edges + label_map + taxonomy/rubric | `data/` (file versioned, **[Đề xuất theo quyết định nhóm]** repo riêng của Người 2, gắn bằng git submodule) | Load lúc startup; cập nhật không sửa code |
| Eval artifacts (gold, run output, `eval_cost_ledger`) | `ai_pipeline/eval/` | Không bị session cleanup xóa; dữ liệu đã de-identify |
| Polling Get Status | không cập nhật `last_activity_at` | Result/Retry/Export/End/Create thì có |

## 6. Hai đồ thị

| | **Data Graph** (BR-17, FR-30) | **Clause Graph** (BR-18, FR-31) |
|---|---|---|
| Mục đích | Retrieval & fact-finding: mở rộng/xếp hạng candidate | Validation & reasoning: điều kiện/phụ thuộc/mâu thuẫn |
| Nút | `LegalProvision` (`citation_id`) | `clause_id` |
| Cạnh | `PARENT_OF` (AUTO, từ `parent_path`); `REFERS_TO`, `GUIDES` (MANUAL, đã xác minh) | `NEXT`, `PARENT_OF`, `REFERS_TO` (chỉ dẫn chiếu nội bộ, resolve duy nhất) |
| Nguồn cạnh | `edges.jsonl` (verified); `edge_suggestions.jsonl` **không load** | Dựng local từ segmentation + regex tham chiếu |
| Mở rộng | 1 hop; ≤4 neighbor/seed, ≤2 child/seed; `graph_score = 0.60*seed.score + edge_bonus(REFERS_TO .30, GUIDES .25, PARENT_OF .15) + direction_bonus(.05)` | Ưu tiên REFERS_TO → PARENT_OF → NEXT; ≤3 clause, ≤6000 code point |
| Kết quả | Cùng `final_k=8` cho graph on/off (EV-08/M8 công bằng) | Masked related context vào Risk request; `ContextResolutionTrace` (ID-only, dev/eval) |
| Bật/tắt | `DATA_GRAPH_ENABLED` | `CLAUSE_GRAPH_ENABLED` (demo bắt buộc true) |
| Vòng đời | Process-wide, build lúc startup | Theo session, xóa cùng phiên |
| Cắt khi trễ (cut 5) | Bỏ `REFERS_TO`/`GUIDES`, giữ cấu trúc | Bỏ `REFERS_TO`, giữ cấu trúc |

Loại trừ dẫn chiếu pháp luật khỏi `REFERS_TO` (Clause Graph): không tạo cạnh nếu ngữ cảnh có `Bộ luật`, `Luật`, `Nghị định`, `Thông tư`, `văn bản pháp luật` hoặc dạng `Điều 26 (của) Bộ luật…`; mơ hồ → bỏ cạnh + diagnostic.

## 7. Tích hợp LLM

- `LLMProvider` (Protocol): `generate_structured(model_id, messages, response_schema, timeout_s)`.
- `GeminiProductClient`: demo/eval, **paid tier**, model id bắt buộc, `response_schema`, temperature 0.0, key qua header. `DevLocalClient`/Gemini free: chỉ `APP_ENV=dev` và dữ liệu de-identify.
- Retry: timeout/network, 429 (backoff+jitter), 5xx, schema-invalid → tối đa 1; 400/401/403 → không. Mỗi *actual request* tăng counter/cost.
- Risk request dùng **candidate catalog** chung (không lặp full text điều luật mỗi item); `candidate_ids` theo thứ tự từng item.
- Sau LLM#2: lint advice theo cụm ("bạn nên", "NLĐ nên", "nên sửa/bổ sung/thương lượng"…, **không** match từ "nên" đơn lẻ) + lint tham chiếu pháp luật ngoài citation → retry ≤1 → xóa câu vi phạm → rỗng thì `AI_OUTPUT_INVALID`.

## 8. Runtime & triển khai

- **1 Uvicorn worker**, không autoscale/serverless (session + lease là process-local). Smoke test fail nếu demo profile cấu hình >1 worker.
- CPU nặng (PyMuPDF, DOCX/OOXML, regex) trong threadpool có giới hạn; `GET status` vẫn ≤2s.
- Startup (fail-fast): load config → taxonomy/rubric → corpus + validate (overlap hiệu lực, endpoint cạnh, PARENT_OF acyclic) → BM25 + label_map + Data Graph → SQLite → Session store + lease + cleanup → threadpool → `readiness=true`.
- Hosting: 1 web frontend + 1 backend service, có HTTPS, temp storage, đọc được corpus. Hiện chạy localhost, chưa chọn nhà cung cấp hosting (SDD không khóa); giao diện tạm phục vụ từ chính backend (cùng origin).
- Hiệu năng mục tiêu: 90% run (PDF ≤15 trang hoặc DOCX ≤50.000 ký tự) ≤120s; UI thấy VALIDATING/PROCESSING ≤2s. Không cam kết 120s cho input tối đa 150 clause. Benchmark D1 (p50/p90 từng stage) trước MS-2.
- Chi phí: $20 = $5 vận hành + $15 đánh giá; `DAILY_LLM_CALL_QUOTA`, `SESSION_CALL_RESERVE` (= p95 planned calls) chốt từ đo D1; IP limit mặc định 5 upload/10'.

## 9. Bảo mật & riêng tư (tóm tắt)

HTTPS · session_id UUIDv4 opaque, tra cứu chính xác (có test âm) · hard byte cap + sniff type + temp dir ngẫu nhiên + sanitize tên file · secrets qua ENV/header, không log · outbound capture test (không PII/canonical) · quét log tự động tìm PII · audit DB/temp/restart không có nội dung · demo không mật khẩu. PII auto-mask không đạt 100% → thông báo không cam kết tuyệt đối (BRD Phụ lục A). Chưa xác nhận văn bản pháp luật bảo vệ dữ liệu cá nhân khi gửi ra nước ngoài (BRD OI-03).

## 10. Tech stack

| Lớp | Công nghệ | Ghi chú |
|---|---|---|
| Runtime | Python 3.12 | Chung cho `backend/` và `ai_pipeline/` |
| HTTP | FastAPI + Uvicorn (1 worker) | multipart upload, streaming export |
| Schema | Pydantic v2 + JSON Schema | `schemas/*.json` versioned; sinh enum từ code hoặc test đối chiếu |
| PDF | PyMuPDF | reading order, header/footer, bảng, 2 cột |
| DOCX | python-docx + lxml (OOXML) | numbering, tracked changes, textbox |
| Unicode | `unicodedata` (NFC) | offset = code point |
| Lexical retrieval | `rank-bm25` | deterministic, local; embedding **tắt** mặc định |
| Graph | dict/list adjacency in-memory | 1 hop |
| Metadata | `sqlite3` (stdlib) | RunLog/quota/rate/tombstone |
| LLM sản phẩm | Gemini Flash (paid), model id cấu hình tường minh | structured output |
| LLM judge | Claude (offline, chỉ đánh giá) | model cụ thể: BRD OI-11 |
| Export | python-docx (DOCX trước); PDF renderer tùy môi trường | font hỗ trợ tiếng Việt |
| Test | pytest + pytest-asyncio | unit/contract/integration/E2E mock/provider smoke/eval |
| Eval | Python CLI + JSON/CSV | `python -m ai_pipeline.evaluation.runner …` |
| Frontend | React + TypeScript + Vite (đã có trong `frontend/`), desktop (Chrome/Edge/Firefox) | Contract bắt buộc ở TDD §5.9 (polling, code point→UTF-16, catalog thông báo) |
| Loại bỏ | PostgreSQL/SQLAlchemy/Alembic (cho nội dung hợp đồng), Qwen/Ollama ở product path, Gemini free ở demo/eval | DEC-16, DEC-19 |

## 11. Cấu trúc repository đích

```text
backend/app/{main.py, pipeline.py (analyze(): chuỗi stage dùng chung cho orchestrator và harness), api/, core/, domain/, session/, document/, privacy/, clause/, ai/, legal/, result/, ops/, integrations/ (risk_assembler.py)}
ai_pipeline/{schemas/, eval/ (runner, metrics, gold), services/ (legacy, xóa khi C-01 xong), data/ (submodule dữ liệu và corpus)}
ai_pipeline/data/{legal_corpus/{manifest.yaml, provisions.jsonl, edges.jsonl, edge_suggestions.jsonl, label_map.yaml},
      docs/{clause_taxonomy/, risk_taxonomy/, severity_rubric/}}
frontend/
tests/{unit/, integration/, contract/, fixtures/}
docs/                          # BRD, SRS, SDD, TDD (gốc)  →  docs/splitted_docs/ (sinh bằng scripts/split_doc.py)
scripts/split_doc.py           # tách tài liệu cho AI đọc đỡ token
```

## 12. Quyết định kiến trúc chính (rút gọn; đầy đủ: TDD-01…TDD-25, SRS DEC-01…DEC-28)

Rule-based segmentation, bỏ router theo tỉ lệ heading (DEC-18/TDD-06) · Upload bất đồng bộ, REJECTED luôn gắn session (DEC-23) · `risk_basis` dựng từ `basis_type` của LLM, severity tra bảng (DEC-24/TDD-23) · lease capacity=1, retry acquire lại (DEC-25) · span code point, partition không chồng (DEC-26/TDD-22) · EV-08 cùng `final_k`, M8 chính dùng predicted labels (DEC-27/TDD-10) · 1 worker (DEC-28/TDD-21) · không lưu nội dung bền vững (DEC-16/TDD-02) · Gemini paid cho demo/eval (DEC-19/TDD-25).

## 13. Rủi ro kiến trúc → biện pháp

| Rủi ro | Biện pháp |
|---|---|
| Latency/chi phí LLM | Batching, candidate catalog dedupe, token budget, quota + reserve, benchmark D1 |
| Mất span do mask/segment | Placeholder cùng độ dài, `boundary_guard`, partition, M4=100%, fixture non-BMP |
| Graph làm phình việc kho luật | Graph là lớp tắt được; cạnh cấu trúc tự sinh; `REFERS_TO`/`GUIDES` là cut 5 |
| Session RAM mất khi restart / không scale | Chấp nhận cho demo; 1 worker; nếu cần nhiều worker phải đổi SDD/TDD sang store dùng chung |
| PII local không đạt recall | Đo D1 sớm; thêm local NER **chỉ** nếu BRD §7.3 không đạt (SRS OI-12) |
| Kho luật sai/lỗi thời, không có luật sư | Closed corpus, effectivity, disclaimer, verified edges, báo cáo nêu giới hạn |
| Codebase cũ lệch tài liệu | Schema-first + mock mới trước; migration M0→M6 (`PROGRESS.md`) |
