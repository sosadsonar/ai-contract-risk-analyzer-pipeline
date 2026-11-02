# C-18 Offline Evaluation Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Implement the fixture-testable dataset loader and deterministic M3a, M4, M5 and paired M8 metric core from TDD §18.

**Architecture:** Put new evaluation code under `ai_pipeline/evaluation/`, matching the TDD CLI namespace. Load a manifest and referenced JSON gold files only from a caller-selected dataset root, reject duplicate JSON keys and path escapes, and return immutable typed rows. Keep metrics pure and inject retrieval through a callback that receives the same masked text, predicted labels, analysis date and final budget for graph-off/on runs. This does not implement document extraction, segmentation/classification, model calls, or gold adjudication.

**Tech Stack:** Python 3.10+, dataclasses, standard library, pytest; existing corpus provision types; no new dependency.

**Spec:** `docs/splitted_docs/TDD/19_18-evaluation-harness-va-gold-format.md` §§18.1–18.5; `docs/BRD_AI_Labor_Contract_Risk_Analyzer_0_5.md` §§8.3–8.4.

## Global Constraints

- M3a requires each emitted citation to be in its candidate list, present in the corpus, and effective on the analysis date.
- M4 uses exact substring matching and Python code-point offsets with half-open `[start, end)` spans.
- M5 counts an injected case only when clause reference, role, and risk label all match; judge output is excluded.
- M8 compares paired cases at one shared `final_k`, reports graph-off and graph-on Recall@5 and graph-added candidate count; predicted labels are the primary retrieval input.
- Fixtures are synthetic smoke tests only. Never report their metrics as project quality or use private T1/T2/D1 data here.
- Do not modify SQLite, corpus law content/release status, or runtime pipeline wiring.

## Review Focus

- Duplicate JSON keys, duplicate document/injection IDs, malformed or escaped paths must fail closed.
- `CONTEXT` spans with `span=null` must not be scored as exact M4 gold.
- Citation versions that are inactive on the analysis date must fail M3a even when the ID exists.
- Duplicate predictions cannot count one injected gold case more than once.
- Graph-on/off must receive identical query text, predicted labels, date and `final_k`.
- Empty metric denominators must return an explicit undefined value or fail; never report a perfect score by default.

---

### Task 1: Dataset loader and manifest validation

**Files:**
- Create: `ai_pipeline/evaluation/__init__.py`
- Create: `ai_pipeline/evaluation/dataset.py`
- Test: `tests/unit/test_evaluation_dataset.py`

**Interfaces:** `load_dataset(manifest_path) -> EvaluationDataset`; documents expose resolved, root-contained source/gold paths and parsed JSON artifacts.

- [x] Add RED tests for valid load, duplicate JSON keys, duplicate IDs, missing files, and traversal outside dataset root.
- [x] Implement strict loader and typed immutable records.
- [x] Run focused tests (7 passed).

### Task 2: M3a, M4 and M5 pure metrics

**Files:**
- Create: `ai_pipeline/evaluation/metrics/citation_validity.py`
- Create: `ai_pipeline/evaluation/metrics/quote_span.py`
- Create: `ai_pipeline/evaluation/metrics/injected_recall.py`
- Test: `tests/unit/test_evaluation_metrics.py`

- [x] Add RED tests for corpus/effectivity/candidate checks, exact substring/code-point spans, `CONTEXT` exclusion, and exact clause-role-label injection matching.
- [x] Implement minimal deterministic metrics with explicit denominators.
- [x] Run focused tests (9 passed).

### Task 3: Paired M8 runner adapter and final verification

**Files:**
- Create: `ai_pipeline/evaluation/runner.py`
- Move/modify: retrieval metric under `ai_pipeline/evaluation/metrics/retrieval.py`
- Modify: `tests/unit/test_retrieval_metric.py`
- Create: `tests/unit/test_evaluation_runner.py`

- [x] Add RED tests proving both runs receive identical query/labels/date/final_k and distinct graph flag; reject mismatched budgets and missing predictions.
- [x] Implement a callback-based offline runner that consumes predicted labels, calls both retrieval modes, and aggregates M8.
- [x] Run focused tests (31 passed), all repository tests (9 skipped for unavailable private submodule), scoped Ruff, and `git diff --check`.
- [x] Inspect scoped changes; corpus and SQLite were not edited by this task, unrelated dirty files remain untouched.

**Completion boundary:** This completes only deterministic evaluation plumbing on fixtures. It does not complete C-18 until the production pipeline adapter, loader for actual approved gold formats, other metrics, and approved D1/T2 runs exist.
