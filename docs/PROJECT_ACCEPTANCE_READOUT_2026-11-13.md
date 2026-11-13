# Project 3 acceptance readout — 13/11/2026

## Decision

**The project has not met all three teacher targets.** D2 Dev clause extraction passes
0.85, but T1 held-out M1 is 0.3718. The frozen Dev M2 heuristic scores 0.3333
Macro-F1 on only two supported T1 risk labels, below 0.80; the 21-label M2 model
is not yet evaluated. The 40-output human agreement is from D2 Dev and is not
the final M6 acceptance sample. No T1/T2 source text is reproduced here.

## v8 Dev-only integration and M8 audit

- The HTTP session route can now bind `make_pipeline_runner()` when
  `PRODUCT_RUNNER_ENABLED=true`. It captures a size-limited PDF in memory,
  extracts and checks it, loads the approved closed corpus, uses the configured
  provider and the persistent `DailyQuota` call ledger, and stores
  `final_result_v1` in `session.result`. The flag defaults to false, preserving
  the old sample route. An injected fake-provider route test verified
  `UPLOADED -> VALIDATING -> PROCESSING -> COMPLETED`. No live Gemini call was
  made. PDF is the only supported real-runner upload type here.
- `version_pins.app_commit` now chooses `APP_COMMIT` environment/config, then
  the repository's 40-character Git HEAD. It uses `dev-unpinned` only when no
  `.git` exists. The route test compared the pin with actual local HEAD. The
  deployed process still needs `APP_COMMIT` set when Git metadata is absent.
- M8-primary Dev remains **66/74 (0.89189)** for both Graph Off and Graph On.
  The six D1 misses are `HDLD001_C024/C025`, `HDLD002_C025/C026`, and
  `HDLD003_C012/C013`, all with Gold citation `BLLD2019:art21:cl1:ptc`.
  The two D2 misses are the two role rows for `HDLD003/d2seg_0024`, Gold
  citation `BLLD2019:art17:cl2`. Of the six D1 misses, three rank 7/8 and
  three are absent from the top eight; the two D2 rows are absent from the top
  eight. Every miss has zero direct clause-label map weight and is unreachable
  from current graph seeds. The only manual graph edge links Article 14 clauses.
- M8-oracle-labels can be run **only on D1's 14 adjudicated clause-label items**:
  Graph Off **8/14**, Graph On **8/14**. Six D1 misses persist with oracle
  labels, so D1's observed retrieval gap is not caused by the local M7 label
  predictor. D2 has injection/segmentation Gold but no adjudicated clause-label
  Gold; a 74-case oracle result would be mislabeled evidence. No legal mapping
  or graph edge was added without source-backed review of its general validity.
- Four D1 Dev `final_result_v1` envelopes generated with fake providers yielded
  **168/168** complete M6 review-shaped rows, so 40 can be selected structurally.
  These are synthetic risk judgments and are **not** a new human-rated 40-output
  packet. Review rows include source quotes and must stay in restricted storage.
- v8 checks: Pipeline full `.venv` pytest exit 0 (16 private-submodule skips),
  Data full `.venv` pytest **143 passed, 2 subtests passed** with the Pipeline
  repo on `PYTHONPATH`; Ruff exit 0 on both complete worktrees; scoped Git
  whitespace check exit 0. No T1/T2 source was accessed or re-evaluated.

## v9 approved graph edges and source-grounded Dev runner

- Four Data Lead-approved `MANUAL` edges were added between existing nodes in
  `edges.jsonl`; the edge checksum and `graph_version` were updated. The 16
  `provisions.jsonl` nodes and `label_map.yaml` are unchanged. Corpus loading
  and graph integrity tests pass.
- **M8-primary Dev Graph Off 66/74, Graph On 66/74**. **D1 oracle-labels Graph
  Off 8/14, Graph On 8/14**. The added graph produced 103 additional candidate
  placements across cases, but **zero top-five gains and zero top-five losses**.
  None of the eight misses has the Gold citation as a one-hop neighbor of the
  actual top-three seeds. The proposed Article 17/21 bridges therefore do not
  reach these misses under the frozen `seed_k=3`, `final_k=8` protocol. No
  retrieval score or seed rule was tuned to these Dev case IDs.
- The instructed `data/intake/restricted/D2_v02/clauses_v07.csv` does not exist
  locally. The 306-row `data/processed/clauses_v07.csv` is a mixed D1/T1
  processed inventory, not an adjudicated D2 clause-label Gold file. On the
  user's direction, the **74-case M8 oracle remains unavailable**; only the
  valid 14-case D1 oracle is reported.
- `SourceGroundedDevProvider` uses D1-trained local clause-label predictions
  and frozen source-text Dev risk rules on **masked** D1/D2 input. The runner
  produced D1 **17 risk items / 18 risk-label tuples** (one item has two labels)
  and D2 **75 risk items / 76 tuples**, of which **58** are Article 17 tuples
  and 18 are background-risk tuples. This differs from a claim of 18 D1 items
  and 58 D2 items. It is a local baseline diagnostic, not independent product
  M2 F1. Emitted citations were valid/effective **80/80** (structural M3a),
  and quote/offsets exact **92/92** (structural M4). Citation relevance and
  explanation quality were not independently adjudicated.
- The prior 40-row D2 M6 packet used default `rules_v1.1` geometry. Its IDs,
  role, normalized label, masked quote and exact spans match **40/40** rows from
  a compatibility runner using that geometry, but only **33/40** citations and
  **0/40** explanations match. Against the current `rules_v1.3` runner,
  **2/40** rows reach span IoU 0.80 and **0/40** have exact spans. The historical
  D2 human agreement (A/B 0.975, κ 0.89474; judge 1.0, κ 1.0) was rechecked
  from its CSV, but **cannot be attributed to the current `final_result_v1`
  output** without a new review of the changed result material.
- Data-boundary disclosure: during inventory, one metadata inspection loaded
  the mixed 306-row `data/processed/clauses_v07.csv` before its T1 membership
  was identified. Only column names and document-ID counts were displayed; no
  T1 contract text or label was printed, used for a rule, or evaluated. This
  inspection fell short of the v9 strict no-read instruction. Subsequent v9
  analysis was limited to D1/D2 Dev and code.

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
- `make_pipeline_runner()` on all four D1 contracts now produces `final_result_v1` **after** masked provider calls. Its 168 risk records have `risk_basis`, 168/168 valid taxonomy severity, 168/168 validated citation IDs and 168/168 exact quotes; all clause spans match the canonical source. The envelope has the TDD spelling `offset_unit="unicode_code_point"`, original source only at the final result boundary, and all 11 `version_pins` keys. Provider payloads passed a PII absence check. Fake risk outputs prove the assembly route only. In v8, the configured product route calls this runner; the default route remains a mock. The `app_commit` pin resolves to the real Git HEAD in this worktree.
- The frozen T1 JSON's actual label breakdown is `WORKING_HOURS_OVERTIME` 0 TP/0 FP/2 FN (F1 0) and `BONUS_BENEFITS` 1 TP/1 FP/0 FN (F1 0.6667). Five FP have Gold support 0; one `BONUS_BENEFITS` FP has Gold support 1. These aggregates conflict with the v7 instruction's proposed attribution. We copied only the already saved JSON counts into `per_label_readout_note`; no T1 source, Gold clause text, or new T1 prediction run was used. Clause-ID attribution cannot be proven from the aggregate JSON.
- M8's paired Dev query uses the approved Gold citation ID and a D1-trained TF-IDF clause-label predictor. Two role items for one D2 injection reuse the same query; confidence intervals and scores must be read with that correlation and in-sample training in mind.

## Verification and delivery

- Data full `.venv` pytest: **143 passed, 2 subtests passed**, exit 0, no collection errors.
- Pipeline full `.venv` pytest: exit 0 with 16 skips for unavailable private submodule fixtures; no failures. Focused dataset/metric/runner suite: 33 passed.
- Ruff check on both complete local worktrees: exit 0, zero findings. The previous 35 Pipeline and 20 Data findings were resolved through import ordering, formatting and three narrow code fixes. Several affected files are pre-existing untracked experiments and remain outside the staged PR slice; on a clean checkout those files are absent.
- `git diff --check`: exit 0. The dirty worktrees contain unrelated tracked and untracked work; only explicitly listed files are eligible for staging.
- Relevant local commits: Data `cad8d066ee48c78113b587f0e7ff1c6f6e4b8b99`, v7 notebook lint `a824795f60e93d9f99d9b3acbb2eeb8678c287d3`; Pipeline `fde757c78f0c444e731672169f2f7c001591050c`, `63316c99cbc305d1b46790951dcdfacfb932261c`, v6 `237ecb917d41ede7e719dd443fc43191f0979a5b`, v7 envelope and tracked lint `b35f427bec93927b4cd52d48055293e66cf354e9`. This report's own commit ID is given in the delivery message because a commit cannot contain its own hash.

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
3. Deploy the opt-in route with a pinned build SHA, real provider/call-ledger verification and independent real-output M3a/M4 review. Adjudicate any proposed Article 21/17 clause-label mappings or graph edges before changing the approved corpus; obtain D2 clause-label Gold for a complete oracle M8 diagnostic.
4. Complete a separately scoped 40-output M6 human review if the D2 Dev packet is not accepted as the formal sample.
5. Obtain an adjudicated D2 clause-label file with source hashes and offsets before claiming a 74-case oracle M8 score. Review actual top-three seed behavior on Dev before proposing any further retrieval change. Re-rate a packet generated from the current v1.3 `final_result_v1` output for M6.
