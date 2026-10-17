<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: Phụ lục B. .env.example | 937 ký tự | trước: 23_phu-luc-a-json-schema-mau.md | sau: 25_phu-luc-c-prompt-contract.md -->

# Phụ lục B. .env.example

```dotenv
APP_ENV=dev
GEMINI_API_KEY=
GEMINI_MODEL_ID=
DEV_LLM_PROVIDER=gemini
LLM_TIMEOUT_SECONDS=30
LLM_AUTO_RETRY=1
CLAUSE_BATCH_SIZE=20
RISK_BATCH_SIZE=6
LLM_PARALLELISM=2
MAX_UPLOAD_MB=10
MAX_PDF_PAGES=30
MAX_DOCX_CHARS=100000
MAX_CLAUSES=150
SESSION_TTL_MINUTES=60
EXPIRED_TOMBSTONE_HOURS=24
# Bắt buộc cấu hình trước demo sau cost model D1:
DAILY_LLM_CALL_QUOTA=
SESSION_CALL_RESERVE=
RATE_LIMIT_UPLOADS=5
RATE_LIMIT_WINDOW_SECONDS=600
DATA_GRAPH_ENABLED=true
CLAUSE_GRAPH_ENABLED=true
RETRIEVAL_SEED_K=3
RETRIEVAL_FINAL_K=8
GRAPH_MAX_NEIGHBORS_PER_SEED=4
GRAPH_MAX_CHILDREN_PER_SEED=2
CLAUSE_GRAPH_MAX_RELATED=3
CLAUSE_GRAPH_MAX_CONTEXT_CHARS=6000
SCOPE_TITLE_SCAN_CHARS=1000
TEMPERATURE=0.0
LEGAL_CORPUS_DIR=./data/legal_corpus
OPS_DB_PATH=./runtime/ops_metadata.sqlite3
```

Demo profile phải chạy 1 worker. `APP_ENV=eval` bypass runtime quota/rate nhưng vẫn cần Gemini model/key và eval cost ledger.
