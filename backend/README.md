# Backend PDF upload

Python **3.11+** is required by pinned SQLAlchemy 2.1.1. Install dependencies
from `requirements.txt`, copy `.env.example` to `.env`, set DATABASE_URL,
apply the existing Alembic migration, and run `uvicorn app.main:app` from
the backend directory. The documented database is PostgreSQL.

## Resource budgets

`POST /api/v1/contracts/upload` retains its successful response fields:
`id`, `filename`, `status`, and `text_length` (Unicode character count).
Extracted text preserves page separators and whitespace. Limits reject
the entire upload; text is never silently truncated.

Defaults, configurable through `.env` (restart workers after changes):

- PDF: 10 MiB, 100 pages, 300,000 extracted Unicode characters.
- Whole multipart body: PDF byte limit + 64 KiB, counting every part and
  header. Actual received bytes are checked even without Content-Length.
- Body deadline: 30 seconds. Parser deadline: 10 seconds after process spawn.
- Parser memory: 512 MiB per disposable child. Windows uses a Job Object
  committed-memory limit; POSIX uses RLIMIT_AS (virtual address space).
  Unsupported/unavailable OS enforcement rejects upload instead of parsing.
- Per API worker: 2 active uploads, 30 admitted attempts in a sliding minute.
  Admission precedes multipart parsing. Excess requests are rejected without
  queueing or reading their bodies. Parser slots also cover direct helper calls.
- Shared database: at most 1,000 contracts and 10,000,000 stored text characters.
  Existing rows count. PostgreSQL transaction advisory locking serializes quota
  checking and insertion across workers. Contended locks reject immediately;
  storage statements have a 3-second timeout. SQLite is supported for local tests;
  other database dialects fail closed because quota locking is not implemented.

Limits bound this upload path; they are not authentication or tenant quotas.
Multiple API workers multiply in-process rate/concurrency limits. Configure
deployment ingress limits and worker count to fit server RAM/CPU/disk. Database
quotas bound application rows/text, not external database logs/backups/physical
disk use. Raise limits deliberately for a reviewed deployment; zero cannot
disable a budget. Quota exhaustion requires operator retention/cleanup decisions.

Native parsing occurs in a disposable process, off the API event loop. Timeout
kills and reaps it. Native diagnostics go to the null device; only bounded JSON
text/error output reaches the API. Cancellation waits for underlying processing
to finish before releasing admission and the request's database session.

## Responses

- 400: non-PDF suffix (unchanged), missing filename or filename over 255 characters.
- 408: body deadline exceeded.
- 413: file or whole request byte budget exceeded.
- 422: invalid PDF, page/text/native-memory budget, parser timeout, unsupported
  NUL text, or no extractable text. Malformed PDFs previously escaped as 500;
  they now receive a controlled 422. Empty-text 422 is preserved.
- 429: worker's minute-rate limit.
- 503: upload/parser capacity, unavailable memory enforcement, storage lock
  contention/quota, or unsupported quota database. Retry-After accompanies
  route capacity rejections; storage exhaustion needs operator intervention.

## Tests

Install exact runtime dependencies plus `httpx==0.28.1` for TestClient, then
run from repository root with the same interpreter:

```powershell
python -m compileall -q backend/app backend/tests
python -m unittest discover -s backend/tests -v
python -m unittest discover -s tests -v
```

PostgreSQL tests require `TEST_POSTGRES_URL` pointing to a **disposable** database
where the test login may create schemas. They create/drop only a random
`upload_test_<uuid>` schema. Without that variable the three PostgreSQL tests
are skipped, so SQLite results alone do not verify cross-worker quota locking.

Verification on Windows/Python 3.12.14 uses pinned runtime dependencies and a
temporary PostgreSQL 18.6 localhost server. Tests use generated harmless PDFs,
real memory allocation denial in a child, a real sleeping child for timeout,
actual multipart disk-spool cleanup, cancellation, normal response/text, and
concurrent PostgreSQL inserts. POSIX OS enforcement is implemented but was
not executed in this Windows environment. Hostile/native exploit PDFs and
production load tests were not run.

Known existing warnings: TestClient's httpx deprecation and the model's
datetime.utcnow deprecation. Neither is changed by this focused security fix.
