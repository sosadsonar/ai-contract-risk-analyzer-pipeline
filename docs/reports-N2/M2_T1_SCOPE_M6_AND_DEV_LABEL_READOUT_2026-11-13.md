# T1 M2 scope, Dev label scoring, and D2 M6 — 2026-11-13

## Input integrity

The supplied T1 v04 CSV SHA-256 is `40b2182a2ff8dcf18ca8813163a544816a8ac3a7a7bf6793785d19c94322c497`; the supplied D2 40-rating CSV SHA-256 is `68a04ce79a67c21889705aa8635d8e738d69d6cf8b40ad96c31fc508fc41f4b4`. Both matched. The M6 output IDs and all non-rating output fields match the existing D2 Dev candidate packet. Neither T1 nor T2 contract text was opened. No runtime rule was tuned on held-out data.

## T1 closed-corpus Gold v02

The T1 v04 CSV was copied intact into the Data repository's ignored `data/intake/private/m2_review_submissions_2026-11-13/`. `scripts/export_t1_m2_gold_closed_corpus.py` validated 1,494 distinct role rows, paired source spans, reviewer identities and statuses, three positive citations against the 16-node corpus, and the exact scope distribution. It created `data/intake/restricted/T1_m2_risk_gold_v02/` without touching v01 or the candidate packet.
The v04 packet has exactly the same 1,494 IDs and values in every pre-existing column as submitted v03; only `scope_status` and `notes` were added.

The v02 manifest records 3 `IN_CORPUS_ADJUDICATED` risk rows, 1,474 `IN_CORPUS_VERIFIED` no-risk rows, and **17 `CORPUS_V1_SCOPE_EXCEPTION` rows**, with exact excluded role IDs and offsets. `evaluation_ready=true` applies **only to this attested 16-node corpus scope**; the 17 excluded units must be removed from the M2 evaluation population. The source CSV has no separate `CONTEXT` status. Its three scope values assign every row; the absence of `CONTEXT` was not independently verified against T1 text. Do not silently treat an overlapping prediction with a different clause ID as an in-scope FP; resolve that alignment before scoring T1.
The M2 scorer accepts the manifest's `excluded_corpus_scope_regions`. The v5 policy merges nearby regions within 15 characters per document/role. A prediction is omitted when at least half of its span, half of a merged exclusion region, or half of their IoU overlaps; smaller positive overlaps remain in the score and appear in `partial_excluded_overlap_warnings`. The result records `excluded_overlap_predictions` and `merged_excluded_regions`. Callers must pass the regions when evaluating T1; the manifest alone does not automatically change a score. The scorer also excludes explicit `CONTEXT` Gold records and can require non-null Gold spans.

## Dev M2/M2b label scope

The Dev runner now reports D1 and D2 separately. D2 evaluation retains only the two Article 17 labels annotated in its Gold. Its 18 predictions in four unannotated background labels are counted separately as `predictions_on_d2_labels_without_gold` and excluded from D2 and combined label-scoped denominators. Combined Dev is the D1 v03 4-label slice plus D2 Article 17 2-label slice. It contains 74 Gold triples over six labels, but D1 and D2 share base documents, so it is not an independent-sample acceptance score.

| Slice | Gold | Predicted in scope | TP / FP / FN | Macro-F1, present Gold labels | M2b basis on TP |
|---|---:|---:|---:|---:|---:|
| D1 Dev v03 | 14 | 18 | 13 / 5 / 1 | 0.776961 | 13/13 |
| D2 Dev Article 17 | 60 | 58 | 58 / 0 / 2 | 0.987179 | 58/58 |
| Combined label-scoped Dev | 74 | 76 | 71 / 5 / 3 | **0.847034** | 71/71 |

JSON: `reports/evaluation/d1_m7_offline_pr26_2026-11-09/m2_m2b_dev_label_scoped_2026-11-13.json`. The combined score clears 0.80 **only on six supported Dev labels**, using a deterministic local rule baseline. It is not full-taxonomy product M2, independent model prediction, or held-out acceptance.

The five D1 FP are two `REST_AND_LEAVE` and three `BONUS_BENEFITS` predictions. The D1 FN is `HDLD003_C013::EMPLOYEE` (`UNILATERAL_CHANGE`). A source-only rule already emits `UNILATERAL_CHANGE` from its containing prediction span, but the one-to-one aligner maps that large span to neighboring `HDLD003_C012`; one prediction cannot become two TP. The `REST_AND_LEAVE` FP spans show the same local keyword relation as the TP, so a document-specific suppression would be leakage. No additional rule was added merely to force 5 FP / 1 FN to zero; resolving these requires a documented annotation/segmentation policy or independent source-grounded evidence.

## D2 40-rating packet

The rating CSV was copied intact to the restricted D2 Dev review folder. `scripts/score_m6_review_packet.py` produced `reports/evaluation/d1_m7_offline_pr26_2026-11-09/m6_d2_dev_human_adjudicated_2026-11-13.json`: 40 outputs; human A/B agreement **0.975**, Cohen κ **0.8947368421**; judge/adjudicated agreement **1.0**, κ **1.0**; numeric threshold flag true. The scorer marks `D2_DEV_REVIEW_AGREEMENT_NOT_M6_ACCEPTANCE` and `acceptance_scope_verified=false` because this is the D2 Dev detector-candidate packet, not an independently verified product-output acceptance sample.

## Required next decisions

1. Approve a policy for predictions overlapping excluded T1 regions when predicted and Gold clause IDs differ, before any held-out M2 score.
2. Review D1's remaining source/segmentation mismatch on Dev; retain the locked T1/T2 boundary.
3. Build a 40-output product M6 packet with independently rated output explanations and recommendations if official M6 acceptance is required.

## 13/11 v5 metadata clarification

The T1 full segmentation Gold has 842 references. T1 clause-label Gold and the M2 packet have the same 747 clause IDs; the remaining 95 segmentation-only references are absent from the M2 packet. The Data manifest now records their 95 refs and 190 role-projected IDs, with `context_scope_rows_in_packet=0`. It would be incorrect to claim 190 `CONTEXT` rows were present in the 1,494-row M2 CSV.

The new metadata-only M1 diagnostic is `reports/evaluation/d1_m7_offline_pr26_2026-11-09/m1_t1_metadata_granularity_diagnostic_2026-11-13.json`. Using the frozen `rules_v1.3` IoU≥0.80 full segmentation report, group A (HDLD005/010/012/013) has 184 Gold, 167 predicted, 98 TP, **F1 0.558405**; group B has 658 Gold, 223 predicted, 131 TP, **F1 0.297389**. The requested 0.6725/0.2871 values were not reproduced from this common denominator. Full segmentation Gold starts at offset 0 in both groups; later starts are from the separate M2 candidate packet. No T1 contract text was read or model rule changed.

The frozen M2 JSON retains the one-to-one D1 13 TP/5 FP/1 FN, D2 58/0/2, combined 71/5/3, and adds `d1_error_breakdown` with metadata-only IDs/offsets. No document-specific rule was introduced.

## Verification

Data exporter compiled; its synthetic scope tests and existing D1 converter tests passed (5/5). Focused pipeline M2/M6 tests passed before the scope helper, and its additional scope tests passed afterward. The full non-LLM pipeline suite exited 0 before the scope helper, with 16 private-submodule tests skipped. `git diff --check` exited 0 with line-ending warnings only. The frozen `dev_injection_candidate.py` SHA-256 remains `a6d7a1fb2663511764606d0ad9075246df423a282eb96c406fca342c6644f438`.
