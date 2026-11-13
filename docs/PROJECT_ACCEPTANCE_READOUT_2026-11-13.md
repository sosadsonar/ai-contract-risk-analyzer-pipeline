# Project 3 acceptance readout — 13/11/2026

## Decision

**The project has not met all three teacher targets.** D2 Dev clause extraction passes
0.85, but T1 held-out M1 is 0.3718. The frozen Dev M2 heuristic scores 0.3333
Macro-F1 on only two supported T1 risk labels, below 0.80; the 21-label M2 model
is not yet evaluated. The 40-output human agreement is from D2 Dev and is not
the final M6 acceptance sample. No T1/T2 source text is reproduced here.

| Metric | Dev evidence | Held-out evidence | Acceptance interpretation |
| --- | --- | --- | --- |
| M1, IoU ≥ 0.80 | D2 v02: 228/250 TP, 253 predicted, F1 **0.90656**. D1 full granularity: 151/329 TP, F1 0.54710. | T1 rules_v1.3: 229/842 TP, 390 predicted, F1 **0.37175**. | Dev D2 passes; T1 does not. D1/D2/T1 annotation granularity differs. |
| M2 risk classification | D1: 13 TP/5 FP/1 FN, present-label Macro-F1 0.77696 (4 labels). D2 Article 17: 58/0/2, 0.98718 (2 labels). Combined: 71/5/3, **0.84703** (6 labels; all-21 Macro-F1 0.24201). | **One read-only T1 v02 run**: 1 TP/6 FP/2 FN, Micro-F1 0.20000, present-label Macro-F1 **0.33333** (2 labels; all-21 Macro-F1 0.03175). | Frozen Dev heuristic, not the product M2 classifier. Fails held-out target; 19 labels lack T1 positive support. D1 and D2 share source contracts. |
| M2b basis type | Dev combined 71/71 correct *among matched true positives*. | T1 1/1 correct *among matched true positives*. | Conditional measure with very small held-out support; not overall basis accuracy. |
| M3a citation validity | D1 injected runner with fake providers: 168/168 citation IDs valid in approved corpus. | Earlier equivalent-gate T1 top-1 retrieval: 747/747, membership/effectivity only. | Structural validity only; no proof of citation relevance or a real model's legal accuracy. |
| M4 quote/offset | D1 injected runner: 168/168 exact quote and source offset. | Earlier T2 technical run: 19/19 exact on emitted risks; T1 had zero emitted risks in that run. | Structural invariant on emitted records, not risk recall. |
| M5 injected-error recall | D2 Dev: 30/30. | Frozen T2 read-only: 26/30. | Recall on Article 17 injections; not M2 F1. |
| M6 human agreement | D2 Dev 40 outputs: human A/B 0.975; Cohen κ 0.89474; judge/adjudicated agreement 1.0, κ 1.0. | No held-out M6 packet scored. | Dev packet passes its agreement check; formal M6 acceptance remains pending. |
| M7 clause taxonomy | D1 leave-one-document-out local baseline Macro-F1 0.51062 (95% CI 0.25458–0.83893). | Earlier T1 full 747-row Macro-F1 0.33775; 340 genuine-clause subset 0.54416. | Below 0.80; separate from M2 risk taxonomy. |
| M8 Recall@5 | Paired D1 v03 14 + D2 60 citation cases, final_k=8: Graph Off **66/74 = 0.89189**, Graph On **66/74 = 0.89189**. | Earlier T2 30 cases: Graph Off 15/30, Graph On 14/30. | Dev uses D1-trained local clause-label predictions on D1/D2 derivatives, so it is in-sample. Graph gives no Dev gain and regresses on the earlier T2 diagnostic. |
| Privacy | Data-repo privacy Gold validator restored; Data full suite passes. | Earlier T1 high/standard sensitivity recall 1.0 each; preserve 62/63. | Technical privacy evidence, not a new held-out privacy run in this change. |

## Scope and implementation facts

- Data repo `T1_m2_risk_gold_v02/manifest.json` declares 1,494 reviewed role rows, 3 positive risk items, 17 corpus-scope exclusions and 190 segmentation-only CONTEXT role references. The M2 packet itself has zero CONTEXT rows. The frozen T1 evaluator passes `excluded_corpus_scope_regions` into the scorer, excludes CONTEXT candidate rows, and reports zero excluded-overlap predictions and zero partial-overlap warnings. Its prediction boundaries come from the pre-existing AI-proposed `T1_segmentation_candidate_v01` (747 CLAUSE rows), not segmentation Gold.
- T1 source bytes were read only in memory for hash verification and the one requested inference pass; HDLD006 required NFC normalization to match its canonical Gold hash. No T1/T2 contract text was printed or put in any report. No detector rule was edited after that pass.
- `dev_injection_candidate.py` SHA-256 remains `a6d7a1fb2663511764606d0ad9075246df423a282eb96c406fca342c6644f438`. Frozen `dev_m2_baseline.py` SHA-256 for this T1 pass: `22dd956fd87b3b12f06c78cace91228b5248d6432332fa52cc028dba6e510087`.
- `make_pipeline_runner()` on all four D1 contracts completed with local fake providers and produced `dev_pipeline_result_v1`, 168 records with `risk_basis`, 168/168 valid taxonomy severity, 168/168 validated citation IDs and 168/168 exact quotes. Provider payloads passed a PII absence check. Fake risk outputs prove the assembly route only. **The product `final_result_v1` envelope is not produced by this runner**, so the requested final-result acceptance condition remains open.
- M8's paired Dev query uses the approved Gold citation ID and a D1-trained TF-IDF clause-label predictor. Two role items for one D2 injection reuse the same query; confidence intervals and scores must be read with that correlation and in-sample training in mind.

## Verification and delivery

- Data full `.venv` pytest: **143 passed, 2 subtests passed**, exit 0, no collection errors.
- Pipeline full `.venv` pytest: exit 0 with 16 skips for unavailable private submodule fixtures; no failures. Focused dataset/metric/runner suite: 33 passed.
- Ruff on all changed/new Python files: pass. Repository-wide Ruff: **35 existing findings** in Pipeline and **20 existing findings** in Data, outside this slice; the full-lint gate is therefore open.
- `git diff --check`: exit 0. The dirty worktrees contain unrelated tracked and untracked work; only explicitly listed files are eligible for staging.
- Relevant local commits: Data `cad8d066ee48c78113b587f0e7ff1c6f6e4b8b99`; Pipeline `fde757c78f0c444e731672169f2f7c001591050c`, `63316c99cbc305d1b46790951dcdfacfb932261c`, v6 code/evidence `237ecb917d41ede7e719dd443fc43191f0979a5b`. This report's own commit ID is given in the delivery message because a commit cannot contain its own hash.

## Evidence files

- `reports/evaluation/d1_m7_offline_pr26_2026-11-09/m8_d1_d2_dev_graph_paired_2026-11-13.json`
- `reports/evaluation/d1_m7_offline_pr26_2026-11-09/m2_t1_closed_corpus_readonly_2026-11-13.json`
- `reports/evaluation/d1_m7_offline_pr26_2026-11-09/d1_dev_runner_structural_2026-11-13.json`
- `reports/evaluation/d1_m7_offline_pr26_2026-11-09/m2_m2b_dev_label_scoped_2026-11-13.json`
- `reports/evaluation/d1_m7_offline_pr26_2026-11-09/m6_d2_dev_human_adjudicated_2026-11-13.json`
- Earlier M1/M5/M7/Privacy evidence cited in the table remains versioned under `reports/evaluation/`.

## Next work

1. Establish one accepted clause annotation granularity for T1 M1, then fix segmentation on Dev and run a newly frozen held-out evaluation.
2. Build and evaluate the actual 21-label M2 risk pipeline with sufficient adjudicated support; do not tune the frozen Dev heuristic to the T1 miss metadata.
3. Produce the product `final_result_v1` envelope and run M3a/M4 with independent real outputs. Review retrieval graph usefulness on Dev before another held-out run.
4. Complete a separately scoped 40-output M6 human review if the D2 Dev packet is not accepted as the formal sample.
