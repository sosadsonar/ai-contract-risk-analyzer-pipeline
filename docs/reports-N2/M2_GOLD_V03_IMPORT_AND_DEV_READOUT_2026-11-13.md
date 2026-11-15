# M2 Gold import and Dev readout — 2026-11-13

## Input and authorization

The owner confirmed that `Minh_N1` participated in this review round; future rounds may use a different approval policy. The two supplied CSV SHA-256 values matched the handoff exactly. Both source CSVs were copied without edits to the Data repository's ignored `data/intake/private/m2_review_submissions_2026-11-13/`. No T1/T2 contract text was opened, no Git push/merge was performed, and `dev_injection_candidate.py` retained SHA-256 `a6d7a1fb2663511764606d0ad9075246df423a282eb96c406fca342c6644f438`.

## Gold outputs

- D1 `data/intake/restricted/D1_m2_risk_gold_v03/`: existing converter `--check-only` passed, then wrote four document JSONs and a manifest. It contains 14 positive items: `UNILATERAL_CHANGE` 9, `BONUS_BENEFITS` 3, `WORKING_HOURS_OVERTIME` 1, `REST_AND_LEAVE` 1. The v02 directory was untouched. The 366-row worksheet includes 14 `RISK`, 352 `NO_RISK`, 18 `CONTEXT` role rows with blank spans, and 14 `CORPUS_V1_SCOPE_EXCEPTION` notes.
- T1 `data/intake/restricted/T1_m2_risk_gold_v01/`: nine document JSONs and a manifest were exported from the submitted 1,494-row CSV. Three positive items have exact existing citation IDs. The manifest records `GOLD_ADJUDICATED_STORAGE_ONLY`, `evaluation_ready=false`; the 1,491 `NO_RISK` rows cannot be separated into verified negatives versus corpus-scope exceptions because the supplied CSV has no `notes` or scope field. No T1 rule tuning or T1 evaluation was performed. The v02 candidate packet was untouched.

The current D1 converter validates three distinct identities and complete risk slots; the T1 export additionally checked 1,494 unique role units, paired roles and spans, review status, citations, and positive count. File hashes and structural validity do not independently prove reviewer provenance or legal relevance.

## M2/M2b Dev diagnostic

The Dev-only source-text baseline now emits three extra canonical labels for open company benefit rules, overtime discretion, and discretionary compensatory rest. It does not read Gold or document IDs at runtime. The M2 metric has an explicit `CONTEXT` exclusion and an opt-in requirement to exclude null Gold spans for span-alignment scoring. The Dev runner uses D1 v03, D2 v02, and the span requirement.

| Slice | Gold tuples | Predictions | TP / FP / FN | Macro-F1 on present Gold labels | Macro-F1 on all 21 labels | M2b basis on TP |
|---|---:|---:|---:|---:|---:|---:|
| D2 Dev | 60 | 76 | 58 / 18 / 2 | 0.987179 | 0.094017 | 58/58 |
| D1 v03 + D2 Dev | 74 | 94 | 71 / 23 / 3 | 0.661123 | 0.188892 | 71/71 |

Aggregate JSON: `reports/evaluation/d1_m7_offline_pr26_2026-11-09/m2_m2b_dev_evaluation_v03_2026-11-13.json`. In the combined slice, `UNILATERAL_CHANGE` has 8 TP / 8 FP / 1 FN; the other new D1 labels have 3/9/0 (`BONUS_BENEFITS`), 1/1/0 (`WORKING_HOURS_OVERTIME`), and 1/5/0 (`REST_AND_LEAVE`). D2 only has Gold for two Article 17 labels, so the extra predictions on other labels count as FP in the raw score without proving they are false risks. D1 and D2 share underlying documents. This local rule diagnostic is not an independent product M2 run or teacher-target acceptance.

## Verification and next gate

Focused pipeline tests: 44 passed, exit 0. Data D1 converter tests: 3 passed. Full pipeline pytest with `-m 'not llm and not llm_local'` exited 0; 16 tests were skipped because the private data submodule is unavailable. `git diff --check` exited 0 (Git emitted only line-ending warnings). Before treating T1 as evaluation-ready, add a versioned field for corpus-scope exceptions and determine whether those rows are excluded, unresolved, or evaluated under a wider corpus. Review the 23 combined Dev FP and three FN on D1/D2 Dev only; then run an independent pinned M2 model. Do not tune on T1/T2.
