# Contributing Guide

Repo này là code của **AI Contract Risk Analyzer** (`ai_pipeline/`, sau này thêm `backend/`, `frontend/`, `notebooks/`).
Dữ liệu nằm ở **repo riêng** (`data`, do Người 2 quản lý) và được gắn vào đây dưới dạng **git submodule** tại `ai_pipeline/data/`.

```
ai-contract-risk-analyzer-pipeline/     <- repo này (code)
├── ai_pipeline/
│   ├── config/         taxonomy.py (12 nhãn, đóng băng), labeling.py (rule multi-label, đóng băng),
│   │                   risk_routing.py (tier rủi ro, ngưỡng, của Risk AI)
│   ├── services/       clause_extraction_service.py, llm_clients.py, mock_clause_service.py
│   ├── utils/          text_processing.py
│   ├── eval/           eval_segmentation.py, fixtures/ (dữ liệu tổng hợp để smoke-test)
│   ├── schemas/        clause_output_v2.json, risk_output_v1.json, explanation_output_v1.json,
│   │                   analysis_response_v1.json
│   ├── test_pipeline.py, test_llm_pipeline.py
│   └── data/           <- SUBMODULE = repo `data` (chỉ đọc từ repo này)
├── docs/               CLAUSE_TAXONOMY.md, DATA_PLAN.md
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

**Dùng Qwen local (không cần key):**

1. Cài Ollama: <https://ollama.com/download>
2. `ollama pull qwen2.5:7b` (máy yếu dùng `qwen2.5:3b` và đặt `OLLAMA_MODEL=qwen2.5:3b`)
3. Đặt `LLM_PROVIDER=qwen_ollama` trong `.env`

**Kiểm tra `.env` không bị commit:** chạy `git status`, file `.env` **không được** xuất hiện. Nếu xuất hiện, dừng lại và báo nhóm trước khi commit.

> Lỡ commit/push API key? Coi như key đã lộ: **vào trang cấp key thu hồi và tạo key mới ngay**, rồi báo nhóm. Xóa commit không đủ vì key vẫn nằm trong lịch sử.

---

## 3. Chạy thử

Các script test import theo kiểu `from config.taxonomy import ...` / `from config.risk_routing import ...` nên **phải chạy từ trong thư mục `ai_pipeline/`**:

```bash
cd ai_pipeline

# Không cần API key: chạy router + routing với kết quả LLM giả lập
python test_pipeline.py

# Cần API key hoặc Ollama: gọi LLM thật
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
| `ModuleNotFoundError: config` | Đang chạy ngoài thư mục `ai_pipeline/` → `cd ai_pipeline` |
| `Thiếu GEMINI_API_KEY` | Chưa tạo `.env` ở thư mục gốc hoặc chưa điền key |
| `ai_pipeline/data/` rỗng | Chưa kéo submodule → `git submodule update --init --recursive` |
| `Nhãn 'XXX' không có trong RISK_TAXONOMY_MAP` | Đang dùng nhãn cũ (8 nhãn). Xem `docs/CLAUSE_TAXONOMY.md` |
| Không kết nối được Ollama | Chưa chạy Ollama hoặc chưa `ollama pull` model |

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
- Ít nhất 1 người review.
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
| **Dữ liệu thật** (HDLD001–003, 140 clause) | `ai_pipeline/data/` (submodule) | Đánh giá thật. Cần `raw_text` + `start_offset/end_offset` (Người 2 đang bổ sung) trước khi đo được Clause Detection F1. |

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

## 7. Đổi taxonomy (nhãn clause / tier rủi ro)

Taxonomy ảnh hưởng đến 3 người (Người 1: prompt/pipeline, Người 2: annotation, Người 3: risk tier), nên:

1. Mở PR riêng (`docs/...` hoặc `ai/...`), **review bắt buộc của Người 1, 2, 3**.
2. Sửa `LABEL_DEFINITIONS` trong `ai_pipeline/config/taxonomy.py` (Người 1, đóng băng) **và** `RISK_TAXONOMY_MAP` trong `ai_pipeline/config/risk_routing.py` (Người 3, tự chốt). Prompt của LLM tự sinh từ `taxonomy.py`; import `risk_routing.py` lỗi ngay nếu hai bảng lệch nhau.
3. Cập nhật `docs/CLAUSE_TAXONOMY.md`, và các file dùng nhãn cứng (`test_pipeline.py`, `mock_clause_service.py`, `eval/fixtures/build_synthetic.py`).
4. Không xóa/đổi tên nhãn khi đã có dữ liệu annotate theo bản cũ mà chưa thống nhất với Người 2.