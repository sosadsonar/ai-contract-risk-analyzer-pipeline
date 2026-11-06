# T1/T2 technical evaluation and acceptance readout

Date: 2026-11-06
Machine-readable results: `result.json`
Evaluation status: `PARTIAL_TECHNICAL_EVALUATION_T1_M4_NO_RISK_OUTPUTS`

## Scope and method

The report evaluates three parallel T1 views: `slice_unique_8` (eight non-duplicate real/template documents), `slice_t1_real_9` (HDLD005–013), and `slice_composite_10` (HDLD005–014, including one synthetic calibration control). T2 contains nine documents, 872 segmentation spans, and 30 injected cases. All confidence intervals use 1,000 cluster-bootstrap resamples with seed 0. Prediction modules are documented in `result.json`; M7 is a fixed character TF-IDF 1-NN trained only on the 183 D1 clauses, and M5 is the frozen Dev Article 17 OR rule.

`slice_composite_10` is an evaluation composition, not ten independent real contracts. HDLD014 remains `SYNTHETIC_CHALLENGE_NOT_T1`. The owner-attested equivalent gate returns 10/10 accepted under `T1_EQUIVALENT_GATE_V1`; the original BRD source gate remains `BLOCKED_9_OF_10_DOCS` because the synthetic control does not satisfy the original ten-source-doc requirement.

## Scores

| Slice | M1 segmentation F1 | M3a citation validity | M4 exact quote/offset | M7 full labels macro-F1 | M7 genuine clauses macro-F1 |
|---|---:|---:|---:|---:|---:|
| Unique 8 | 0.3683 [0.2055, 0.5621] | 630/630 = 1.000 | Not estimable: zero risk outputs | 0.3348 [0.2424, 0.5364], n=630 | 0.5580 [0.4683, 0.6516], n=281 |
| T1 real 9 | 0.3713 [0.2198, 0.5460] | 747/747 = 1.000 | Not estimable: zero risk outputs | 0.3377 [0.2476, 0.5154], n=747 | 0.5442 [0.4642, 0.6308], n=340 |
| Composite 10 | 0.3805 [0.2303, 0.5513] | 757/757 = 1.000 | Not estimable: zero risk outputs | 0.3496 [0.2560, 0.5311], n=757 | 0.5577 [0.4810, 0.6424], n=350 |
| T2, 9 documents | 0.3431 [0.2043, 0.4935] | 387/387 = 1.000 | 19/19 emitted risk outputs = 1.000 [1.000, 1.000] | Not applicable: no independent T2 clause-label Gold | Not applicable |

T2 M5 recall is 12/30 = **0.4000 [0.2667, 0.5333]**. T2 M8 Recall@5 is **15/30 = 0.5000 [0.3214, 0.6774]** with graph expansion off and **14/30 = 0.4667 [0.2857, 0.6364]** with graph expansion on. Both intervals are bootstrap intervals from the 30 paired injection cases.

Privacy §7.3 diagnostic results are reported separately from M4: on T1 real 9, high-sensitivity PII recall is 3/3 = 1.000, standard-sensitivity PII recall is 18/18 = 1.000, and preserve rate is 62/63 = 0.9841 [0.9524, 1.000]. On the composite 10 slice these are 3/3, 18/18, and 69/70 = 0.9857 [0.9571, 1.000]. T2 privacy uses a derived reference projected from T1 adjudicated privacy Gold and T2 injection spans; it is not a separately adjudicated T2 privacy Gold and is not an acceptance result.

## BRD threshold readout

Thresholds below are taken from the repository's BRD measurement table at `docs/splitted_docs/BRD/08_8-do-luong-chat-luong-va-nghiem-thu.md` (§8.3); privacy thresholds are from its §7.3. The repository copy is the available source for this evaluation. This readout does not establish a different BRD revision.

| Requirement | BRD threshold | Current evidence | Status |
|---|---:|---|---|
| M1 | ≥0.85 on T1 | T1 real 9: 0.3713; bootstrap CI [0.2198, 0.5460] | **Fail** |
| M2 | ≥0.80 on T1 | No independent T1 risk-classification run in this report | **Not run** |
| M3a | 100% valid citations | T1 747/747; T2 387/387 | **Technical check passes**, limited to top-1 retrieved candidates' corpus/effectivity membership; does not measure relevance or citation accuracy of risk outputs |
| M3b | ≥0.85 relevance | No adjudicated 40-output relevance sample or judge result | **Not run** |
| M4 | 100% exact quote and offsets | T1 has zero emitted risk outputs, so undefined; T2 19/19 emitted outputs exact | **T2 emitted-output check passes; T1 not estimable**. This does not measure missed risks |
| M5 | ≥0.90 on at least 30 T2 injections | 12/30 = 0.4000; CI [0.2667, 0.5333] | **Fail** |
| M6 | ≥0.80 agreement and Cohen's κ ≥0.6 | No judge calibration result | **Not run** |
| M7 | ≥0.80 on T1 | Full 747-row slice: 0.3377; genuine 340-clause slice: 0.5442 | **Fail on both views** |
| M8 | ≥0.90 Recall@5 on T2 | Graph off 0.5000; graph on 0.4667 | **Fail on both views** |
| §7.3 high-sensitivity privacy | ≥0.99 recall | T1 real 9: 3/3 = 1.000 | **Point estimate passes** |
| §7.3 standard-sensitivity privacy | ≥0.90 recall | T1 real 9: 18/18 = 1.000 | **Point estimate passes** |
| §7.3 preserve fields | ≥0.95 | T1 real 9: 62/63 = 0.9841; CI lower bound 0.9524 | **Pass** |

## Interpretation and remaining gates

These are reproducible technical baseline scores, not overall project acceptance. M3a is structurally limited because it checks retrieved top-1 candidates against the corpus/effectivity set and cannot establish relevance. M4 is conditional on emitted risks; T1 produced none. T2 M5 uses a narrower frozen Dev rule rather than the higher-recall W7 composite and therefore measures that stated baseline only. M7 is a newly materialized D1-only baseline and is not evidence that the previously locked W5 model meets T1 acceptance.

The original BRD source gate remains blocked at 9/10 real/source documents. The equivalent 10-document route is an owner-attested project deviation; its receipt does not independently establish source rights, data-controller authority, legal compliance, or de-identification. T1/T2 scores above do not clear the failed/not-run BRD criteria. Do not mark the end-to-end Data Lead / MS-4 acceptance complete until the remaining criteria have valid evidence or an authorized, documented acceptance disposition.
