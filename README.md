# AI Contract Risk Analyzer — Pipeline

Hệ thống AI hỗ trợ phân tích hợp đồng lao động tiếng Việt: tách điều khoản, phân loại (12 nhãn), gán mức rủi ro và cờ cần review.

## Chạy thử nhanh

```bash
git clone --recurse-submodules https://github.com/sosadsonar/ai-contract-risk-analyzer-pipeline.git
cd ai-contract-risk-analyzer-pipeline

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .'[dev]'

cp .env.example .env        # rồi điền GEMINI_API_KEY (hoặc dùng Qwen local qua Ollama)

cd ai_pipeline
python test_pipeline.py          # không cần API key
python test_llm_pipeline.py      # gọi LLM thật
```

Hướng dẫn đầy đủ (cài đặt, `.env`, quy trình Git, submodule dữ liệu, đổi taxonomy): xem [CONTRIBUTING.md](CONTRIBUTING.md).

## API phiên tuần 2 (chỉ môi trường dev)

Từ thư mục gốc: `python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`. API tạo UUIDv4, giữ phiên trong RAM, lease xử lý một phiên, giới hạn upload streaming 10 MiB, rate theo HMAC IP, tombstone SQLite 24 giờ. SQLite tại `OPS_DB_PATH` chỉ chứa metadata; không phục hồi nội dung phiên sau restart. `RATE_LIMIT_HMAC_SALT` vắng trong dev được tạo ngẫu nhiên mỗi process; cấu hình salt cố định nếu cần rate ổn định qua restart. Dev chỉ áp dụng quota khi có cả `DAILY_LLM_CALL_QUOTA` và `SESSION_CALL_RESERVE`; runner sample không gọi provider, không trừ counter.

Kết quả `final_result_v1` hiện là **fixture dev**, không phải phân tích file tải lên. `APP_ENV=demo/eval` vẫn fail-fast đến khi extraction, LLM và legal corpus được tích hợp; không dùng API dev để đánh giá hợp đồng thật.

## Tài liệu

- [docs/CLAUSE_TAXONOMY.md](docs/CLAUSE_TAXONOMY.md) — 12 nhãn clause (con trỏ tới taxonomy nguồn; không còn tier)
- [docs/DATA_PLAN.md](docs/DATA_PLAN.md) — hiện trạng dataset và con trỏ tới BRD §8.2
- `ai_pipeline/data/` — submodule dữ liệu (repo `data` của Người 2)
