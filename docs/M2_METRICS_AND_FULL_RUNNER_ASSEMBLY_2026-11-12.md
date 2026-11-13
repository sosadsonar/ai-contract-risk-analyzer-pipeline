# M2/M2b metrics and Dev runner assembly — 12/11/2026

## Boundaries and freeze

The M5 detector file was restored byte-for-byte to SHA-256 `a6d7a1fb2663511764606d0ad9075246df423a282eb96c406fca342c6644f438`. It contains 260 content lines plus a terminating newline (`split("\n")` yields 261 elements); the **byte hash**, not a line-count convention, is the freeze criterion. The legacy M5→canonical risk-label helper now resides in the new M2 metrics module. The frozen detector body was not modified and T2 was not read or rerun. No Gemini call, destructive Git command, staging, commit, merge or push was performed.

## M2 and M2b evaluation module

Added `ai_pipeline/evaluation/metrics/risk_classification.py` alongside M7 `clause_classification.py`. TDD §18.3 defines Gold risk records with clause reference, role, risk label and basis; §18.4 names the M2 metric as Macro-F1 over `(clause, role, risk label)` and M2b basis accuracy on M2 true positives. The new module validates 21 canonical risk labels and two roles, handles one-to-one same-ID and optional IoU≥0.50 span alignment within each document, and reports TP/FP/FN, precision/recall/F1 and support for each label. It reports separate macro scores over present Gold labels and all 21 labels (zero division = 0), micro scores, coverage, and Wilson 95% CI for M2b basis accuracy when there are true positives. `document_id` may namespace repeated clause IDs across contracts. No real M2 score was produced; Gold and independent predictions still need a versioned evaluation run.

The helper `map_dev_candidate_to_risk_labels()` is explicit and diagnostic only: `EMPLOYEE_OBLIGATIONS_DISCIPLINE`→`DISCIPLINE_OBLIGATION`, `DEPOSIT_DOCUMENT_HELD` unchanged. It does not transform M5 Gold or imply a clause-taxonomy→risk-taxonomy mapping.

## Dev/eval runner

Inspected available components: `BaselineRetriever` and a closed legal corpus exist; `app.integrations.risk_assembler.assemble_risk_output()` already computes severity from the taxonomy, validates canonical span equality and filters role-incompatible labels. There is no standalone citation-validator or advice-sanitizer module in `backend/app/`.

Extended the **injected** `make_pipeline_runner()` to accept an approved corpus and optional retriever. Retrieval produces per-clause public-law candidates for the Risk Adapter. After `analyze_risks()`, the runner keeps only citation IDs present in that clause's candidate list **and** effective in the supplied corpus on the analysis date. If none remain, it downgrades to `INSUFFICIENT_EVIDENCE`; the existing assembler then sets severity to null. If the model supplied citations that were all rejected, the runner replaces the unsupported legal explanation with a neutral message; this is a narrow fail-closed measure, not a general advice sanitizer. It assembles a canonical `risk_merged_v1` object and adds a separate Dev result view with `quote`, `start_char`, `end_char`, and `related_clause_ids`. Quote/span originate from segmentation, not model output. A synthetic approved corpus and two FakeProviders cover valid citation, outside-candidate citation, expired citation, code-derived severity, original-text span invariant and retrieval candidate propagation.

The runner returns `dev_pipeline_result_v1`, **not** the product `final_result_v1` envelope. Default `Orchestrator(store, lease)` still uses `sample_result`; no production activation occurred. Advice sanitization, full product response/disclaimer, product quota lifecycle, and semantic citation relevance remain separate gates. If no approved corpus is supplied, the runner cannot validate a citation as effective and therefore downgrades it; it must not claim legal support from a bare candidate ID. The existing assembler drops role-invalid labels and marks `need_review`; review this behavior against the current TDD before product activation.

## Verification

Interpreter: `C:\Users\Admin\OneDrive\Documents\ChatGPT\Các vấn đề\ai-contract-risk-analyzer-pipeline\.venv\Scripts\python.exe`; `PYTHONPATH=backend`.

| Command | Result |
|---|---|
| `pytest tests/unit/test_risk_classification_metrics.py tests/unit/test_dev_injection_candidate.py -q` | 26 passed, exit 0 |
| `pytest tests/unit/test_orchestrator_pipeline_integration.py -q` | 6 passed, exit 0 |
| `pytest tests/unit -q` | Collection interrupted by missing `pymupdf` in `test_pdf_extraction.py`; full unit suite **not passed** |
| `pytest tests/unit --ignore=tests/unit/test_pdf_extraction.py tests/integration/test_mock_sessions.py tests/integration/test_session_admission.py -q -o addopts=''` | 625 passed, 3 skipped, exit 0; skips require an absent data submodule |
| `git diff --check` | Exit 0 for tracked diffs, no whitespace errors; Git emitted LF→CRLF notices for three unrelated tracked files. Untracked files are outside this check. |

## Changed-file SHA-256

| File | SHA-256 |
|---|---|
| `backend/app/risk/dev_injection_candidate.py` (restored M5 freeze) | `a6d7a1fb2663511764606d0ad9075246df423a282eb96c406fca342c6644f438` |
| `ai_pipeline/evaluation/metrics/risk_classification.py` | `491841c7bb276ced67ef14e835e907bf0bd75f49bf3cb3699337c0d012baf56b` |
| `tests/unit/test_risk_classification_metrics.py` | `cfd3721185020438a507354dcaa77010398c39576cf9d07f0458b83bd65d687c` |
| `tests/unit/test_dev_injection_candidate.py` | `33aa9f205ada49cf7764d6383c83543b965fe39b8cefac1b71567b07eef64690` |
| `backend/app/session/pipeline_runner.py` | `da5b9ed8bbf91151b42b3eed10dcce59d6c86c300c215c743e14518b55a48d25` |
| `tests/unit/test_orchestrator_pipeline_integration.py` | `0ed5a831b8ba784f10d3aa4bdd17e7097e3674a7a3b6b4dc04d1eb901098a164` |
| `backend/app/session/orchestrator.py` (injected runner from prior slice) | `63a74d06c915e3721a233a0ec4c87e285c6d4f71f99501f3a865f9e95c82e373` |

The report cannot contain its own stable SHA-256; hash it separately after finalization. All hashes above are working-tree file hashes, not committed-object IDs.

## Follow-up on 12/11/2026

The subsequent approved Dev slice added `sanitize_advice_sentences()` to the injected runner and ran the versioned D1+D2 Dev evaluation. Its current code hashes, full test result, and actual metrics are in `FINAL_DEV_METRICS_AND_COMMIT_REPORT_2026-11-12.md` and `m2_m2b_dev_evaluation_2026-11-12.json`; the earlier hashes and "advice sanitization remains" statement above describe the pre-follow-up snapshot only.
