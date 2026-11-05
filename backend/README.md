# Backend development mock

Use Python 3.12 from the repository root:

```sh
python -m pip install -e '.[dev]'
APP_ENV=dev uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
python -m pytest
```

The dev-only `/api/v1/sessions` API returns a de-identified sample result; it does not analyze uploads, call Gemini, enforce production admission/lease/quota, or persist files. Demo/eval startup is disabled until the real pipeline is integrated. Do not deploy this mock as a production analyzer.

For local PDF/DOCX validation (no API session, LLM call, persistent artifacts, or final result),
call `app.session.local_validation.validate_local(path, display_name, Settings())` from
Python with `backend/` on the import path. It returns extraction, scope, masking, and
segmentation artifacts in memory; invalid inputs raise `ValidationReject`. The caller
owns and removes the input document. Exercise both document formats with
`python -m pytest tests/integration/test_local_validation.py tests/unit/test_docx_extraction.py`.
The dev sample API is separate and must not be treated as analysis of an uploaded file.

`RunLogWriter(db).record_stage(...)` records only typed stage metadata in SQLite.
`DailyQuota(db, quota, reserve)` increments the UTC-day counter before each
actual provider request; admission alone checks whether enough calls remain
for a new session, so retries may exceed the quota for an admitted session.
`EvalCostLedger(path_to_csv, app_env="eval")` records attempts and completion
costs separately from the product database; `summary()` reports call/token/cost
totals, including unfinished attempts. Neither ledger accepts contract text.
The dev fixture runner does not emit fake stage logs; production stage logging
waits for the real orchestrator. No demo quota number is chosen yet.
