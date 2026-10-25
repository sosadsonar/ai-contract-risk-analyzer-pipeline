# Contributing Guide

Repo này là code của **AI Contract Risk Analyzer** (`ai_pipeline/`, sau này thêm `backend/`, `frontend/`, `notebooks/`).
Dữ liệu nằm ở **repo riêng** (`data`, do Người 2 quản lý) và được gắn vào đây dưới dạng **git submodule** tại `ai_pipeline/data/`.

```
ai-contract-risk-analyzer-pipeline/     <- repo này (code)
├── ai_pipeline/
│   ├── services/       clause_extraction_service.py (LEGACY, bị thay ở C-01), llm_clients.py,
│   │                   mock_clause_service.py (mock theo clause_output_v3)
│   ├── utils/          (trống; `text_processing.py`/`document_router` đã bị xóa ở C-02)
│   ├── eval/           eval_segmentation.py, fixtures/ (dữ liệu tổng hợp để smoke-test)
│   ├── schemas/        clause_output_v3.json (C-04, xong); risk_output_v1.json do Người 3 thêm
│   ├── test_pipeline.py, test_llm_pipeline.py
│   └── data/           <- SUBMODULE = repo `data` (chỉ đọc từ repo này)
├── .github/workflows/ci.yml   CI: pytest (py3.10/3.12), smoke, ruff, test cần submodule (xem §3.1)
├── backend/app/
│   ├── domain/errors.py     ValidationReject (N4 bổ sung các lỗi còn lại vào cùng file)
│   ├── core/enums.py        Role, SessionStatus, Stage, Severity, EvidenceStatus, BasisType, *EdgeType (MỘT nguồn, DEC-20)
│   └── clause/              taxonomy.py (12 nhãn + validate_labels, MỘT nguồn, đóng băng MS-1),
│                            structure_parser.py (C-02, 5 pattern heading), segmenter.py (C-01 a, `segment()`)
├── tests/{unit,contract,integration,fixtures}/   unit: taxonomy (+freeze), structure_parser, segmenter, PII, risk;
│                            contract: enum ↔ schema; integration: segmenter trên hợp đồng thật (cần submodule);
│                            fixtures/segmentation/*.txt
├── docs/               CLAUSE_TAXONOMY.md (con trỏ), CLAUSE_TAXONOMY_FREEZE.md (đóng băng MS-1 + đa nhãn), DATA_PLAN.md
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

| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `LLM_PROVIDER` | `gemini` hoặc `qwen_ollama` | `gemini` |
| `GEMINI_API_KEY` | Key Gemini, lấy miễn phí tại <https://aistudio.google.com/apikey> | (bắt buộc nếu dùng Gemini) |
| `GEMINI_MODEL` | Tên model Gemini | `gemini-2.0-flash` nếu không đặt (`.env.example` đặt `gemini-2.5-flash`) |
| `OLLAMA_HOST` | Địa chỉ Ollama | `http://localhost:11434` |
| `OLLAMA_MODEL` | Model Qwen | `qwen2.5:7b` |

**Dùng Gemini:** điền `GEMINI_API_KEY`, giữ `LLM_PROVIDER=gemini`.

> ⚠️ Gói miễn phí và model local chỉ dùng cho phát triển với dữ liệu **đã de-identify**; demo/đánh giá dùng Gemini Flash gói trả phí và model id phải đặt tường minh, không dựa mặc định ngầm (SRS DEC-19, NFR-SEC-06; SRS C-07 sẽ thay cách cấu hình này).

**Dùng Qwen local (không cần key):**

1. Cài Ollama: <https://ollama.com/download>
2. `ollama pull qwen2.5:7b` (máy yếu dùng `qwen2.5:3b` và đặt `OLLAMA_MODEL=qwen2.5:3b`)
3. Đặt `LLM_PROVIDER=qwen_ollama` trong `.env`

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
ruff check backend/app/clause tests/unit   # lint (xem §3.1 cho danh sách đường dẫn bị chặn cứng)
```

**Script legacy** (sẽ chuyển sang pytest ở C-17/C-19 phần 2). Các script `sys.path` tự thêm `backend/` nên chạy được từ `ai_pipeline/`:

```bash
cd ai_pipeline

# Không cần API key: chạy router với kết quả LLM giả lập, kiểm nhãn bằng validate_labels
python test_pipeline.py

# Cần API key hoặc Ollama: gọi LLM thật (service legacy, chỉ dùng với dữ liệu đã de-identify)
python test_llm_pipeline.py
```

Đổi provider tạm thời cho một lần chạy:

```bash
# macOS/Linux
LLM_PROVIDER=qwen_ollama python test_llm_pipeline.py
# Windows PowerShell
$env:LLM_PROVIDER="qwen_ollama"; python test_llm_pipeline.py
```

| Lỗi thường gặp | Nguyên nhân / cách xử lý |
|---|---|
| `ModuleNotFoundError: app` / `services` | Script legacy chạy ngoài `ai_pipeline/` → `cd ai_pipeline`; với pytest chạy từ thư mục gốc |
| `Thiếu GEMINI_API_KEY` | Chưa tạo `.env` ở thư mục gốc hoặc chưa điền key |
| `ai_pipeline/data/` rỗng | Chưa kéo submodule → `git submodule update --init --recursive` |
| Nhãn không thuộc 12 nhãn | Đang dùng nhãn cũ (8 nhãn v1). Xem `docs/CLAUSE_TAXONOMY.md` |
| Không kết nối được Ollama | Chưa chạy Ollama hoặc chưa `ollama pull` model |

### 3.1 CI (`.github/workflows/ci.yml`)

Mỗi push vào `main` và mỗi PR chạy tự động; **PR đỏ thì không merge** (§4.5). CI không dùng API key, không gọi LLM, không đụng Postgres.

| Job | Làm gì | Chạy lại ở máy bạn |
|---|---|---|
| `test` (py3.10 và 3.12) | `pip install -e '.[dev]'`, `pytest --ignore=tests/test_data_lead_review.py`, rồi `python test_pipeline.py` (smoke) | `pytest --ignore=tests/test_data_lead_review.py` và `cd ai_pipeline && python test_pipeline.py` |
| `data` | Kéo submodule rồi chạy `tests/test_data_lead_review.py` + `tests/integration`. **Không kéo được submodule thì chỉ cảnh báo**, không đỏ CI. Repo data private: tạo PAT chỉ đọc và đặt secret `SUBMODULE_TOKEN` | `pytest tests/test_data_lead_review.py tests/integration` |
| `lint` | `ruff check` trên danh sách đường dẫn đã sạch (**bắt buộc**) + toàn repo (**chỉ cảnh báo**, còn lỗi cũ) | `ruff check <đường dẫn>` |

**Test gọi LLM thật (tùy chọn, thủ công).** `tests/llm/test_llm_live.py` (marker `llm`) gọi Gemini bằng văn bản tổng hợp; `pytest` thường tự bỏ qua (`-m "not llm"`). Chạy ở máy: đặt `GEMINI_API_KEY` trong `.env` rồi `pytest -m llm tests/llm -s`. Chạy trên GitHub:

1. Repo → Settings → Secrets and variables → Actions → **New repository secret**: tên `GEMINI_API_KEY`, dán key (nên dùng key riêng cho CI, có hạn mức thấp). Tùy chọn: tab *Variables* đặt `GEMINI_MODEL`; hoặc tạo Environment tên `llm` và đặt secret ở đó để yêu cầu người duyệt.
2. Actions → CI → **Run workflow** → tick `run_llm`. Kết quả JSON hiện ở Summary của job `llm-live` và tải được ở artifact `llm-result`.

Job này không bao giờ chạy trên push/PR (fork không có secret, tránh tốn quota). Không đưa hợp đồng thật vào test này (AI_CONTEXT §3).

Khi dọn xong lint một file/thư mục, thêm nó vào danh sách bắt buộc trong `ci.yml`. File/test mới phải sạch lint ngay từ đầu (dòng ≤100 ký tự, import đã sắp). Test cần dữ liệu thật phải tự `skip` khi thiếu submodule (xem `tests/integration/`), không làm job `test` đỏ.

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
