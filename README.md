# AI Contract Risk Analyzer — Pipeline

Hệ thống AI hỗ trợ phân tích hợp đồng lao động tiếng Việt: tách điều khoản, phân loại (12 nhãn), gán mức rủi ro và cờ cần review.

## Chạy thử nhanh

```bash
git clone --recurse-submodules https://github.com/sosadsonar/ai-contract-risk-analyzer-pipeline.git
cd ai-contract-risk-analyzer-pipeline

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .'[dev]'

cp .env.example .env        # rồi điền GEMINI_API_KEY (hoặc dùng Qwen local qua Ollama)

python scripts/smoke_pipeline.py # toàn pipeline với provider giả, không cần API key
# test gọi LLM thật / Ollama: xem CONTRIBUTING.md §3 (pytest -m llm | llm_local)
```

Chạy kiểm thử tự động: `pytest` từ thư mục gốc (CI chạy cùng lệnh trên mỗi push/PR — `.github/workflows/ci.yml`).

Hướng dẫn đầy đủ (cài đặt, `.env`, CI, quy trình Git, submodule dữ liệu, đổi taxonomy): xem [CONTRIBUTING.md](CONTRIBUTING.md).

## API phiên tuần 2 (chỉ môi trường dev)

Từ thư mục gốc: `python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`. API tạo UUIDv4, giữ phiên trong RAM, lease xử lý một phiên, giới hạn upload streaming 10 MiB, rate theo HMAC IP, tombstone SQLite 24 giờ. SQLite tại `OPS_DB_PATH` chỉ chứa metadata; không phục hồi nội dung phiên sau restart. `RATE_LIMIT_HMAC_SALT` vắng trong dev được tạo ngẫu nhiên mỗi process; cấu hình salt cố định nếu cần rate ổn định qua restart. Dev chỉ áp dụng quota khi có cả `DAILY_LLM_CALL_QUOTA` và `SESSION_CALL_RESERVE`; runner sample không gọi provider, không trừ counter.

Từ tuần 5 (X-19) API chạy **pipeline thật** (`backend/app/pipeline.py`: extraction → scope → che PII → segmentation → Clause Graph → LLM #1 → retrieval → LLM #2 → citation validation → assembly) khi có provider: `DEV_LLM_PROVIDER=fake` (offline, tất định, chỉ để smoke/ghép frontend), `local` (Ollama) hoặc `gemini` có `GEMINI_API_KEY` + `GEMINI_MODEL_ID`. Dev không có provider vẫn trả fixture mẫu. `APP_ENV=demo/eval` luôn chạy pipeline thật và fail-fast khi thiếu key/model/quota/reserve/salt hoặc corpus chưa `APPROVED`.

## Tài liệu

- [docs/CLAUSE_TAXONOMY.md](docs/CLAUSE_TAXONOMY.md) — 12 nhãn clause (con trỏ tới taxonomy nguồn; không còn tier)
- [docs/CLAUSE_TAXONOMY_FREEZE.md](docs/CLAUSE_TAXONOMY_FREEZE.md) — đóng băng MS-1 + chính sách đa nhãn (OI-10)
- [docs/DATA_PLAN.md](docs/DATA_PLAN.md) — hiện trạng dataset và con trỏ tới BRD §8.2
- `ai_pipeline/data/` — submodule dữ liệu (repo `data` của Người 2)
