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

## Tài liệu

- [docs/CLAUSE_TAXONOMY.md](docs/CLAUSE_TAXONOMY.md) — 12 nhãn clause và tier rủi ro
- [docs/DATA_PLAN.md](docs/DATA_PLAN.md) — kế hoạch dữ liệu
- `ai_pipeline/data/` — submodule dữ liệu (repo `data` của Người 2)
