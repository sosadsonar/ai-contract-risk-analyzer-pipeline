# D1 M7 improvement — 09/11/2026

Status: D1 Dev experiment and proposed parser change; **no new official M7 score or Gold release**.

## Why M7 is low

The saved 198-classification run scored 0.499868 Macro-F1 (95% document-bootstrap CI 0.440152–0.578259) under BRD 0.6's unchanged one-to-one IoU ≥ 0.5 rule. Only 111/174 `EXACT` Gold spans matched. The old segmentation's optimistic macro ceiling, even with perfect labels on matches and no unmatched-prediction false positives, was 0.7431. Improving labels alone therefore cannot reach the 0.80 Dev threshold on those boundaries.

Of 63 missed Gold spans, 62 are inside a larger prediction. Twenty-three predicted spans cover the 63 misses; 28 of those missed Gold rows sit in predictions containing `+` lines. `structure_parser_v1` recognized dash bullets but not `+` items. This is a source-text structural pattern, so a rule for repeated sibling `+` items is more defensible than changing Gold or the IoU threshold.

The other error is prediction scope. Of 87 unmatched predictions, 71 overlap only Gold `CONTEXT`, 14 overlap both `CONTEXT` and `EXACT`, and two overlap only `EXACT`. Thirty-one unmatched predictions carry `OTHER`. This comparison identifies review work; **Gold must not be used as a runtime filter**. A source-derived genuine-clause policy needs N1/N2 review and a separate D1-only test before changing which units enter classification.

## Options tested on D1 only

The offline probe splits saved predictions by a source-only rule and temporarily copies each parent's saved label to its children. That isolates boundary effects; the copied labels are not independent classifier output and none of these rows is a new official M7 score.

| Boundary option | Predicted spans | IoU matches | Diagnostic Macro-F1 with copied labels |
|---|---:|---:|---:|
| Saved `rules_v1.1` output | 198 | 111 | 0.499868 |
| Saved spans, source-based preamble gate | 172 | 111 | 0.526339 |
| Repeated `+` list lines | 235 | 135 | 0.533357 |
| `+` lines and preamble gate | 209 | 135 | 0.559703 |
| All list markers | 247 | 143 | 0.521307 |
| Every nonblank line | 366 | 168 | 0.524293 |

`+` is the best narrow *segmentation* rule tested: it gains 24 matches and scores better than broad list or line splitting. A second source-based experiment excludes predictions wholly before the first accepted `Điều` heading. This removes 26 unmatched predictions on D1, where no eligible `EXACT` Gold lies before that heading, and raises the copied-label diagnostic to 0.559703 when combined with `+`. It could suppress real contract terms in another document. It is a policy question, not part of `rules_v1.2`. The actual `rules_v1.2` parser was then run with the current masker on all four D1 documents. Against locked NFC Gold it produces 231 spans and 135 matches; against the separately rebased pipeline-canonical **candidate** it also produces 135 matches. Counts per document are in `reports/evaluation/d1_m7_offline_pr26_2026-11-09/rules_v12_geometry.json`. Its optimistic ceiling is 0.830927, which assumes perfect labels and ignores false positives; this is not an achieved score.

## Chosen change and release gate

The branch adds `+` as a weak structural marker. It becomes a separate clause only when at least two sibling `+` items exist, like the existing dash rule. A lone `+` line remains in its parent. The parser version changes to `structure_parser_v1.1` and the segmenter version to `rules_v1.2`; fixture tests cover both cases and partition invariants. The change is a D1 Dev candidate pending N1/N2 review of the boundary policy and the corresponding TDD §11.2/§11.4 update. The Gold files, M7 scorer, IoU threshold, and BRD 0.80 target remain unchanged.

The next validity step is to classify the **new** 231 spans with the same pinned model/prompt/schema and record a new prediction artifact. The current environment has no configured Gemini model/key or local provider, so this step was not run. The old labels cannot be presented as a new score. Once output exists, bind it to the same approved canonical text, compare official M7 with the saved 0.499868 baseline, and report CI/per-label counts. The old `d1_clause_run.py` uses a `difflib` raw-to-canonical mapper; use the hash-checked canonical candidate only after human approval, or fix the mapper before scoring newly canonicalized text.

After that, examine the 87 unmatched prediction IDs without filtering by Gold: agree on a source-based genuine-clause rule, implement and test it on D1/D2 Dev, and rerun classification. Only then tune label prompts for remaining errors. The current matched-pair labels are correct on 110/111 matches; most loss is boundary/scope related. T1/T2 labels remain excluded from development. PR #20's T1 M2 candidates and the human Gold/rights/privacy gates remain separate Data Lead work.

Evidence: `reports/evaluation/d1_m7_offline_pr26_2026-11-09/{result.json,canonical_handoff_audit.json,boundary_options_diagnostic.json,rules_v12_geometry.json}`. These reports contain IDs, hashes and counts; no contract text or PII.
