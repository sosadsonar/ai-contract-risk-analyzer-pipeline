# Contributing Guide

Repo này là code của **AI Contract Risk Analyzer** (`ai_pipeline/`, sau này thêm `backend/`, `frontend/`, `notebooks/`).
Dữ liệu nằm ở **repo riêng** (`data`, do Người 2 quản lý) và được gắn vào đây dưới dạng **git submodule** tại `ai_pipeline/data/`.

```
ai-contract-risk-analyzer-pipeline/     <- repo này (code)
├── ai_pipeline/
│   ├── services/       mock_clause_service.py (mock theo clause_output_v3, dùng ở test contract)
│   ├── schemas/        clause_output_v3, risk_output_v2, extraction_v1, final_result_v1 (JSON Schema)
│   ├── eval/           eval_pii*.py, eval_p1.py (đo PII, BRD §7.3), eval_segmentation.py
│   ├── evaluation/     runner, dataset, metrics/ (M1, M2/M2b/M9, M3a, M4, M5, M6, M7, M8, M10, privacy)
│   └── data/           <- SUBMODULE = repo `data` (chỉ đọc từ repo này)
├── backend/app/
│   ├── pipeline.py          analyze(): chuỗi stage end-to-end, orchestrator + harness cùng gọi (X-19)
│   ├── api/, session/       6 operation HTTP, store RAM, lease, orchestrator (retry/resume/cancel), cleanup
│   ├── document/            PDF/DOCX extraction (extract_docx_v2, OI-11), scope precheck (scope_rules_v2, OI-03)
│   ├── privacy/             detector + masker (pii_draft_0.5)
│   ├── clause/              taxonomy (v05, OI-10), structure_parser_v2, segmenter, graph_builder (v2, REFERS_TO),
│   │                        context_resolver (TDD §12.2, FR-33)
│   ├── ai/                  provider + retry/ledger, gemini_client (giá có nguồn), dev_local_client, dev_fake_client,
│   │                        clause_adapter (LLM #1), risk_adapter (LLM #2 + lint/retry ngữ nghĩa), prompts/
│   ├── legal/               corpus loader/validator, BaselineRetriever, DataGraph
│   ├── risk/                taxonomy + severity, lint (advice/unsupported reference), citation_validator
│   ├── integrations/        risk_assembler (risk_merged_v1, bản ghi needs_review)
│   ├── result/              report_model, export_docx, notices (disclaimer/data notice)
│   ├── ops/                 quota, rate_limit, runlog, session_ledger, metadata_db, benchmark_d1, benchmark_pipeline
│   ├── domain/errors.py     ValidationReject, Ai*, PipelineInternalError, LegalCorpusConflict (MỘT file)
│   └── core/                config (Settings, validate_for_env), enums (MỘT nguồn, DEC-20)
├── frontend/           React + TS + Vite (N5): Upload, Progress, Result; lib/ có test vitest
├── scripts/            smoke_pipeline.py, parse_legal_text.py, expand_label_map.py, update_legal_corpus_checksums.py…
├── tests/{unit,contract,integration,llm,fixtures}/ ; backend/tests/
├── data/legal_corpus/  kho luật (checksum theo byte LF — không đổi CRLF)
├── docs/               BRD/SRS/SDD/TDD, taxonomy, quyết định OI (docs/decisions/), báo cáo đo
├── .env.example        mẫu cấu hình (copy thành .env)
└── CONTRIBUTING.md
```

---

## 1. Clone và cài đặt

### 1.1 Clone (nhớ kéo cả submodule)

```bash
git clone --recurse-submodules https://github.com/sosadsonar/ai-contract-risk-analyzer-pipeline.git
cd ai-contract-risk-analyzer-pipeline
```

Nếu đã lỡ clone thường (thư mục `ai_pipeline/data/` bị rỗng):

```bash
git submodule update --init --recursive
```

Nếu làm việc trên **fork**, thêm remote gốc để đồng bộ:

```bash
git remote add upstream <url-repo-gốc>
git fetch upstream
```

> ⚠️ Không chạy `git submodule update --remote`. Lệnh đó kéo `main` mới nhất của repo `data` và làm đổi phiên bản dữ liệu mà không ai biết. Muốn cập nhật data, làm theo mục 6.

### 1.2 Cài môi trường Python

```bash
python -m venv .venv

# macOS/Linux
source .venv/bin/activate
# Windows (CMD)
.venv\Scripts\activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
pip install -e .'[dev]'
```

## 2. Cấu hình `.env`

`.env` chứa API key nên **không được commit** (đã có trong `.gitignore`). Repo chỉ chứa file mẫu `.env.example`.

```bash
# macOS/Linux
cp .env.example .env
# Windows CMD
copy .env.example .env
# Windows PowerShell
Copy-Item .env.example .env
```

Đặt `.env` ở **thư mục gốc repo** (cùng cấp `README.md`), rồi mở ra điền giá trị.

Danh sách đầy đủ ở `.env.example` và `backend/app/core/config.py` (`Settings`). Biến hay dùng:

| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `APP_ENV` | `dev` / `demo` / `eval`. demo/eval fail-fast nếu thiếu key, model, quota, reserve, salt | `dev` |
| `DEV_LLM_PROVIDER` | `gemini`, `local` (Ollama), `fake` (offline, tất định — smoke/ghép frontend, không đo chất lượng). `local`/`fake` chỉ dev | `gemini` |
| `GEMINI_API_KEY`, `GEMINI_MODEL_ID` | Key và model id **tường minh** (không có model mặc định ngầm) | trống |
| `DAILY_LLM_CALL_QUOTA`, `SESSION_CALL_RESERVE` | Giá trị tạm OI-05: 300 / 40 (`.env.example`); reserve là ngưỡng admission, quota không phải trần USD | trống ở `Settings` |
| `LLM_PRICE_INPUT_USD_PER_MTOK`, `LLM_PRICE_OUTPUT_USD_PER_MTOK`, `LLM_PRICE_SOURCE` | Giá có nguồn để tính cost; trống ⇒ cost = 0.0 nghĩa là "chưa biết" | trống |
| `OLLAMA_BASE_URL` | Địa chỉ Ollama khi `DEV_LLM_PROVIDER=local` | `http://localhost:11434` |
| `LEGAL_CORPUS_DIR`, `APP_COMMIT` | Thư mục kho luật; commit ghi vào `version_pins.app_commit` (EV-07) | `data/legal_corpus`, `unknown` |

**Chế độ chạy API:** dev không có provider (gemini thiếu key/model) ⇒ trả fixture mẫu; dev có provider ⇒ pipeline thật (corpus DRAFT được phép); demo/eval ⇒ luôn pipeline thật.

> ⚠️ Gói miễn phí và model local/fake chỉ dùng cho phát triển với dữ liệu **đã de-identify**; demo/đánh giá dùng Gemini gói trả phí, model id đặt tường minh (SRS DEC-19, NFR-SEC-06).

**Dùng Qwen local (không cần key):** cài Ollama (<https://ollama.com/download>), `ollama pull qwen2.5:7b-instruct`, đặt `DEV_LLM_PROVIDER=local`, `GEMINI_MODEL_ID=qwen2.5:7b-instruct` (tên model Ollama).

**Kiểm tra `.env` không bị commit:** chạy `git status`, file `.env` **không được** xuất hiện. Nếu xuất hiện, dừng lại và báo nhóm trước khi commit.

> Lỡ commit/push API key? Coi như key đã lộ: **vào trang cấp key thu hồi và tạo key mới ngay**, rồi báo nhóm. Xóa commit không đủ vì key vẫn nằm trong lịch sử.

---

## 3. Chạy thử

**pytest (khuyến nghị, từ thư mục gốc):** `pyproject.toml` đã đặt `pythonpath = [".", "backend"]` nên `import app.*` và `import ai_pipeline.*` đều chạy được.

```bash
pip install -e '.[dev]'
pytest                      # unit + contract + integration (+ test của Data Lead; cần submodule ai_pipeline/data)
pytest tests/contract       # chỉ hợp đồng schema (clause_output_v3, enum ↔ schema)
pytest tests/unit/test_segmenter.py tests/unit/test_structure_parser.py   # segmentation (INV-02/03)
ruff check .                # lint toàn repo (CI chặn cứng)
cd frontend && npm ci && npm test && npm run build   # frontend
```

**Smoke toàn pipeline** (không cần API key; DOCX tổng hợp → `analyze()` với provider giả → kiểm schema):

```bash
python scripts/smoke_pipeline.py
```

**Chạy API với pipeline thật nhưng offline** (ghép frontend, thử tay): `DEV_LLM_PROVIDER=fake python -m uvicorn app.main:app --app-dir backend --port 8000`, rồi `cd frontend && VITE_USE_MOCK=false npm run dev`.

**Benchmark end-to-end** (X-05): `python -m app.ops.benchmark_pipeline --provider fake --latency-ms 800` (chạy từ `backend/`, cần submodule D1); `--provider gemini` chỉ với dữ liệu D1 đã che và key paid.

**Test gọi model thật** (mặc định `pytest` bỏ qua; chỉ văn bản tổng hợp, `tests/llm/_synthetic.py`):

```bash
# Gemini (tốn quota): cần GEMINI_API_KEY, tùy chọn GEMINI_MODEL_ID
pytest -m llm tests/llm -s

# Model cục bộ qua Ollama (chỉ APP_ENV=dev): cần Ollama đang chạy và model đã `ollama pull`
OLLAMA_MODEL=qwen2.5:7b-instruct pytest -m llm_local tests/llm/test_llm_local.py -s
# Windows PowerShell
$env:OLLAMA_MODEL="qwen2.5:7b-instruct"; pytest -m llm_local tests/llm/test_llm_local.py -s
```

Luồng `DevLocalClient` còn có test OFFLINE (transport giả) trong `tests/unit/test_dev_local_client.py`, chạy mặc định.

**Đo PII** (BRD §7.3): `python ai_pipeline/eval/eval_pii.py --out docs/PII_MEASUREMENT_<ngày>.md`.

| Lỗi thường gặp | Nguyên nhân / cách xử lý |
|---|---|
| `ModuleNotFoundError: app` | Chạy pytest/script từ thư mục gốc (pyproject đặt `pythonpath`), uvicorn dùng `--app-dir backend` |
| `SHA-256 mismatch` ở corpus | Editor đổi `data/legal_corpus` sang CRLF → `git checkout -- data/legal_corpus`, **không** băm lại |
| `Thiếu GEMINI_API_KEY` | Chưa tạo `.env` ở thư mục gốc hoặc chưa điền key |
| `ai_pipeline/data/` rỗng | Chưa kéo submodule → `git submodule update --init --recursive` |
| Nhãn không thuộc 12 nhãn | Đang dùng nhãn cũ (8 nhãn v1). Xem `docs/CLAUSE_TAXONOMY.md` |
| Không kết nối được Ollama | Chưa chạy Ollama hoặc chưa `ollama pull` model |

### 3.1 CI (`.github/workflows/ci.yml`)

Mỗi push vào `main` và mỗi PR chạy tự động; **PR đỏ thì không merge** (§4.5). CI không dùng API key, không gọi LLM.

| Job | Làm gì | Chạy lại ở máy bạn |
|---|---|---|
| `test` (py3.10 và 3.12) | `pip install -e '.[dev]'`, `pytest --ignore=tests/test_data_lead_review.py` (gồm `tests/` + `backend/tests/`), rồi `python scripts/smoke_pipeline.py` | cùng lệnh |
| `data` | Kéo submodule rồi chạy `tests/test_data_lead_review.py` + `tests/integration`. **Không kéo được submodule thì chỉ cảnh báo**, không đỏ CI. Repo data private: tạo PAT chỉ đọc và đặt secret `SUBMODULE_TOKEN` | `pytest tests/test_data_lead_review.py tests/integration` |
| `lint` | `ruff check .` toàn repo (**bắt buộc**) | `ruff check .` |
| `frontend` | `npm ci`, `npm test` (vitest), `npm run build` | `cd frontend && npm test && npm run build` |

**Test gọi LLM thật (tùy chọn, thủ công).** `tests/llm/test_llm_live.py` (marker `llm`) gọi Gemini bằng văn bản tổng hợp; `pytest` thường tự bỏ qua (`-m "not llm"`). Chạy ở máy: đặt `GEMINI_API_KEY` trong `.env` rồi `pytest -m llm tests/llm -s`. Chạy trên GitHub:

1. Repo → Settings → Secrets and variables → Actions → **New repository secret**: tên `GEMINI_API_KEY`, dán key (nên dùng key riêng cho CI, có hạn mức thấp). Tùy chọn: tab *Variables* đặt `GEMINI_MODEL`; hoặc tạo Environment tên `llm` và đặt secret ở đó để yêu cầu người duyệt.
2. Actions → CI → **Run workflow** → tick `run_llm`. Kết quả JSON hiện ở Summary của job `llm-live` và tải được ở artifact `llm-result`.

Job này không bao giờ chạy trên push/PR (fork không có secret, tránh tốn quota). Không đưa hợp đồng thật vào test này (AI_CONTEXT §3).

File/test mới phải sạch lint ngay từ đầu (dòng ≤150 ký tự theo pyproject, import đã sắp). Test cần dữ liệu thật phải tự `skip` khi thiếu submodule (xem `tests/integration/`), không làm job `test` đỏ.

---

## 4. Quy trình Git

### 4.1 Không push trực tiếp vào `main`

```
main → tạo branch → code / sửa file → commit → push → Pull Request → review → merge
```

### 4.2 Bắt đầu task

```bash
git switch main
git pull origin main
git switch -c <ten-branch>
```

Ví dụ: `git switch -c ai/sync-clause-taxonomy`

### 4.3 Tên branch

```
data/<task>
ai/<task>
backend/<task>
frontend/<task>
docs/<task>
fix/<task>
```

### 4.4 Commit

Format: `<type>: <description>`

```
data: update clause taxonomy
feat: add risk classifier
fix: correct parser bug
docs: update README
chore: bump data submodule
```

### 4.5 Pull Request

- Mọi thay đổi vào `main` phải qua PR.
- Ít nhất 1 người review và **CI xanh** (§3.1).
- Không merge khi còn conflict.
- Merge ưu tiên **Squash and merge**. Không dùng `git push --force`.

### 4.6 Tránh conflict

Không sửa cùng file với người khác nếu chưa trao đổi. Nếu `main` có thay đổi mới:

```bash
git switch main
git pull origin main
git switch <ten-branch>
git merge main
```

### 4.7 Không commit secrets

Không commit: `.env`, API key, password, AWS credentials, file model nặng (`*.gguf`, `*.pt`...).

---

## 5. Dữ liệu dùng để test

| Bộ dữ liệu | Ở đâu | Dùng để làm gì |
|---|---|---|
| **Synthetic** (6 hợp đồng tự viết, 27 clause) | `ai_pipeline/eval/fixtures/synthetic_v0.2.json`, sinh bởi `build_synthetic.py` | Smoke-test `eval_segmentation.py` và định dạng dữ liệu, chạy offline, không cần submodule/API. **Không dùng để báo cáo KPI.** |
| **Dataset v06** (HDLD001–005, 234 clause; mẫu hợp đồng) | `ai_pipeline/data/` (submodule pin a086606) | 225 EXACT + 9 CONTEXT. Áp masks provisional_v06 trước đánh giá; CONTEXT không phải exact gold. Xem `docs/DATA_LEAD_REVIEW_V03.md` và handoff tuần 5 trong data submodule. |

Chạy lại bộ synthetic (khi thêm hợp đồng vào `CONTRACTS`):

```bash
cd ai_pipeline
python eval/fixtures/build_synthetic.py
```

---

## 6. Submodule `ai_pipeline/data` (repo dữ liệu)

Quy tắc:

- **Chỉ đọc** từ repo này. Muốn sửa dữ liệu, sửa ở repo `data` của Người 2 và mở PR ở đó. Không sửa/commit file bên trong `ai_pipeline/data/` từ repo code.
- Không sửa trực tiếp `data/raw/`. Không xóa version cũ (`clauses_v01.csv`, `clauses_v02.csv`...).
- Repo code **ghim (pin) vào 1 commit cụ thể** của repo `data`. Dữ liệu chỉ đổi khi có PR bump submodule rõ ràng.

### Quy trình bump khi có data mới

```bash
cd ai_pipeline/data
git fetch origin
git log origin/main --oneline -5      # xem có gì mới, chọn đúng commit muốn lấy
git checkout <sha-cụ-thể>             # pin vào 1 commit rõ ràng, không checkout "origin/main"
cd ../..
git status                            # thấy: modified: ai_pipeline/data (new commits)
git add ai_pipeline/data
git commit -m "chore: bump data submodule to <sha-ngắn> - <lý do, vd: clauses_v03 + raw_text/offset>"
git push -u origin <nhánh-hiện-tại>
```

Sau đó mở PR như bình thường để cả nhóm thấy diff (chỉ 1 dòng đổi SHA).

Kiểm tra đang pin commit nào: `git submodule status` (ký tự `+` đầu dòng = submodule đang lệch commit so với repo cha; `-` = chưa init).

---

## 7. Đổi taxonomy (nhãn clause)

Clause taxonomy là artifact đóng băng ở **MS-1 (25/10/2026)** (SRS DEC-10); sau đó đổi nhãn/định nghĩa làm mất giá trị số đo (BRD 8.2 quy tắc 5). Risk taxonomy và severity là artifact **riêng** (BRD OI-01), không nằm trong `taxonomy.py`.

Taxonomy ảnh hưởng đến Người 1 (prompt/pipeline), Người 2 (annotation) và Người 3 (risk), nên:

1. Mở PR riêng (`docs/...` hoặc `ai/...`), **review bắt buộc của Người 1, 2, 3**.
2. Semantics nguồn nằm ở data repo (`clause_taxonomy_v03.md`). Bản đóng băng và chính sách đa nhãn ghi ở `docs/CLAUSE_TAXONOMY_FREEZE.md`. Sửa `LABEL_DEFINITIONS` trong `backend/app/clause/taxonomy.py` và tăng `TAXONOMY_VERSION` (hiện `v04` = revision định nghĩa prompt; bộ 12 nhãn đổi thì phải thống nhất với data). Prompt của LLM tự sinh từ `taxonomy.py`. Schema `clause_output_v3.json` có enum chép tay nhưng `tests/contract/test_schema_enums.py` sẽ **fail** nếu lệch `CLAUSE_LABELS`.
3. Sửa test khóa (`tests/test_data_lead_review.py`, `tests/unit/test_clause_taxonomy_freeze.py` — hằng `FROZEN_*` và fingerprint), enum trong schema (sinh từ code hoặc có test đối chiếu — DEC-20), `docs/CLAUSE_TAXONOMY.md`, và các file dùng nhãn cứng (`tests/unit/test_clause_taxonomy.py`, `mock_clause_service.py`, `eval/fixtures/build_synthetic.py`).
4. Không xóa/đổi tên nhãn khi đã có dữ liệu annotate theo bản cũ mà chưa thống nhất với Người 2.
