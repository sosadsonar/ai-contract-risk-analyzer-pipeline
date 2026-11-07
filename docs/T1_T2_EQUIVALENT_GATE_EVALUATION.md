# T1/T2 equivalent-gate evaluation

This document explains the reproducible technical baseline delivered with
`reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/result.json`. It is a
diagnostic run, not MS-4/MS-5 acceptance.

## Dataset boundaries

| Set | Documents | Gold used here |
| --- | --- | --- |
| D1 Dev | HDLD001–004 | 183 reviewed clauses; the only training source for the M7 baseline |
| D2 Dev | HDLD001–004 | 30 injected errors; source of the frozen narrow Article 17 M5 rule |
| T1 unique 8 | HDLD005, 007–013 | Independent real/template documents; excludes the HDLD005/006 granularity pair duplicate |
| T1 real 9 | HDLD005–013 | 842 segmentation spans, 747 full clause-label spans, 340 genuine clauses |
| T1 composite 10 | HDLD005–014 | Real 9 plus synthetic calibration control HDLD014 |
| T2 | HDLD005–013 | 872 segmentation spans and 30 injected errors |

The three T1 slices are reported separately. HDLD014 is synthetic and must not
be described as a tenth independently sourced contract. The equivalent intake
gate counts 4 restricted sources, 5 public templates, and this 1 synthetic
control. The older source-only gate is a different historical check.

## Reproduce the run locally

The Data repository holds Gold and raw text outside the public Pipeline Git
history. Obtain the authorized local Data checkout, then run from the Pipeline
repository root on Windows:

```powershell
$env:PYTHONPATH = 'backend;.'
$dataRoot = '<path-to-authorized-local-Data-repository>'
.venv\Scripts\python.exe scripts/evaluate_t1_t2_equivalent_gate.py `
  --data-root $dataRoot `
  --output 'reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/result.json'
```

The run writes prediction details only under the Data repository's ignored
`data/intake/restricted/` directory. The public JSON contains aggregate scores,
confidence intervals, counts, method names, and input hashes. It must not be
used to reconstruct or publish raw contract text.

`data/legal_corpus/manifest.yaml` is `APPROVED`. Its three checksums use the LF
bytes committed to Git, as required by `.gitattributes`; changing line endings
or the pinned corpus content makes the loader fail closed.

## What the metrics mean

The runner uses 1,000 document-cluster bootstrap resamples with seed 0. M7
predictions come from a fixed character TF-IDF nearest-neighbor model fitted
only on D1. M5 uses the previously frozen D2 Article 17 rule. Neither path
reads T1/T2 Gold labels while predicting. The runner then opens Gold to score.

| Metric | Current T1 real 9 or T2 result | Interpretation |
| --- | --- | --- |
| M1 | T1 0.3713; T2 0.3431 | Below the BRD acceptance threshold |
| M3a | T1 747/747; T2 387/387 | Corpus membership and legal-effectivity check only; not relevance |
| M4 | T1 undefined; T2 19/19 emitted outputs | Exact quotes/offsets among emitted outputs, not missed risks |
| M5 | T2 12/30 | Below threshold |
| M7 | T1 0.3377 on 747 spans; 0.5442 on 340 genuine clauses | Both below threshold |
| M8 | T2 Recall@5: 15/30 graph off; 14/30 graph on | Both below threshold; graph expansion reduced recall here |
| Privacy §7.3 | T1 21/21 PII; 62/63 fields retained | T2 privacy uses a derived, not separately adjudicated reference |

M2, M3b, and M6 are not run in this report. See `acceptance_readout.md` next to
the JSON for thresholds and confidence intervals. The failing and undefined
measurements remain open work; no T1/T2 tuning is authorized by this report.

## Maintainer checks

Run `python -m pytest -q`, `ruff check` on tracked Python files, and
`git diff --check` before review. In a clean checkout without the restricted
Data submodule, integration tests requiring private source text are skipped;
that is a test-environment limitation, not proof of data-level acceptance.
Reviewers should check that no raw contract, Gold CSV, restricted prediction,
SQLite database, API key, or real PII is staged.
