# SKELETON.md — Hàm, API và cách chúng tương tác

> Nguồn: TDD 0.2 (chính), SRS 1.4 (FR/Phụ lục C), SDD 0.1, BRD 0.5. Mục đích: biết **module nào, hàm nào, gọi ai, trả gì, lỗi gì** trước khi viết code.
> Đọc kèm: `AI_CONTEXT.md` (invariant), `ARCHITECTURE.md` (kiến trúc), `PROGRESS.md` (ai làm gì, tuần nào).

## 0. Quy ước đánh dấu — đọc trước

| Dấu | Nghĩa |
|---|---|
| **[TDD]** | Tên file/module/hàm/field có trong TDD 0.2. Đổi phải sửa TDD. |
| **[Đề xuất]** | Chữ ký hàm do file này đề xuất để team thống nhất. TDD chỉ khóa **tên file + hợp đồng dữ liệu**, **không** khóa chữ ký hàm (trừ `mask_value`, `canonicalize`, `boundary_guard`, `resolve_context`, `generate_structured`, `try_acquire`). Có thể đổi, nhưng đổi thì sửa file này cùng PR. |
| **[Cũ]** | Thứ đang có trong codebase snapshot 12/10/2026, **chỉ biết qua mô tả ở SRS Phụ lục C (C-01…C-21)**. Chưa đối chiếu với mã thật; tên hàm ngoài `segment/classify/_locate_span/document_router` là chưa kiểm chứng. |

Nguyên tắc chung: stage module là **hàm thuần** (không import `api/`, `session/`); chỉ `session/orchestrator.py` đổi state; lỗi dùng typed exception (§8); offset luôn là Unicode code point sau NFC.

---

## 1. Bản đồ tương tác

```text
Browser (frontend/)
   │  HTTP /api/v1  (polling status)
   ▼
api/routes/sessions.py ──► admission_gate ──► ops.rate_limit ─► ops.quota ─► session.lock.try_acquire
   │                                   (fail ⇒ KHÔNG tạo session)
   ├──► session.store (InMemorySessionStore)  ◄───────────────┐
   └──► session.orchestrator  (NƠI DUY NHẤT đổi state) ───────┘
            │  VALIDATING
            ├─► document.extractor ─► canonicalizer ─► quality ─► scope_precheck
            ├─► privacy.masker (detector)                      ─► pii_spans, masked_text
            ├─► clause.segmenter (structure_parser, boundary_guard) ─► clauses[]
            ├─► clause.graph_builder                           ─► ClauseGraph (chỉ ID)
            │  PROCESSING
            ├─► ai.clause_adapter ─► ai.provider (Gemini)      ─► LLM #1
            ├─► legal.baseline_retriever ─► legal.data_graph   ─► candidates (≤ final_k)
            ├─► clause.context_resolver ─► ai.risk_adapter ─► ai.provider ─► LLM #2
            ├─► legal.citation_validator
            └─► result.assembler ─► (publish nguyên tử) COMPLETED
                                      └─► result.exporter (khi gọi /export)
Mọi actual LLM request ─► ops.quota (tăng counter TRƯỚC call) + ops.runlog (cost) 
Eval harness (ai_pipeline/evaluation) gọi trực tiếp các module trên, không qua HTTP/quota.
```

Quy tắc phụ thuộc: `api → session → {document, privacy, clause, ai, legal, result, ops}`; các stage module **không** gọi ngược lên `session/`; `domain/`, `core/` là lá, ai cũng import được.

---

## 2. Ánh xạ codebase cũ → mới (SRS Phụ lục C)

> Chưa thấy mã thật — cột "Hành động" suy ra từ C-xx. Khi mở file cũ, nếu thực tế khác mô tả → ghi vào `PROGRESS.md` §Nhật ký, đừng sửa bảng này ngầm.

| File / thứ đang có [Cũ] | Hành động | Đích | C-xx |
|---|---|---|---|
| `ai_pipeline/services/clause_extraction_service.py` (1 prompt LLM cắt + phân loại trên text chưa che; `_locate_span` dùng `str.find`) | **Tách đôi**; xóa `_locate_span`; giữ cách sinh prompt từ `LABEL_DEFINITIONS` | `clause/segmenter.py` (`segment`) + `ai/clause_adapter.py` (`classify`) + `ai/prompts/clause_v1.py` | C-01 |
| `utils/text_processing.py` (`document_router` theo tỉ lệ heading, regex chỉ trả dòng tiêu đề) | **Bỏ router**; regex trả khoảng điều khoản; thêm fallback paragraph | `clause/structure_parser.py` | C-02 |
| `config/labeling.py` (`type_scores`, `max_content_risk_tier`, `review_zone`; 2 import hỏng `config.risk_routing`) | **Xóa** 3 khái niệm + 2 import; chỉ còn validate 1–3 nhãn, thuộc taxonomy, không trùng | `clause/taxonomy.py` + `core/enums.py` (một nguồn, DEC-20) | C-03 |
| `schemas/clause_output_v2.json` (`contract_id` bắt buộc; `taxonomy_version` cố định v02 trong khi code đã v04; enum chép tay) | **Thay** | `ai_pipeline/schemas/clause_output_v3.json`, `risk_output_v2.json`, `final_result_v1.json`, … (enum sinh từ code hoặc có test đối chiếu) | C-04 |
| Backend Postgres + SQLAlchemy + Alembic, bảng `contracts` lưu `original_text`, id số nguyên, status chữ thường | **Gỡ** cho nội dung hợp đồng | `session/store.py` (RAM), `ops/metadata_db.py` (sqlite metadata) | C-05 |
| `backend/app/api/routes/contracts.py` (chỉ `.pdf`, không role, `HTTPException` tự do) | **Viết lại** | `api/routes/sessions.py` + `api/errors.py` + `api/deps.py` | C-06 |
| `backend/app/services/llm_clients.py` (free tier + Qwen/Ollama, timeout 60/120s, key trong query string, model ngầm) | **Viết lại** | `ai/provider.py`, `ai/gemini_client.py`, `ai/dev_local_client.py` | C-07 |
| `backend/app/services/document_service.py` (`page.get_text()` nối newline) | **Viết lại** | `document/{extractor,pdf_extractor,docx_extractor,canonicalizer,quality}.py` | C-08 |
| `backend/app/integrations/{clause_ai,risk_ai,explanation_ai}` (3 adapter rỗng) | Giữ 2, **xóa `explanation_ai`** (explanation nằm trong LLM #2) | `ai/clause_adapter.py`, `ai/risk_adapter.py`; sửa `backend_architecture.md` | C-11 |
| `mock_clause_service.py` (schema cũ) | **Viết lại theo schema mới** | `tests/` mock API/pipeline | C-17 |
| `test_pipeline.py`, `test_llm_pipeline.py` (script chạy tay; `pyproject` trỏ `tests/` chưa có) | **Chuyển pytest** | `tests/{unit,integration,contract}/` | C-17 |
| `eval/eval_segmentation.py` (M1: IoU 0.80, ghép tham lam) | **Giữ M1**, chuyển chỗ | `ai_pipeline/evaluation/metrics/segmentation.py` + `runner.py` | C-18 |
| `docs/CLAUSE_TAXONOMY.md`, `docs/DATA_PLAN.md`, `README.md`, `CONTRIBUTING.md`, `backend/text_extraction_contract.md` | Thay bằng con trỏ về BRD; sửa contract cho khớp SRS | — | C-19 |
| `pyproject.toml` (thiếu deps backend) | Gộp nguồn deps, thêm lib DOCX/export | — | C-20 |
| **Chưa có**: DOCX, scope precheck, PII masking, kho luật/retrieval, Data Graph, Clause Graph, risk/citation/assembly, export, RunLog/quota/rate, frontend | **Viết mới** | xem §5 | C-09, 10, 12–16, 21 |

> **Cập nhật 20/10/2026 (Người 1, T1):** C-03 và C-04 đã xong — `ai_pipeline/config/{taxonomy,labeling}.py` đã bị xóa; nguồn nhãn nay ở `backend/app/clause/taxonomy.py` (+ `validate_labels`) và `backend/app/core/enums.py`; schema `ai_pipeline/schemas/clause_output_v3.json` thay `clause_output_v2.json`. Với `clause_extraction_service.py`, mô tả [Cũ] ở hàng C-01 đã được đối chiếu với mã thật — chênh lệch ghi ở `PROGRESS.md` §9 (bảng trên giữ nguyên để truy vết).

---

## 3. HTTP API — 6 operation (TDD §5)

Base `/api/v1`. JSON UTF-8. Lỗi: `{"error":{"code","message"(vi),"retryable","details?"}}`. `session_id` = UUIDv4 opaque, tra cứu chính xác.

| # | Operation | Handler [Đề xuất] | Hành vi chính | Thành công | Lỗi |
|---|---|---|---|---|---|
| 1 | `POST /sessions` (multipart `role`, `file`) | `create_session` | `admission_gate(role, ip)` → tạo session `UPLOADED` → nhận file với hard byte cap → `schedule(orchestrator.run)` → trả nhanh | `201 {session_id,status:UPLOADED,created_at}` | Không tạo session: `ROLE_REQUIRED 400`, `RATE_LIMITED 429`, `QUOTA_EXCEEDED 429`, `SYSTEM_BUSY 409` |
| 2 | `GET /sessions/{id}/status` | `get_status` | Đọc state; **không** cập nhật `last_activity_at` | `200 {status, stage, manual_retry_count, progress{completed_units,total_units}, error_code, updated_at}` | `404 SESSION_NOT_FOUND`; EXPIRED còn tombstone → `200 status=EXPIRED` |
| 3 | `GET /sessions/{id}/result` | `get_result` | Chỉ COMPLETED; **touch** activity | `200 final_result_v1` | `SESSION_NOT_READY`, `SESSION_REJECTED`, `SESSION_EXPIRED 410` |
| 4 | `POST /sessions/{id}/retry` | `retry_session` | Chỉ FAILED và `manual_retry_count<2`; `try_acquire` lease **trước** khi tăng counter | `200/202` trạng thái mới (VALIDATING hoặc PROCESSING theo `failed_stage`) | `409 INVALID_SESSION_STATE`, `409 SYSTEM_BUSY` (counter không tăng), `RETRY_LIMIT_EXCEEDED` (lần 3) |
| 5 | `GET /sessions/{id}/export?format=docx\|pdf` | `export_session` | Chỉ COMPLETED; build in-memory, stream, xóa trong `finally`; touch | file | `501 FEATURE_NOT_ENABLED` (nếu PDF bị cắt), + 3 mã API-state như (3) |
| 6 | `DELETE /sessions/{id}` | `end_session` | Idempotent: cancel task, cleanup, release lease nếu sở hữu, ghi tombstone; touch | `200 {session_id,status:EXPIRED,message}` | `404 SESSION_NOT_FOUND` chỉ khi không có session lẫn tombstone |

Ghi chú tương tác:
- **Lỗi file sau khi 201** (sai loại, quá lớn, quá trang/ký tự, không có text, encoding hỏng, không phải HĐLĐ, quá 150 clause) là **REJECTED của session**, client đọc `error_code` qua `get_status` — **không** trả đồng bộ từ POST.
- Polling: bắt đầu sau 500 ms, mỗi 1,5 s khi VALIDATING/PROCESSING (sau 60 s có thể 2,5 s). Dừng ở COMPLETED/FAILED/REJECTED/EXPIRED.
- **[Đề xuất — cần lưu ý khi code]** FastAPI/Starlette đã parse multipart (spool ra đĩa/RAM) *trước* khi vào handler, nên "hard byte cap" không tự có. Cần kiểm `Content-Length` + middleware/streaming reader dừng khi vượt 10MB, rồi map sang `REJECTED/FILE_TOO_LARGE`. Cần chốt cách làm ở tuần 2 và có test biên.
- Race bắt buộc có test: 2 Create đồng thời chỉ 1 acquire lease; Retry khi phiên khác chạy → `SYSTEM_BUSY` không tăng counter; End Session vs callback provider muộn không "hồi sinh" session (TDD §7.5).

---

## 4. Domain types (TDD §6) — dạng rút gọn

```python
# core/enums.py  [TDD §6.1]  — MỘT nguồn, không chép enum ở chỗ khác
class Role(str, Enum):           EMPLOYEE; EMPLOYER
class SessionStatus(str, Enum):  UPLOADED; VALIDATING; REJECTED; PROCESSING; COMPLETED; FAILED; EXPIRED
class Stage(str, Enum):          UPLOAD; EXTRACTION; SCOPE_PRECHECK; PII_MASKING; SEGMENTATION; CLAUSE_GRAPH; \
                                 CLAUSE_CLASSIFICATION; LEGAL_RETRIEVAL; RISK_ANALYSIS; CITATION_VALIDATION; ASSEMBLY; EXPORT
class Severity(str, Enum):       HIGH; MEDIUM; LOW            # None = thiếu căn cứ
class EvidenceStatus(str, Enum): SUPPORTED; INSUFFICIENT_EVIDENCE
class BasisType(str, Enum):      LEGAL_VIOLATION; UNFAVORABLE; AMBIGUOUS
class LegalEdgeType(str, Enum):  PARENT_OF; REFERS_TO; GUIDES
class ClauseEdgeType(str, Enum): NEXT; PARENT_OF; REFERS_TO
```

```python
# domain/models.py  [TDD §6.2–6.4]
@dataclass class PiiSpan:        type: PiiType; start: int; end: int          # KHÔNG có giá trị gốc
@dataclass class Clause:         clause_id: str; original_text: str; start_char: int; end_char: int
                                 clause_labels: list[str]                       # 1..3, điền sau LLM #1
@dataclass class ClauseStructure: level: int; number: str | None; parent_clause_id: str | None   # metadata local, không ra API
@dataclass class ClauseEdge:     src: str; dst: str; edge_type: ClauseEdgeType  # chỉ ID
@dataclass class ClauseGraph:    node_ids: list[str]; edges: list[ClauseEdge]   # KHÔNG chứa text
@dataclass class LegalProvision: citation_id: str; document_id: str; document_name: str; version: str
                                 article: str | None; clause: str | None; point: str | None
                                 parent_path: list[str]; content: str; effective_from: date; effective_to: date | None
@dataclass class LegalCandidate: citation_id: str; content: str; document_name: str; article: str | None
                                 version: str; effective_from: date; effective_to: date | None
                                 origin: str      # SEED_LABEL|SEED_LEXICAL|BASELINE_BACKUP|GRAPH_PARENT_OF|GRAPH_REFERS_TO|GRAPH_GUIDES
                                 rank: int
@dataclass class RiskResult:     clause_id: str; role: Role; risk_labels: list[str]
                                 risk_basis: list[dict]        # BACKEND dựng từ basis_type (LLM trả) + risk_labels
                                 severity: Severity | None; explanation: str
                                 evidence_status: EvidenceStatus; citation_ids: list[str]; version_pins: VersionPins
@dataclass class StageArtifact:  stage: Stage; status: str; output: Any; fingerprint: str
@dataclass class ErrorInfo:      code: str; stage: Stage | None; retryable: bool
@dataclass class VersionPins:    extraction_version; clause_taxonomy_version; risk_taxonomy_version; severity_rubric_version
                                 corpus_version; data_graph_version; clause_prompt_version; risk_prompt_version
                                 model_id; temperature; app_commit
```

`Session` (aggregate, chỉ ở RAM): `session_id, role, status, current_stage, failed_stage, created_at, last_activity_at, manual_retry_count, filename, analysis_date, extraction_version, canonical_text, masked_text, pii_spans, clauses, clause_graph, clause_classification_outputs, legal_candidates, risk_results, version_pins, stage_cache, last_error, active_tasks`.

Schema stage bắt buộc (`ai_pipeline/schemas/`): `extraction_v1`, `masking_v1`, `segmentation_v1`, `clause_output_v3`, `retrieval_v1`, `risk_output_v2`, `final_result_v1` — mỗi cái có `schema_version`.

---

## 5. Skeleton theo package

Mỗi khối: **vai trò**, rồi chữ ký. `# gọi bởi` / `# raise` ghi tương tác. Tất cả `[Đề xuất]` trừ khi có `[TDD]`.

### 5.1 `core/` và `domain/`

```python
# core/config.py   — Pydantic Settings, biến ở TDD §4.1 / Phụ lục B
class Settings(BaseSettings): ...                    # APP_ENV, GEMINI_*, *_BATCH_SIZE, MAX_*, *_K, DATA_GRAPH_ENABLED ...
def load_settings() -> Settings
def validate_for_env(s: Settings) -> None            # demo/eval thiếu GEMINI_MODEL_ID/KEY, DAILY_LLM_CALL_QUOTA,
                                                     # SESSION_CALL_RESERVE ⇒ fail startup; demo >1 worker ⇒ fail

# core/clock.py
def today() -> date                                  # analysis_date (inject được để test hiệu lực)
def now() -> datetime

# core/security.py
def ip_hash(ip: str, salt: str) -> str               # HMAC-SHA256(salt, ip) cắt ngắn; IP thô chỉ ở request context
def sanitize_display_filename(name: str) -> str      # log chỉ extension + size nếu tên có PII

# domain/errors.py  [TDD §7.2]
class ValidationReject(Exception): code: str         # → REJECTED
class AiTimeout(Exception); class AiProviderError(Exception); class AiOutputInvalid(Exception)   # → FAILED
class PipelineInternalError(Exception)               # → FAILED / INTERNAL_ERROR
class LegalCorpusConflict(Exception)                 # → fail-fast lúc startup
```

### 5.2 `api/`

```python
# api/routes/sessions.py   (prefix /api/v1)
async def create_session(role: Role | None = Form(None), file: UploadFile = File(...), request: Request) -> CreateResponse
async def get_status(session_id: UUID) -> StatusResponse
async def get_result(session_id: UUID) -> FinalResult
async def retry_session(session_id: UUID) -> StatusResponse
async def export_session(session_id: UUID, format: Literal["docx","pdf"]) -> StreamingResponse
async def end_session(session_id: UUID) -> EndResponse

# api/deps.py
def get_orchestrator() -> AnalysisOrchestrator ; def get_store() -> InMemorySessionStore ; def client_ip(req) -> str

# api/errors.py
class ApiError(Exception): code; http_status; retryable; details
def register_exception_handlers(app) -> None         # ApiError → ErrorResponse; mọi message tiếng Việt (TDD Phụ lục E)
```
`admission_gate` (gọi trong `create_session`, thứ tự cố định — TDD §5.2):
```python
async def admission_gate(role, ip) -> AdmissionTicket:
    # 1 role hợp lệ?            → ApiError(ROLE_REQUIRED, 400)
    # 2 rate_limit.check(ip_hash)→ ApiError(RATE_LIMITED, 429)
    # 3 quota.admit_new_session()  (remaining_daily_calls >= SESSION_CALL_RESERVE) → ApiError(QUOTA_EXCEEDED, 429)
    # 4 lease.try_acquire()        → ApiError(SYSTEM_BUSY, 409)   # luôn là bước CUỐI, để fail ở 1–3 không kẹt lease
```

### 5.3 `session/`

```python
# session/store.py
class InMemorySessionStore:
    def create(role, filename, analysis_date) -> Session
    def get(session_id) -> Session | None                      # lookup chính xác; có test âm cho ID khác
    def touch(session_id) -> None                              # CHỈ Create/Result/Retry/Export/End gọi; Status KHÔNG
    def delete(session_id) -> None                             # xóa mọi content + clause_graph + temp file
    def expired(now, ttl) -> list[str]
    # Chỉ Orchestrator được gọi các hàm ghi state (không để api/ tự set status)

# session/lock.py
class ProcessingLease:                                         # non-blocking, capacity=1
    def try_acquire(owner: str | None = None) -> bool          # [TDD]
    def assign_owner(owner: str) -> None
    def release(owner: str) -> None                            # chỉ owner release; gọi trong finally
    def holder() -> str | None

# session/cleanup.py
class CleanupScheduler:
    async def run_once(now) -> None      # inactivity >= SESSION_TTL_MINUTES ⇒ cancel → xóa temp/content → tombstone EXPIRED 24h
    def start(interval_s=60); def stop()
    def sweep_stale_temp(max_age_h=2)    # lúc startup

# session/orchestrator.py  — NƠI DUY NHẤT đổi state
class AnalysisOrchestrator:
    async def start(session_id, upload_path) -> None            # schedule _run; giữ lease tới finally
    async def retry(session_id) -> Session                      # try_acquire → tăng counter nguyên tử → chọn target theo failed_stage
    async def end(session_id) -> None                           # set cancel flag, cancel provider tasks, cleanup, release, tombstone
    async def _run(session, resume_from: Stage | None = None) -> None   # xem §6
    def _fingerprint(stage: Stage, session) -> str              # SHA-256(stage + upstream hashes + role + analysis_date + versions + config version)
    def _set_status(session, status, stage=None) -> None        # kiểm tra transition hợp lệ
    def _reject(session, code) ; def _fail(session, err_code, stage)
    def _check_cancel(session) -> None                          # gọi giữa các batch
```

### 5.4 `document/`

```python
# document/extractor.py
@dataclass class ExtractionResult: canonical_text: str; extraction_version: str; page_count: int | None; char_count: int
def detect_kind(path, display_name) -> Literal["pdf","docx"]    # sniff magic bytes; sai ⇒ ValidationReject(UNSUPPORTED_FILE_TYPE)
def extract(path: Path, kind) -> ExtractionResult               # CPU nặng ⇒ gọi qua asyncio.to_thread ở orchestrator

# document/pdf_extractor.py
def extract_pdf(path) -> list[str]     # page_count<=30 trước full extract (PDF_PAGE_LIMIT_EXCEEDED); 2 cột; bỏ header/footer lặp ≥60% trang; bảng flatten bằng " | "
# document/docx_extractor.py
def extract_docx(path) -> list[str]    # python-docx + lxml: numbering → text prefix, tracked changes = accepted state, bỏ comment/footnote, textbox gần anchor
# document/canonicalizer.py
def canonicalize(chunks: list[str]) -> str                      # [TDD §8.4] NFC → CRLF→LF → NBSP→space → trim cuối dòng → tối đa 2 dòng trống → join LF → NFC
# document/quality.py
def run_quality_gates(text: str, cfg) -> None                   # NO_EXTRACTABLE_TEXT / UNSUPPORTED_TEXT_ENCODING (U+FFFD, control char, printable ratio, legacy-font TCVN3/VNI); DOCX_TEXT_LIMIT_EXCEEDED
# document/scope_precheck.py
@dataclass class ScopeDecision: accept: bool; score: int; signals: list[str]
def precheck(canonical_text: str, cfg) -> ScopeDecision         # luật từ khóa/cấu trúc, KHÔNG LLM; strong-title chỉ tính trong SCOPE_TITLE_SCAN_CHARS đầu; không sửa canonical
```

### 5.5 `privacy/`

```python
# privacy/pii_types.py
class PiiType(str, Enum): PERSON_NAME; DATE_OF_BIRTH; NATIONAL_ID_OR_PASSPORT; RESIDENTIAL_ADDRESS; PHONE; EMAIL; BANK_ACCOUNT; LEGAL_ENTITY
TYPE_TAG: dict[PiiType,str]         # "<EMAIL>", "<NAME>", ...
TYPE_SHORT_CODE: dict[PiiType,str]  # N D I R P E B O
# privacy/detector.py
def detect(canonical_text: str) -> list[PiiSpan]    # regex độ chính xác cao trước; heuristic anchor ("Ông/Bà","Người lao động","Công ty","MST") sau; preserve-list; resolve overlap
# privacy/masker.py
def mask_value(text: str, pii_type: PiiType) -> str # [TDD §10.1]  assert len(out)==len(text) theo code point
def mask(canonical_text: str) -> MaskResult         # MaskResult(masked_text, pii_spans); toàn bộ canonical, TRƯỚC segmentation; không lưu bảng ánh xạ ngược
```

### 5.6 `clause/`

```python
# clause/taxonomy.py   — nguồn duy nhất của nhãn clause (12 nhãn, đóng băng MS-1)
CLAUSE_LABELS: tuple[str, ...] ; LABEL_DEFINITIONS: dict[str,str]
def validate_labels(labels: list[str]) -> list[str]    # 1..3, thuộc taxonomy, không trùng; else ValueError

# clause/structure_parser.py
def parse_structure(masked_text: str, boundary_guard: Callable[[int], bool]) -> list[HeadingMark]
#   5 pattern: Điều n | n.n | n) | a) | gạch đầu dòng; gán level/number/parent; boundary rơi vào placeholder thì dời ra mép placeholder hoặc bỏ

# clause/segmenter.py
def boundary_guard(pos: int, pii_spans: list[PiiSpan]) -> bool       # [TDD] False nếu start < pos < end của bất kỳ span
def segment(canonical_text, masked_text, pii_spans) -> list[SegmentedClause]
#   chạy trên masked_text, span tính trên canonical (cùng độ dài); original_text = canonical[start:end]
#   partition KHÔNG chồng lấn; mọi ranh giới kết thúc clause trước; fallback paragraph (<40 ký tự gộp neighbor)
#   clause >4000 ký tự giữ nguyên + warning; >150 clause ⇒ ValidationReject(TOO_MANY_CLAUSES)

# clause/graph_builder.py
def build_clause_graph(clauses, structure, masked_text) -> tuple[ClauseGraph, list[Diagnostic]]
#   NEXT (i→i+1), PARENT_OF (level cha < con, không chu trình), REFERS_TO (resolve duy nhất trong cùng hợp đồng)
#   LOẠI TRỪ dẫn chiếu pháp luật ("Điều 26 (của) Bộ luật…", Luật, Nghị định, Thông tư); mơ hồ ⇒ bỏ cạnh + diagnostic
# clause/context_resolver.py
def resolve_context(graph, target_id, masked_by_id, max_related=3, max_chars=6000) -> list[RelatedClause]   # [TDD §12.2]
#   thứ tự: REFERS_TO ra → REFERS_TO vào → cha/con → NEXT trước/sau; dedupe; bỏ target
def make_trace(target_id, related, included: bool) -> ContextResolutionTrace    # chỉ ID, dev/eval, KHÔNG vào API sản phẩm
```

### 5.7 `ai/`

```python
# ai/provider.py
class LLMProvider(Protocol):                                           # [TDD §13.4]
    async def generate_structured(self, *, model_id: str, messages: list[dict],
                                  response_schema: dict, timeout_s: int) -> LLMResponse: ...
class CallLedger(Protocol):                                            # do ops.quota/ops.runlog hiện thực
    def before_call(self) -> None          # tăng counter nguyên tử TRƯỚC mỗi actual request (kể cả retry)
    def after_call(self, in_tokens, out_tokens, cost, error_code=None) -> None
async def call_with_retry(provider, ledger, **req) -> LLMResponse      # retry matrix: timeout/network/429(backoff+jitter)/5xx/schema-invalid ≤1; 400/401/403 KHÔNG

# ai/gemini_client.py   — demo/eval (paid)
class GeminiProductClient(LLMProvider): ...    # model id bắt buộc, response_schema, temperature 0.0, KEY QUA HEADER (không query string)
# ai/dev_local_client.py — chỉ APP_ENV=dev + dữ liệu de-identify
class DevLocalClient(LLMProvider): ...

# ai/clause_adapter.py   — LLM #1
def make_batches(items, size) -> list[list]
async def classify_clauses(masked_items: list[ClauseMasked], provider, ledger, cfg, cancel) -> ClauseOutput
#   request = {schema_version, taxonomy_version, items:[{clause_id, masked_text}]}   KHÔNG gửi role, canonical, start/end
#   validate: mỗi clause_id đúng 1 lần; 1..3 nhãn thuộc taxonomy; không confidence/type_scores/quote/span; sai ⇒ retry ≤1 ⇒ AiOutputInvalid
#   batch=CLAUSE_BATCH_SIZE, song song ≤ LLM_PARALLELISM; kiểm cancel giữa batch

# ai/risk_adapter.py   — LLM #2 (basis_type + explanation + chọn citation; severity do backend tra bảng)
async def analyze_risks(role, items: list[RiskItemIn], candidates: dict[str, LegalCandidate],
                        risk_taxonomy, provider, ledger, cfg, cancel) -> RiskOutput
#   request = risk_analysis_request_v2: role, risk_taxonomy(label+definition), basis_types, candidates(catalog dedupe), items[{clause_id, masked_text,
#             clause_labels, candidate_ids, related_clauses[]}]; batch=RISK_BATCH_SIZE
#   response = risk_output_v2 (LLM trả basis_type; KHÔNG trả severity, role, span, version pins)
def detect_advice(text: str) -> list[str]                  # cụm: "bạn nên","NLĐ nên","nên sửa/bổ sung/thương lượng/yêu cầu","khuyến nghị"… KHÔNG match "nên" đơn
def detect_unsupported_reference(text, allowed_citation_ids, candidates) -> list[str]
def sanitize_explanation(text, bad_sentences) -> str       # xóa câu vi phạm; rỗng ⇒ AiOutputInvalid
# ai/prompts/clause_v1.py, risk_v1.py: build_system_prompt(...), build_messages(...) — sinh từ taxonomy, version pin
```

### 5.8 `legal/`

```python
# legal/citation_id.py
def make_citation_id(document_id, article, clause=None, point=None) -> str    # deterministic, vd "BLLD2019:art26"
def parse_citation_id(cid) -> CitationParts
# legal/corpus_loader.py
def load_corpus(root: Path) -> LegalCorpus     # manifest.yaml + provisions.jsonl + edges.jsonl (edge_suggestions.jsonl KHÔNG load)
class LegalCorpus:
    def resolve(cid, analysis_date) -> LegalProvision | None   # chỉ bản hiệu lực
    def effective_at(date) -> Iterable[LegalProvision]
# legal/corpus_validator.py
def validate_corpus(corpus) -> None            # raise LegalCorpusConflict: overlap hiệu lực, endpoint cạnh lạ, PARENT_OF có chu trình, content rỗng/không NFC
# legal/baseline_retriever.py
class BaselineRetriever:
    @classmethod def build(corpus, label_map) -> "BaselineRetriever"            # rank-bm25 + label_map trọng số trực tiếp
    def retrieve(masked_text, clause_labels, analysis_date, final_k) -> BaselinePool
    #   score = 0.70*label_weight + 0.30*bm25_norm ; pool = top final_k sau effectivity+dedupe ; seeds = top RETRIEVAL_SEED_K
# legal/data_graph.py
class DataGraph:
    @classmethod def build(corpus, edges) -> "DataGraph"       # PARENT_OF (AUTO từ parent_path) + REFERS_TO/GUIDES (MANUAL, đã xác minh)
    def expand(seeds, pool, cfg) -> list[LegalCandidate]       # 1 hop, ≤4 neighbor/seed, ≤2 child/seed
    #   graph_score = 0.60*seed.score + edge_bonus(REFERS_TO .30, GUIDES .25, PARENT_OF .15) + direction_bonus(.05)
def get_candidates(retriever, graph | None, masked_text, labels, analysis_date, cfg) -> RetrievalResult
#   seed-first; merge pool[seed_k:] + graph-only theo score chuẩn hóa; dedupe; lấy final_k (graph on/off CÙNG final_k)
#   graph lỗi runtime ⇒ pool + graph_fallback=True (RunLog), KHÔNG fail phiên
# legal/citation_validator.py
def validate_citations(risk: RiskItemOut, candidate_ids: set[str], corpus, analysis_date) -> ValidatedRisk
#   id ∉ candidates ⇒ log outside_candidate, loại ; resolve() hiệu lực ⇒ giữ
#   rỗng ⇒ evidence_status=INSUFFICIENT_EVIDENCE, severity=None, citation_ids=[]
```

### 5.9 `result/`

```python
# result/assembler.py
def derive_risk_basis(risk_labels, basis_type, role, risk_taxonomy) -> list[dict]     # one-to-one với risk_labels; ô '-' ⇒ gỡ nhãn; nhãn ngoài taxonomy ⇒ PipelineInternalError
def assemble(session) -> FinalResult
#   join theo clause_id; quote/start/end CHỈ từ canonical Clause; citations từ ID đã validate; offset_unit="unicode_code_point"
#   không risk ⇒ COMPLETED + thông điệp "không phát hiện rủi ro trong phạm vi phân tích" + disclaimer (không nói "an toàn")
#   publish NGUYÊN TỬ; FAILED không lộ partial
# result/exporter.py
def build_report_model(final: FinalResult) -> ReportModel          # header, disclaimer, DATA NOTICE, summary, risk section, citation appendix, footer version
def export_docx(model: ReportModel) -> bytes                       # bắt buộc
def export_pdf(model: ReportModel) -> bytes                        # cut item 4; tắt ⇒ 501 FEATURE_NOT_ENABLED
```

### 5.10 `ops/`

```python
# ops/metadata_db.py
def init_db(path) -> sqlite3.Connection        # chỉ metadata: run_log, usage, rate, tombstone; CẤM nội dung/PII
# ops/runlog.py
class RunLogWriter:
    def record_stage(session_id, stage, started_at, duration_ms, calls, in_tokens, out_tokens, cost, error_code,
                     graph_enabled, graph_added_candidates) -> None    # không prompt/canonical/masked/quote/PII/tên file thô
# ops/quota.py
class DailyQuota(CallLedger):
    def remaining() -> int
    def admit_new_session() -> bool            # remaining >= SESSION_CALL_RESERVE
    def before_call(); def after_call(...)     # tăng nguyên tử TRƯỚC call; phiên đang chạy không bị dừng nếu vượt
class EvalCostLedger(CallLedger): ...          # APP_ENV=eval: ghi eval_cost_ledger riêng, bỏ qua quota/rate runtime
# ops/rate_limit.py
class SlidingWindowLimiter:
    def check_and_record(ip_hash, now) -> bool # mặc định 5 upload/10 phút/IP
```

---

## 6. Luồng gọi end-to-end của Orchestrator (pseudocode)

```python
async def _run(self, session, resume_from=None):
    owner = str(session.session_id)
    try:
        # ───────── VALIDATING (EXTRACTION → CLAUSE_GRAPH) ─────────
        self._set_status(session, VALIDATING)
        kind = detect_kind(path, session.filename)                                   # UNSUPPORTED_FILE_TYPE / FILE_TOO_LARGE
        ext  = await to_thread(extract, path, kind)                                  # NO_EXTRACTABLE_TEXT / PDF_PAGE_LIMIT_EXCEEDED / DOCX_TEXT_LIMIT_EXCEEDED
        run_quality_gates(ext.canonical_text, cfg)                                   # UNSUPPORTED_TEXT_ENCODING
        if not precheck(ext.canonical_text, cfg).accept: raise ValidationReject("NOT_LABOR_CONTRACT")
        mask = await to_thread(mask_pii, ext.canonical_text)                         # INV-01: len(masked)==len(canonical)
        segs = await to_thread(segment, ext.canonical_text, mask.masked_text, mask.pii_spans)   # INV-02/03; TOO_MANY_CLAUSES
        graph = build_clause_graph(...) if cfg.CLAUSE_GRAPH_ENABLED else None        # INV-08
        # ───────── PROCESSING ─────────
        self._set_status(session, PROCESSING)
        labels = await classify_clauses(masked_items, provider, ledger, cfg, cancel) # LLM #1 — không role
        cands  = {c.clause_id: get_candidates(...) for c in clauses}                 # LEGAL_RETRIEVAL (local)
        items  = build_risk_items(clauses, labels, cands, graph, resolve_context)    # related masked context (≤3 clause, ≤6000 cp)
        raw    = await analyze_risks(session.role, items, catalog, taxonomy, provider, ledger, cfg, cancel)   # LLM #2
        valid  = [validate_citations(r, cand_ids[r.clause_id], corpus, session.analysis_date) for r in raw.items]
        final  = assemble(session_with(valid))                                       # dựng risk_basis + tra severity, join clause_id
        self._publish(session, final)                                                # nguyên tử ⇒ COMPLETED
    except ValidationReject as e:          self._reject(session, e.code)            # REJECTED (cuối, không retry)
    except AiTimeout:                      self._fail(session, "AI_TIMEOUT", stage)
    except AiProviderError:                self._fail(session, "AI_PROVIDER_ERROR", stage)
    except AiOutputInvalid:                self._fail(session, "AI_OUTPUT_INVALID", stage)
    except Exception:                      self._fail(session, "INTERNAL_ERROR", stage)   # bọc thành PipelineInternalError
    finally:
        self.lease.release(owner)                                                    # FAILED KHÔNG giữ lease ⇒ retry phải acquire lại
```

Retry: `lease.try_acquire()` → (thất bại ⇒ `SYSTEM_BUSY`, counter giữ nguyên) → `manual_retry_count += 1` → `failed_stage` thuộc local stage ⇒ về `VALIDATING`, thuộc processing ⇒ về `PROCESSING` → resume artifact có fingerprint còn hợp lệ (nếu cut item 2 thì chạy lại từ đầu, vẫn giới hạn 2 lần).

Số LLM call/hợp đồng ≈ `ceil(n/CLAUSE_BATCH_SIZE) + ceil(n/RISK_BATCH_SIZE)` (40–60 clause ≈ 9–13 call, trước retry). Graph không thêm LLM call.

---

## 7. Hợp đồng dữ liệu giữa stage

| Stage | Vào | Ra (artifact) | Validate sau stage | Lỗi |
|---|---|---|---|---|
| EXTRACTION | file, role | `extraction_v1` {canonical_text, extraction_version, page_count?, char_count} | NFC, không rỗng, giới hạn, quality gate | REJECTED |
| SCOPE_PRECHECK | canonical | `ScopeDecision` | score/ngưỡng | `NOT_LABOR_CONTRACT` |
| PII_MASKING | canonical | `masking_v1` {masked_text, pii_spans[{type,start,end}]} | `len` bằng nhau, span không chồng, không bảng ngược | `INTERNAL_ERROR` |
| SEGMENTATION | canonical + masked + pii_spans | `segmentation_v1` {clauses[{clause_id, original_text, start_char, end_char, structure}]} | ID unique, sorted, partition, substring, không ranh giới trong placeholder, ≤150 | `TOO_MANY_CLAUSES` |
| CLAUSE_GRAPH | clauses + structure + masked | `ClauseGraph` (ID + edge_type) | node tồn tại, không self-loop, PARENT_OF không chu trình | `INTERNAL_ERROR` |
| CLAUSE_CLASSIFICATION | `{clause_id, masked_text}` theo lô | `clause_output_v3` {items[{clause_id, clause_labels}], model_id, prompt_version, taxonomy_version} | mỗi ID đúng 1 lần, 1..3 nhãn hợp lệ | `AI_*` |
| LEGAL_RETRIEVAL | masked clause + labels + analysis_date | `retrieval_v1` {per_clause[{clause_id, candidates[]}], corpus_version, data_graph_version, graph_enabled} | candidate tồn tại + hiệu lực, ≤ final_k | `INTERNAL_ERROR` |
| RISK_ANALYSIS | role + items + candidate catalog | `risk_output_v2` {items[{clause_id, basis_type, risk_labels, citation_ids, evidence_status, explanation}]} | nhãn ∈ taxonomy; SUPPORTED ⇒ citation + severity; INSUFFICIENT ⇒ `[]` + `null`; lint advice/tham chiếu | `AI_OUTPUT_INVALID` |
| CITATION_VALIDATION | risk + candidate_ids + corpus | `ValidatedRisk` | citation ⊂ candidates ⊂ corpus ⊂ hiệu lực | — (hạ về INSUFFICIENT) |
| ASSEMBLY | tất cả | `final_result_v1` | `risk_basis` dựng đủ, severity khớp bảng taxonomy; không risk thiếu clause; thêm `offset_unit` | `INTERNAL_ERROR` |

---

## 8. Lỗi → exception → state → HTTP

| Nhóm | Mã | Exception | State | Retry? |
|---|---|---|---|---|
| Không tạo session | `ROLE_REQUIRED 400`, `SYSTEM_BUSY 409`, `QUOTA_EXCEEDED 429`, `RATE_LIMITED 429` | `ApiError` (ở gate) | — | client tự thử lại |
| Input/phạm vi | `UNSUPPORTED_FILE_TYPE`, `FILE_TOO_LARGE`, `PDF_PAGE_LIMIT_EXCEEDED`, `DOCX_TEXT_LIMIT_EXCEEDED`, `NO_EXTRACTABLE_TEXT`, `UNSUPPORTED_TEXT_ENCODING`, `NOT_LABOR_CONTRACT`, `TOO_MANY_CLAUSES` | `ValidationReject` | `REJECTED` (cuối) | **Không** |
| AI/nội bộ | `AI_TIMEOUT`, `AI_PROVIDER_ERROR`, `AI_OUTPUT_INVALID`, `INTERNAL_ERROR` | `AiTimeout`, `AiProviderError`, `AiOutputInvalid`, `PipelineInternalError` | `FAILED` | Thủ công ≤2 |
| API-state | `INVALID_SESSION_STATE`, `SESSION_NOT_READY`, `SESSION_REJECTED`, `SESSION_EXPIRED 410`, `RETRY_LIMIT_EXCEEDED`, `FEATURE_NOT_ENABLED 501`, `SESSION_NOT_FOUND` | `ApiError` | không đổi | — |
| Startup | `LEGAL_CORPUS_CONFLICT` | `LegalCorpusConflict` | service không ready | — |

---

## 9. Invariant tests INV-01…INV-12 (TDD §19.2) — mỗi cái phải có test

| ID | Invariant | Hàm chịu trách nhiệm | Test đề xuất [Đề xuất] |
|---|---|---|---|
| INV-01 | `len(masked)==len(canonical)` (code point) | `masker.mask`, `mask_value` | `tests/unit/test_inv01_mask_length.py` (fixture `privacy/`, gồm non-BMP) |
| INV-02 | `canonical[start:end]==original_text` | `segmenter.segment` | `tests/unit/test_inv02_span_substring.py` |
| INV-03 | span không chồng + ranh giới không trong PII | `segment`, `boundary_guard` | `tests/unit/test_inv03_partition.py` (nested, list adversarial) |
| INV-04 | ra ngoài chỉ có masked text | `clause_adapter`, `risk_adapter`, `gemini_client` | `tests/integration/test_inv04_outbound_capture.py` (bắt payload gửi provider, quét PII/canonical) |
| INV-05 | LLM không override span/quote | schema validate ở adapter | `tests/contract/test_inv05_extra_fields.py` (response có `start_char`, `quote`, `type_scores` ⇒ bị từ chối) |
| INV-06 | citation ⊂ candidate ∈ corpus hiệu lực | `validate_citations` | `tests/unit/test_inv06_fake_citation.py` |
| INV-07 | INSUFFICIENT ⇒ severity null, citation rỗng | `validate_citations`, assembler | `tests/contract/test_inv07_insufficient.py` |
| INV-08 | Clause Graph không chứa text | `build_clause_graph` | `tests/unit/test_inv08_graph_no_text.py` (serialize + duyệt object) |
| INV-09 | restart mất nội dung session | `InMemorySessionStore`, cleanup | `tests/integration/test_inv09_restart.py` |
| INV-10 | FAILED không trả final | orchestrator, `get_result` | `tests/integration/test_inv10_failed_no_result.py` (error injection) |
| INV-11 | graph on/off cùng `final_k` | `get_candidates` | `tests/unit/test_inv11_final_k.py` |
| INV-12 | highlight JS đúng với non-BMP | frontend `cpToUtf16` | `frontend/src/**/offset.test.ts` |

API/state bổ sung (TDD §19.3): pre-admission không tạo session; 2 Create đồng thời; REJECTED sau 201; retry #1/#2/#3; retry khi phiên khác chạy; local FAILED→VALIDATING, processing FAILED→PROCESSING; polling không kéo TTL, Result/Export có; End idempotent; tombstone 24h → `SESSION_NOT_FOUND`.

---

## 10. Frontend skeleton **[Đề xuất]** (TDD không khóa framework; chỉ khóa contract §5.9)

```text
frontend/src/
  api/client.ts            createSession(role,file) · getStatus(id) · getResult(id) · retry(id) · exportReport(id,fmt) · endSession(id)
  api/types.ts             sinh/đối chiếu từ final_result_v1 + ErrorResponse
  hooks/usePolling.ts      500ms đầu → 1.5s (→2.5s sau 60s); dừng ở trạng thái cuối; KHÔNG kéo TTL
  lib/offset.ts            buildCodePointIndex(text) → number[] ; cpSlice(text, start, end)   # INV-12
  lib/messages.ts          catalog thông báo tiếng Việt theo error_code (TDD Phụ lục E)
  pages/Upload.tsx         chọn role (bắt buộc) + upload + disclaimer + data notice
  pages/Progress.tsx       VALIDATING/PROCESSING + stage + progress
  pages/Result.tsx         canonical text + highlight (1 highlight/clause) + detail panel (nhiều label) + export + End
  components/RiskDetail.tsx   label + basis_type + severity badge | "Chưa đủ căn cứ pháp lý trong kho luật" (không badge) + citations
```
Quy tắc UI: REJECTED không có nút Retry; FAILED có Retry khi `manual_retry_count<2` (có thể gặp `SYSTEM_BUSY`); không risk ⇒ "Không phát hiện rủi ro trong phạm vi phân tích" + disclaimer, **không** dùng chữ "an toàn"; không tự merge AI result, không tự tính span.

---

## 11. Cấu hình → nơi dùng (TDD §4.1)

| Biến | Dùng ở |
|---|---|
| `APP_ENV`, `GEMINI_API_KEY`, `GEMINI_MODEL_ID`, `DEV_LLM_PROVIDER` | `core/config.validate_for_env`, `ai/gemini_client`, `ai/dev_local_client` |
| `LLM_TIMEOUT_SECONDS`(30), `LLM_AUTO_RETRY`(1), `TEMPERATURE`(0.0) | `ai/provider.call_with_retry`, adapters |
| `CLAUSE_BATCH_SIZE`(20), `RISK_BATCH_SIZE`(6), `LLM_PARALLELISM`(2) | `ai/clause_adapter`, `ai/risk_adapter` (tune D1) |
| `MAX_UPLOAD_MB`(10), `MAX_PDF_PAGES`(30), `MAX_DOCX_CHARS`(100000), `MAX_CLAUSES`(150) | `api/create_session` (byte cap), `document/*`, `clause/segmenter` |
| `SESSION_TTL_MINUTES`(60), `EXPIRED_TOMBSTONE_HOURS`(24) | `session/cleanup`, `ops/metadata_db` |
| `DAILY_LLM_CALL_QUOTA`, `SESSION_CALL_RESERVE` (**bắt buộc ở demo**) | `ops/quota` |
| `RATE_LIMIT_UPLOADS`(5), `RATE_LIMIT_WINDOW_SECONDS`(600) | `ops/rate_limit` |
| `DATA_GRAPH_ENABLED`, `RETRIEVAL_SEED_K`(3), `RETRIEVAL_FINAL_K`(8), `GRAPH_MAX_NEIGHBORS_PER_SEED`(4), `GRAPH_MAX_CHILDREN_PER_SEED`(2) | `legal/*` |
| `CLAUSE_GRAPH_ENABLED`, `CLAUSE_GRAPH_MAX_RELATED`(3), `CLAUSE_GRAPH_MAX_CONTEXT_CHARS`(6000) | `clause/graph_builder`, `context_resolver` |
| `SCOPE_TITLE_SCAN_CHARS`(1000) | `document/scope_precheck` |

Startup (fail-fast): config → taxonomy/rubric (bảng severity theo `basis_type`) → corpus + `validate_corpus` → BM25 + label_map + Data Graph → SQLite → store + lease + cleanup → threadpool → `readiness=true`. Demo: **1 Uvicorn worker**.

---

## 12. Evaluation harness (TDD §18)

```bash
python -m ai_pipeline.evaluation.runner --dataset T1 --config configs/eval.yaml --output evaluation/runs/run_001/
python -m ai_pipeline.evaluation.runner --dataset T2 --metric M8 --graph-enabled true|false
```

| Hàm / module [Đề xuất] | Việc | Ghi chú |
|---|---|---|
| `runner.run(dataset, config, output)` | gọi pipeline **trực tiếp** (không HTTP, không quota), ghi version pins + config snapshot + commit | `APP_ENV=eval`, `EvalCostLedger` |
| `load_dataset(manifest)` | đọc manifest + gold (seg/clause/risk/injected/privacy/judge/annotation/context_trace) | dữ liệu đã de-identify; dataset v06: 1 dòng = 1 nhãn, `offset_quality` EXACT/CONTEXT, CONTEXT `span=null` không chấm exact, không phải gold segmentation (TDD §18.3) |
| `metrics/segmentation.py` | **M1** IoU≥0.80, ghép tham lam | giữ từ `eval_segmentation.py` |
| `metrics/risk_classification.py` | M2 macro-F1 (clause, role, risk label) | chỉ macro nhãn ≥5 mẫu |
| `metrics/citation_validity.py` | M3a = 100% | candidate + corpus + hiệu lực |
| `metrics/citation_relevance.py` | M3b ≥85% (nhập từ người/judge) | |
| `metrics/quote_span.py` | M4 = 100% | substring + code-point offset |
| `metrics/injected_recall.py` | M5 ≥90% (≥30 lỗi chèn) | judge không tham gia |
| `metrics/judge_calibration.py` | M6 ≥80% & κ≥0.6 | |
| `metrics/clause_classification.py` | M7 macro-F1 ≥0.80 | |
| `metrics/retrieval.py` | M8 recall@5 on/off, **cùng final_k**, predicted labels là primary | `M8-oracle-labels` chỉ chẩn đoán |
| `metrics/privacy.py`, `annotation_agreement.py`, `baseline_comparison.py` | PII recall + preserve rate; Cohen κ ≥20% item; BL-1 (cut item 1) | |

**Không chỉnh hệ thống dựa trên T1/T2.** Mọi tuning làm trên D1/D2 và version config.

---

## 13. Chưa có trong tài liệu / cần chốt khi code (đừng tự quyết ngầm)

1. **Chữ ký hàm ở §5 là đề xuất** — nhóm review một lần ở tuần 1–2 rồi khóa.
2. **12 nhãn clause taxonomy**: semantics nguồn ở data repo `docs/clause_taxonomy_v03.md`, code ở `taxonomy.py` (`TAXONOMY_VERSION=v04`; BRD/SRS chỉ nói "12 nhãn"); topic bảo mật/không cạnh tranh và giải quyết tranh chấp chưa có nhãn chốt; risk taxonomy v0.1 (21 nhãn) đã có ở `docs/RISK_TAXONOMY_v0.1.md` và `app/risk/taxonomy.py`, chờ đóng băng ở MS-1 (BRD OI-01).
3. Hard byte cap khi upload (§3 ghi chú) — cách hiện thực chưa chốt.
4. `GET /status` trả `progress.completed_units/total_units` — đơn vị (batch? clause?) TDD chưa định nghĩa; đề xuất: đơn vị = clause đã xong ở stage hiện tại.
5. Mã `retry` trả về 200 hay 202 — TDD chưa nêu rõ.
6. API-state code (TDD §5.8) chưa backport vào SRS 6.2 (TDD O-09); SDD thiếu mũi tên `VALIDATING → FAILED` (TDD O-11).
7. Nếu muốn `related_clause_ids` trong RiskResult sản phẩm → **sửa SRS trước**; hiện chỉ có `ContextResolutionTrace` dev/eval.
8. Quy đổi gold dataset (single-label, tách clause theo ngữ nghĩa, bỏ heading) ↔ clause pipeline (partition, 1–3 nhãn) khi tính M2/M7 — chưa có chính sách (SRS OI-10); đề xuất chờ N1+N2 chốt cùng guideline, đừng tự quyết ngầm.
