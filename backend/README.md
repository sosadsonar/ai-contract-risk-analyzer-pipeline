# Backend development mock

Use Python 3.12 from the repository root:

```sh
python -m pip install -e '.[dev]'
APP_ENV=dev uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
python -m pytest
```

The dev-only `/api/v1/sessions` API returns a de-identified sample result; it does not analyze uploads, call Gemini, enforce production admission/lease/quota, or persist files. Demo/eval startup is disabled until the real pipeline is integrated. Do not deploy this mock as a production analyzer.

For local PDF-only validation (no API session, LLM call, persistent artifacts, or final result),
call `app.session.local_validation.validate_local(path, display_name, Settings())` from
Python with `backend/` on the import path. It returns extraction, scope, masking, and
segmentation artifacts in memory; invalid inputs raise `ValidationReject`. The caller
owns and removes the input PDF. Run the real-PDF examples with
`python -m pytest tests/integration/test_local_validation.py`.
The dev sample API is separate and must not be treated as analysis of a real PDF.
