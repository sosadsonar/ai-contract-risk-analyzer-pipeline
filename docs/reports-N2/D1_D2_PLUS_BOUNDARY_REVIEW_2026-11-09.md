# D1/D2 `+` boundary decision packet — 09/11/2026

Status: **technical Dev evidence; human boundary decision pending**. No Gold, labels or metric threshold changed.

## Decision requested from N1/N2

Should a repeated `+` list item be a separate clause, and under which source-visible conditions? Review the indicated D1 and D2 source spans in the authorized local Data checkout. Record the chosen annotation unit, treatment of headings/context, exceptions, and the corresponding TDD §11.2/§11.4 change before enabling the candidate by default. Do not use Gold labels as a runtime filter.

## Evidence

| Dev set and mode | Gold spans | Predicted spans | Greedy IoU ≥ 0.5 matches | Meaning |
|---|---:|---:|---:|---|
| D1 saved `rules_v1.1` | 174 `EXACT` | 198 | 111 | Saved M7 run, true Macro-F1 0.499868. |
| D1 opt-in `rules_v1.2` | 174 `EXACT` | 231 | 135 | Geometry only; no new independent labels or M7 score. |
| D2 existing `rules_v1.1` checkout | 236 | 194 | 189 | Reference geometry. |
| D2 current default | 236 | 194 | 189 | Same per-document counts and unmatched Gold rows as reference. |
| D2 opt-in `rules_v1.2` | 236 | 231 | 184 | Five fewer matches overall; geometry only. |

On D2, seven Gold refs become unmatched under the opt-in rule: HDLD001 `d2seg_0012`, `d2seg_0013`, `d2seg_0025`, `d2seg_0037`; HDLD002 `d2seg_0016`, `d2seg_0028`, `d2seg_0039`. Two HDLD001 refs, `d2seg_0035` and `d2seg_0036`, become matched. These identifiers point to restricted local Gold; this packet contains no source excerpts. The per-document JSON includes source/Gold SHA-256 and offsets for unmatched rows.

## Interim technical decision

Keep `rules_v1.1` as the default. Permit `rules_v1.2` only through `enable_plus_lists=True` in Dev experiments. After human review, test a source-derived condition on both D1 and D2, rerun geometry, then classify newly produced D1 spans independently using the pinned model/prompt/schema. Report official M7 and its CI only from that new output.

Evidence: `reports/evaluation/d1_m7_offline_pr26_2026-11-09/` and `reports/evaluation/d2_plus_parser_regression_2026-11-09/`. D2 Gold and candidate text remain in the Data checkout; neither is committed here.
