# D1 Canonical Span Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile D1 canonical offsets and segmentation boundaries, then rescore the saved Gemini D1 output offline without changing Gold labels or calling Gemini again.

**Architecture:** The Data repository owns canonical source bytes and adjudicated Gold. The Pipeline repository owns prediction adapters, one-to-one span alignment, and metric calculation. Both sides pin the same canonical-text SHA-256 for each HDLD001–004 document; no Test document enters Dev scoring or tuning.

**Tech Stack:** Python 3.10+, pytest, JSON/CSV, Unicode NFC, SHA-256.

## Evidence and scope fixed on 2026-11-07

- Teammate artifacts (local Downloads, not for Git): `d1_198_clauses.json` SHA-256 `58f8e0b2567f53b80cbe6788ce6a297a43e88bc981b3e7020bae68056b78db2b`; `d1_63_unmatched_spans.json` SHA-256 `1b666236bcb626d2fe217c8e741e20bab4045b8c29ac5d05aa6dacce5f07256b`; `report.json` SHA-256 `fe565a5e2e9414eaee73fa1daab43473122d6d0a892c1993e1f3841b360d73d7`.
- 198 predicted clauses: HDLD001 43, HDLD002 47, HDLD003 40, HDLD004 68. Against the locally pinned `D1_m1_runtime_predictions_v01/*.canonical_nfc.txt`, offsets are in bounds; 172 slices equal `text` exactly and 26 differ only in whitespace.
- Reported M1 proxy: 99 TP, 99 FP, 75 FN at IoU 0.80; F1 0.5323. Reported preliminary M7: macro-F1 0.4974 on 174 EXACT Gold spans, 198 predicted spans, 111 matched, 63 Gold unmatched and 87 predictions unmatched at IoU 0.50. The 63 unmatched rows all overlap a prediction: 39 have IoU below 0.25, 24 have IoU from 0.25 to below 0.50.
- `d1_198_clauses.json` contains boundaries and text, **not predicted labels**. `report.json` contains aggregate M7 scores, **not per-clause labels**. A fresh M7 score cannot be reproduced from these three files alone.
- Version pins supplied by teammate: commit `8c382c8` (PR #21 on main), extraction schema `extraction_v1`, segmenter `rules_v1.1`, model `gemini-3.5-flash-lite`, prompt `clause_prompt_v1+v04+28987a13`, output schema `clause_output_v3`.

## Task 1 — Freeze the shared coordinate system (Data owner)

- [ ] Inspect `backend/app/document/canonicalizer.py` at the exact source commit and pin its file SHA-256 plus each D1 canonical-text SHA-256 in a private manifest. Verify NFC, LF, NBSP-to-space and the function's additional trim/join behavior.
- [ ] Recompute each Gold `[start_char,end_char)` against those canonical bytes, preserving clause IDs, labels, review decisions, and `CONTEXT`/`EXACT` eligibility. Emit a candidate release beside the old Gold; do not overwrite v06 or promote without the required reviewer decision.
- [ ] Fail closed if any EXACT Gold quote differs from `canonical_text[start:end]`, offsets overlap contrary to the segmentation schema, or source hashes differ. Save counts per document and a text-free validation report.

## Task 2 — Reconcile predicted offsets (Pipeline owner)

- [ ] Reproduce the 172 exact / 26 whitespace-only finding from the 198-clause artifact. For each of the 26, retain original prediction and record whether the pipeline quote was whitespace-normalized; never silently move its offset to the nearest matching text.
- [ ] Make the prediction adapter read the same pinned canonical text as Task 1. Test exact slicing, Unicode code-point offsets, CRLF/NBSP cases, repeated substrings, heading lines, and 26 whitespace-only cases. Return a mismatch report before scoring.
- [ ] Confirm HDLD005 and later are rejected by the Dev runner. Keep D1 = HDLD001–004 and D2 = four Dev documents.

## Task 3 — Shared one-to-one alignment and diagnostics (Pipeline owner)

- [ ] Reuse or extract the existing greedy IoU logic in `ai_pipeline/evaluation/metrics/clause_classification.py`; do not introduce a competing matcher. Define stable tie breaks, inclusive threshold `IoU >= 0.50`, half-open Unicode offsets, and one-to-one matching.
- [ ] Add focused tests for exact match, one predicted span overlapping two Gold spans, heading-plus-body span, zero-width rejection, tied IoU, Unicode, and unmatched counts. Compare results with the saved 111/63/87 baseline.
- [ ] Report M1 at its separate `IoU >= 0.80` rule. Keep M1 and M7 thresholds distinct. A 0.50 matcher cannot rescue the 63 currently below 0.50; inspect segmentation granularity and heading treatment without relabeling Gold to match predictions.

## Task 4 — Offline M7 rescore (both owners)

- [ ] Pipeline owner supplies the saved 198 prediction records **including `clause_id`, `start_char`, `end_char`, `clause_labels`, source hash, and model/prompt/schema pins**. The currently supplied boundary-only JSON and aggregate report are insufficient.
- [ ] Data owner verifies the Gold candidate/release and source hashes. Pipeline runner then scores the saved output offline, with no Gemini API call. Publish per-document alignment counts, macro-F1 and per-class scores, 95% document-cluster bootstrap CI, and an explicit list of unmatched IDs in private storage.
- [ ] Compare old v06 and canonical candidate under the same saved predictions. State whether changes stem from coordinates, segmentation policy, or classification; do not report a higher score as model improvement if only the evaluation reference changed.

## Task 5 — Review and release

- [ ] Run Data and Pipeline pytest, Ruff, `git diff --check`, and the existing privacy/secret scan. Keep raw text, prediction text, and private/restricted artifacts out of Git.
- [ ] Request independent review of changed Gold boundaries and label inheritance policy. Merge code and release Gold only after the applicable owner/reviewer decisions are recorded. Preserve the previous release and its benchmark for comparison.

## Required handoff from the teammate

The missing item is the **per-clause classified output for all 198 clauses**, with labels and version/source pins. The three files currently supplied are enough to audit geometry but not enough to recompute M7. No new Gemini call is needed if that output was saved with the original run.
