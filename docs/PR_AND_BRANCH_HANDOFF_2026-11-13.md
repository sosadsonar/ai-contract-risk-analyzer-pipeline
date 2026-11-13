# PR and branch handoff — 13/11/2026

## Scope and remote PR state

This is a local handoff. No push, merge, PR close, or PR creation was performed.
The branch inventories below are local commits reachable from `HEAD` but absent
from the locally cached `origin/main` at the time of this report. Re-fetch and
compare before any remote action because remote branches may have advanced.

## v8 local update

Pipeline commit `44006c0` adds the opt-in session route, bounded PDF runner
factory, real Git `app_commit` pin, M6 result-row projection, Dev-only M8
primary/oracle diagnostic, tests and metadata-only reports. The Data branch has
no v8 changes. `PRODUCT_RUNNER_ENABLED=false` remains the default. The v8
route test uses fake providers and makes no Gemini request. Do not advertise it
as a production M2 accuracy result.

M8-primary is 66/74 Graph Off and Graph On. Six D1 misses persist under D1
oracle clause labels (8/14 hits in each graph mode); D2 has no adjudicated
clause-label Gold, so the 74-case oracle score is unavailable. All eight
primary misses have zero direct map weight and cannot be reached from the
current graph seeds. The approved 16-node corpus and its checksums were not
changed. Proposed law mappings/edges require source-backed legal review.

The M6 projection yielded 168 complete review-shaped rows from four D1 Dev
envelopes with fake risk judgments, enough to select 40 structurally. It did
not create new human ratings or change the prior 40-output D2 Dev review.
Full `.venv` tests pass on both repos (Pipeline exit 0, 16 skips; Data 143
passed and 2 subtests), full Ruff checks are green, and staged whitespace
check is clean. T1/T2 were not opened or rerun.

- Data: `D:\DHCN\Nam3_Ky1\CVDKHMT\ai-contract-risk-analyzer`, branch `codex/data-intake-status-2026-10-27`.
- Pipeline: `D:\DHCN\Nam3_Ky1\CVDKHMT\ai-contract-risk-analyzer-pipeline-eval-integration`, branch `codex/d1-m7-handoff-2026-11-09`.
- GitHub read on 13/11/2026: [Data PR #19](https://github.com/24021368-DucAnh/ai-contract-risk-analyzer/pull/19) is **open**, head `15f4247801f6adc3241d996769803d66229cfacf`, base `main`; [Data PR #20](https://github.com/24021368-DucAnh/ai-contract-risk-analyzer/pull/20) is **open**, head `eb259a3b7d9274e7d874f6fc2e0d7cfca1d8058d`, base `main`. They are not the same head as this local Data branch.
- The numerically matching [Pipeline PR #19](https://github.com/sosadsonar/ai-contract-risk-analyzer-pipeline/pull/19) and [Pipeline PR #20](https://github.com/sosadsonar/ai-contract-risk-analyzer-pipeline/pull/20) were already merged. Do not close those as if they were the open Data PRs.

## Data branch commits, chronological

| Commit | Date | Subject |
| --- | --- | --- |
| `ab07db8421ba8b546864884bf62a24d4050c7a02` | 2026-11-02 | data: record circular 10 source registry recheck |
| `1bf817d6b66e653acd1db99aba0eac54a7044c74` | 2026-11-06 | data(t1): finalize manual clause labels v08, equivalent gate v1 and feasibility reports |
| `dc4358737a10250fa0cf583a10be3945b4e09524` | 2026-11-06 | data: tag genuine T1 clean clauses and lint tracked code |
| `cad8d066ee48c78113b587f0e7ff1c6f6e4b8b99` | 2026-11-13 | feat(data): version T1 M2 scope metadata utilities |
| `a824795f60e93d9f99d9b3acbb2eeb8678c287d3` | 2026-11-13 | style(data): satisfy Ruff in week5 QC notebook |

## Pipeline branch commits, chronological

| Commit | Date | Subject |
| --- | --- | --- |
| `bbd6355d8b39abbeb1f64b5a4d37f40d864c8135` | 2026-11-07 | eval(m7): extract deterministic span alignment and D1 reconciliation plan |
| `e33cd3b6463a085a8973c6fde077cdb088f091d6` | 2026-11-07 | eval(d1): audit saved span geometry against canonical gold |
| `fff53ef1967cc6d68d04a9d8bd82fadf6f1da430` | 2026-11-07 | eval(d1): pin canonical source parity and Gold coverage |
| `3bf8accf427ae7d1898de1dbc8403c1960161382` | 2026-11-07 | eval(d1): prepare private pipeline-canonical Gold candidate |
| `ab70537b3480e65bbaa29f912baa1a84aab13d3c` | 2026-11-07 | eval(d1): rebase saved prediction offsets into private candidate |
| `4229dd63f7692c705fa5a483f0efbb68daffb40a` | 2026-11-07 | eval(d1): add dual-mode span diagnostics and exact canonical rebase |
| `70855f33534344c39fa329ee3def40fd3e5a534d` | 2026-11-07 | eval(d1): add fail-closed offline M7 scorer for saved labels |
| `1be72db268287d61b708168541c896f4351b4a99` | 2026-11-09 | docs(eval): audit D1 M7 canonical handoff and Data Lead gates |
| `40ecfc41c575cf774d67e2e23315d2755ddd94d5` | 2026-11-09 | feat(segmenter): split repeated plus list items on D1 Dev |
| `fa208b86eac401c92dc9e29479d625337c97ba99` | 2026-11-09 | docs(eval): probe preamble eligibility on D1 only |
| `e5da1b4cf86beb1fc7cacb3de36afdaea07af698` | 2026-11-09 | fix(eval): authenticate D1 prediction rebase inputs |
| `d3744d6791532c8642171550376682c52ccdc4cd` | 2026-11-09 | fix(segmenter): gate plus-list candidate after D2 regression |
| `b99a6474b914c7a49891398e189731dbeb1ce09c` | 2026-11-10 | docs(data): record local D1 D2 and privacy gate handoff |
| `3c4199404753a71481852d8e2e01ad31297661cf` | 2026-11-12 | feat(clause): add opt-in rules v1.3 parser boundaries |
| `9ddffee90c94eeb1641c479edaa3b1556cbb21db` | 2026-11-12 | feat(clause): filter classification eligibility from source text |
| `40e4805658b8d20840bbadea8e9f76f3717fc3bd` | 2026-11-12 | feat(risk): attach bounded clause graph context |
| `42d852ca3d94f204ef931526aaeac8388c65c315` | 2026-11-12 | test(m6): score blinded human review packet |
| `67e3ad1baee662cb8e1b8ddbad7401d2ca44efd4` | 2026-11-12 | feat(eval): score approved Dev risk slices and freeze M5 |
| `f806a4a48a828d9a60ca22b57bdcc2329c55360f` | 2026-11-12 | feat(dev): assemble validated risk output and sanitize advice |
| `162f8d8b0886abfe3abb507bc1deb1f636c7af6c` | 2026-11-12 | docs(eval): report Dev metrics and scoped delivery |
| `3f96bdfb32e7571608eca9f9c7e1d347063e408c` | 2026-11-12 | fix(eval): align contained Dev clauses and calibrate M6 proxy |
| `fde757c78f0c444e731672169f2f7c001591050c` | 2026-11-13 | fix(eval): score M2 by annotated labels and excluded regions |
| `63316c99cbc305d1b46790951dcdfacfb932261c` | 2026-11-13 | docs(eval): record M2 Gold scope and M6 Dev evidence |
| `237ecb917d41ede7e719dd443fc43191f0979a5b` | 2026-11-13 | feat(eval): restore privacy validation and record Dev/T1 diagnostics |
| `2af8539885bd6eaa74c68b4dcb575f31c96cf6f8` | 2026-11-13 | docs(eval): summarize project acceptance and open gates |
| `b35f427bec93927b4cd52d48055293e66cf354e9` | 2026-11-13 | feat(result): assemble final result envelope and close tracked lint |
| `28759b051138cc5bbb0cf7c44ca44e7c1e3bfa7d` | 2026-11-13 | docs(eval): record v7 acceptance and PR handoff |
| `44006c0` | 2026-11-13 | feat(pipeline): wire opt-in product runner and audit Dev M8 |

The commit containing this handoff document is necessarily reported in the delivery
message; a commit cannot contain its own hash. All restricted Gold and review CSVs
remain outside Git under `.gitignore`.

## Dirty files preserved outside the v7 PR slice

These are the exact local Git status entries at document generation. The v7
acceptance report is excluded because it is being prepared for a scoped commit.
No entry below was staged for this handoff. Some pre-existing untracked Python
experiments received formatting fixes to make local Ruff green; they remain
untracked and are not silently admitted to a PR.

### Pipeline (111 entries)

```text
 M docs/D1_D2_PLUS_BOUNDARY_REVIEW_2026-11-09.md
 M docs/DATA_LEAD_CONTINUATION_2026-11-10.md
 M docs/TDD_AI_Labor_Contract_Risk_Analyzer_v0.3.md
 M scripts/audit_d1_rules_v12_geometry.py
?? docs/D1_D2_BOUNDARY_DECISION_2026-11-10.md
?? docs/D1_D2_RATIFIED_POLICY_IMPLEMENTATION_2026-11-10.md
?? docs/D1_D2_RULES_V13_AND_TEACHER_TARGETS_2026-11-10.md
?? docs/D1_GOLD_STRUCTURE_AND_M5_JSON_DIFF_2026-11-10.md
?? docs/D1_HDLD003_HDLD004_FOLLOWUP_2026-11-10.md
?? docs/D1_REFERS_TO_AUDIT_AND_ORCHESTRATOR_WIRING_2026-11-12.md
?? docs/INDEPENDENT_AUDIT_FIXES_AND_W5_REFERS_TO_2026-11-12.md
?? docs/M1_CLAUSE_ONLY_AND_M5_VOCAB_2026-11-11.md
?? docs/M1_CONTEXT_NEUTRAL_AND_M5_STRUCTURAL_FIX_2026-11-11.md
?? docs/M1_D1_D2_GRANULARITY_AND_M5_ART17_VS_ART62_2026-11-11.md
?? docs/M1_M5_ART17_GENERALIZATION_AND_T1_V13_2026-11-10.md
?? docs/M1_M5_BLANK_LINE_AND_T2_READOUT_2026-11-10.md
?? docs/M1_M5_FINAL_LOCK_READOUT_2026-11-11.md
?? docs/M1_M5_M6_FOCUSED_IMPLEMENTATION_2026-11-10.md
?? docs/M1_M5_M6_FOCUSED_REVIEW_2026-11-10.md
?? docs/M1_PAIRWISE_LINE_AND_M5_STATUTORY_2026-11-11.md
?? docs/M1_PER_DOC_AND_M5_BLIND_FLAGS_2026-11-11.md
?? docs/M1_SCOPED_SPLIT_AND_M5_FULL_FLAGS_2026-11-11.md
?? docs/M2_M6_SCOPED_TECHNICAL_SLICE_2026-11-11.md
?? docs/M2_M6_WORKER_HANDOFF_TO_CODEX_2026-11-12.md
?? docs/M2_M6_WORKER_RESPONSE_TO_REVIEW_2026-11-11.md
?? docs/M5_REGRESSION_AND_D1_FULL_GOLD_PROBE_2026-11-10.md
?? docs/M6_40_OUTPUT_RATINGS_TEMPLATE.csv
?? docs/WEEKLY_DATA_LEAD_REPORT_2026-11-02_TO_10.md
?? docs/WEEKLY_DATA_LEAD_REPORT_2026-11-09_TO_10.md
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/context_neutral_saved_2026-11-10.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/d1_clause_graph_and_context_trace_2026-11-12.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/d1_d2_iou_band_2026-11-10.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/d1_d2_single_line_granularity_2026-11-11.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/d1_full_paragraph_probe_2026-11-10.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/d1_gold_structure_2026-11-10.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/dev_m1_iou08_2026-11-10.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/lodo_local_classifier_2026-11-10.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/m1_ascii_dieu_context_neutral_2026-11-11.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/m1_clause_only_2026-11-11.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/m1_context_neutral_2026-11-11.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/m1_geometry_focus_2026-11-11.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/m1_pairwise_body_probe_2026-11-11.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/m1_pairwise_dev_2026-11-11.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/m1_relaxed_pair_probe_2026-11-11.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/m1_short_field_probe_2026-11-11.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/m1_short_field_scoped_probe_2026-11-11.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/min160_offline_scores_2026-11-10.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/remaining_geometry_features_2026-11-10.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/rules_v12_boundary_delta_2026-11-10.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/rules_v12_min160_geometry_2026-11-10.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/rules_v13_blank_line_iou_band_2026-11-10.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/rules_v13_blank_line_m1_2026-11-10.json
?? reports/evaluation/d1_m7_offline_pr26_2026-11-09/t1_rules_v13_m1_readonly_2026-11-10.json
?? reports/evaluation/d2_plus_parser_regression_2026-11-09/boundary_delta.json
?? reports/evaluation/d2_plus_parser_regression_2026-11-09/min160_gold_v02_geometry_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/d2_article17_clause_guard_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/d2_article17_debt_context_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/d2_article17_legacy_monotonic_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/d2_article17_monotonic_guard_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/d2_article17_restored_debt_context_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/d2_article17_statutory_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/d2_article17_structural_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/d2_article17_vocab_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/d2_article17_vs_art62_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/d2_dev_m5_causes_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/d2_m5_final_lock_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/d2_risk_candidate_article17_generalized_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/d2_risk_candidate_probe_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/d2_risk_candidate_probe_v04_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/dev_article17_vs_art62_emissions_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/dev_candidate_emissions_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/dev_m5_final_lock_emissions_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/dev_statutory_emissions_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/m5_miss_causes_readonly_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/t2_article17_blind_flags_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/t2_article17_blind_flags_full_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/t2_article17_clause_guard_readonly_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/t2_article17_legacy_monotonic_readonly_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/t2_article17_monotonic_guard_readonly_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/t2_article17_restored_debt_context_readonly_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/t2_article17_statutory_readonly_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/t2_article17_structural_readonly_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/t2_article17_vocab_readonly_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/t2_article17_vs_art62_readonly_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/t2_m5_final_lock_readonly_2026-11-11.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/t2_risk_candidate_article17_generalized_readonly_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/t2_risk_candidate_readonly_2026-11-10.json
?? reports/evaluation/t1_t2_equivalent_gate_eval_2026-11-06/t2_risk_candidate_readonly_v04_2026-11-10.json
?? scripts/audit_d1_clause_graph_context.py
?? scripts/audit_d1_d2_granularity.py
?? scripts/audit_d1_gold_span_structure.py
?? scripts/audit_d1_remaining_geometry.py
?? scripts/audit_d2_plus_boundary_delta.py
?? scripts/audit_dev_candidate_emissions.py
?? scripts/audit_m1_context_neutral.py
?? scripts/audit_m1_geometry_focus.py
?? scripts/audit_m1_pairwise_dev.py
?? scripts/audit_m5_blind_flags.py
?? scripts/audit_segmentation_iou_band.py
?? scripts/audit_t1_rules_v13_m1.py
?? scripts/audit_t2_m5_misses_readonly.py
?? scripts/build_m6_dev_candidate_packet.py
?? scripts/evaluate_m5_candidate.py
?? scripts/probe_d1_full_paragraphs.py
?? scripts/probe_m1_short_fields.py
?? scripts/propose_d2_plus_gold_v02.py
?? scripts/publish_d2_gold_v02.py
?? scripts/score_d1_context_neutral.py
?? scripts/score_d1_lodo_local.py
?? scripts/score_d1_offline_eligibility_projection.py
?? scripts/score_m1_clause_only.py
```

### Data (102 entries)

```text
 M .gitignore
 M data/intake/legal_ocr_structure_index_receipts_2026-11-02.csv
 M data/intake/legal_source_receipts_2026-11-02.csv
 M data/processed/clauses_v06.csv
 M docs/LEGAL_SOURCE_DISCOVERY_2026-11-02.md
 M docs/N2_DATA_LEAD_STATUS_2026-11-01.md
 M docs/N2_DATA_LEAD_UPDATE_2026-11-02.md
 M docs/W4_LEGAL_DATA_ACQUISITION_2026-10-29.md
 M docs/clause_taxonomy_v03.md
 M scripts/audit_d1_segmentation_queue.py
 M scripts/audit_preview_dataset.py
 M scripts/build_legal_article_review_queue.py
 M scripts/validate_gold_segmentation.py
 M tests/test_audit_preview_dataset.py
 M tests/test_build_legal_article_review_queue.py
 M tests/test_d1_segmentation_queue_audit.py
 M tests/test_source_intake.py
 M tests/test_validate_dataset.py
 M tests/test_validate_gold_segmentation.py
?? data/intake/d1_clause_label_parity_audit_2026-11-05.json
?? data/intake/legal_source_receipts_2026-11-04.csv
?? data/intake/owner_signoff_queue_2026-11-05.csv
?? data/intake/owner_signoff_queue_2026-11-05.csv.pre-owner-signoff
?? data/processed/clauses_v08_candidate_manifest.json
?? data/processed/contracts_metadata_v08_candidate.csv
?? data/processed/contracts_metadata_v08_source_snapshot.csv
?? data/processed/d2_injection_authoring_v01_candidate.csv
?? data/processed/d2_injection_authoring_v01_candidate_manifest.json
?? data/releases/v06-rc1/frozen/docs/annotation_guideline.md
?? data/splits/d1_v06_candidate_2026-11-05.json
?? data/splits/d1_v06_candidate_2026-11-05_v02.json
?? data/w7_dev_candidate_2026-11-05.yaml
?? data/w7_dev_candidate_2026-11-05_v02.yaml
?? data/w7_dev_candidate_D1_2026-11-05.json
?? data/w7_dev_candidate_D1_2026-11-05_v02.json
?? data/w7_dev_candidate_D2_2026-11-05.json
?? data/w7_dev_candidate_inputs_2026-11-05.json
?? data/w7_owner_baseline_D1_v01.json
?? data/w7_owner_baseline_D1_v02.json
?? data/w7_owner_baseline_D1_v03.json
?? data/w7_owner_baseline_D2_v01.json
?? data/w7_owner_baseline_v01.yaml
?? data/w7_owner_baseline_v02.yaml
?? data/w7_owner_baseline_v03.yaml
?? data/w7_owner_baseline_v04.yaml
?? data/w7_owner_baseline_v05.yaml
?? data/w7_owner_baseline_v06.yaml
?? data/w7_owner_baseline_v07.yaml
?? docs/CONTRACT_INVENTORY_CHECK_2026-11-04.md
?? docs/D1_SEGMENTATION_COVERAGE_AUDIT_2026-11-04.md
?? docs/N2_T1_EQUIVALENT_PATHS_2026-11-04.md
?? docs/annotation_guideline_alignment_draft_2026-11-05.md
?? docs/superpowers/plans/2026-10-20-repository-file-organization.md
?? reports/intake/t1_gate_blockers_2026-11-06.json
?? reports/intake/t1_manual_label_review_2026-11-06.json
?? reports/intake/t1_source_provenance_local_audit_2026-11-06.json
?? scripts/apply_d1_m2_delta_decisions.py
?? scripts/apply_t1_manual_labels.py
?? scripts/augment_d2_m5_art17_predictions.py
?? scripts/build_clauses_v08_candidate.py
?? scripts/build_d1_m1_review_packet.py
?? scripts/build_d1_m2_risk_annotation_worksheet.py
?? scripts/build_d1_privacy_review_packet.py
?? scripts/build_d1_split_candidate.py
?? scripts/build_d2_segmentation_review_packet.py
?? scripts/build_hdld014_synthetic_candidate.py
?? scripts/build_owner_review_manifest.py
?? scripts/build_t1_privacy_review_worksheet.py
?? scripts/convert_d1_label_review_to_gold.py
?? scripts/convert_d1_m1_review_to_gold.py
?? scripts/convert_d1_m2_review_to_gold.py
?? scripts/convert_d1_privacy_review_to_gold.py
?? scripts/convert_d2_injection_review_to_gold.py
?? scripts/convert_d2_segmentation_review_to_gold.py
?? scripts/convert_t1_clause_labels_to_gold.py
?? scripts/convert_t1_privacy_review_to_gold.py
?? scripts/convert_t1_t2_segmentation_review_to_gold.py
?? scripts/convert_t2_injection_review_to_gold.py
?? scripts/finalize_d1_privacy_preserve_owner_rule.py
?? scripts/import_reviewed_clauses_v08.py
?? scripts/propose_t1_keyword_labels.py
?? scripts/propose_t1_three_tier_labels.py
?? scripts/propose_t1_three_tier_labels_v02.py
?? scripts/propose_t1_three_tier_labels_v03.py
?? scripts/upgrade_d1_m2_review_worksheet_v02.py
?? scripts/validate_clauses_v08_candidate.py
?? scripts/validate_d2_injection_authoring_candidate.py
?? tests/test_augment_d2_m5_art17_predictions.py
?? tests/test_build_d1_m1_review_packet.py
?? tests/test_build_d1_m2_risk_annotation_worksheet.py
?? tests/test_build_d1_privacy_review_packet.py
?? tests/test_convert_d1_label_review_to_gold.py
?? tests/test_convert_d1_m1_review_to_gold.py
?? tests/test_convert_d1_m2_review_to_gold.py
?? tests/test_convert_d1_privacy_review_to_gold.py
?? tests/test_convert_d2_injection_review_to_gold.py
?? tests/test_convert_d2_segmentation_review_to_gold.py
?? tests/test_convert_t1_t2_segmentation_review_to_gold.py
?? tests/test_convert_t2_injection_review_to_gold.py
?? tests/test_exact_offset_rebase.py
?? tests/test_validate_clauses_v08_candidate.py
?? tests/test_validate_d2_injection_authoring_candidate.py
```

## Review and PR checklist

1. Refresh both remotes and inspect branch divergence in a separate clean worktree. Do not rebase or reset either dirty worktree. Compare the exact PR #19/#20 head SHA with the local Data branch and decide whether each open PR is still useful, superseded, or requires review changes.
2. For Data PR #19 and #20, inspect file lists, privacy boundary, Gold status wording, required reviews and CI at their current remote heads. If a PR is superseded, close it only after its reviewer/owner records that decision; closing is distinct from merging. Do not upload `data/intake/restricted/` or private review CSVs.
3. For a Pipeline PR, create a clean branch from current `main` in a separate worktree, then select only the needed, dependency-ordered commits from the table above. Verify the resulting diff contains no unrelated dirty/untracked files, no raw contract text, no runtime SQLite database and no restricted Gold. The current Pipeline branch contains a long history of experiments and should not be published wholesale without review.
4. Run the mandatory `.venv` tests, Ruff and `git diff --check` on the clean PR branch. Confirm the candidate detector SHA-256 remains `a6d7a1fb2663511764606d0ad9075246df423a282eb96c406fca342c6644f438`. Check `final_result_v1`/PII tests and distinguish its fake-provider structural proof from held-out M2 accuracy.
5. Keep the PR description honest: T1 M1 and M2 teacher targets remain unmet, M6 is a D2 Dev review result, and the frozen T1 M2 score was not rerun. Require independent review before any merge. No remote action is authorized by this handoff alone.
