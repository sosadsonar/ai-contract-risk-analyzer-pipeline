# M8 Retrieval Metric Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Add an offline, fixture-testable M8 metric that compares graph-off and graph-on Recall@5 on the same paired cases and final candidate budget.

**Architecture:** Add a pure metric module under the existing `ai_pipeline/eval` package. Input rows carry one injection case, its gold citation, and ranked baseline/graph candidate IDs. The helper validates the paired inputs and candidate budget, then returns counts, recalls, and the aggregate number of graph-added candidates. It does not load real datasets or run retrieval.

**Tech Stack:** Python, dataclasses, pytest; no new dependency.

**Spec:** `docs/splitted_docs/TDD/19_18-evaluation-harness-va-gold-format.md` §18.4–18.5; `docs/BRD_AI_Labor_Contract_Risk_Analyzer_0_5.md` §8.3 M8.

## Global Constraints

- M8 is Recall@5 over injected-error cases and gold citation IDs.
- Graph-on and graph-off use the same case, corpus/configuration, and `final_k`; predicted labels remain the future primary runner input.
- This task creates no gold T2 and makes no retrieval-quality claim.
- Do not touch private data, runtime SQLite, corpus content, or production runtime wiring.

## Review Focus

- A case missing from either run must fail rather than silently changing the denominator.
- Duplicate case IDs or invalid/duplicate citation IDs must fail clearly.
- Candidate lists longer than `final_k` must fail; graph-on cannot gain a larger evaluation budget.
- Empty datasets must not be reported as a perfect score.
- Graph-added counts must be computed from citation IDs, not raw list length.

---

### Task 1: Implement paired M8 Recall@5 calculation

**Files:**
- Create: `ai_pipeline/eval/metrics/__init__.py`
- Create: `ai_pipeline/eval/metrics/retrieval.py`
- Test: `tests/unit/test_retrieval_metric.py`

**Interfaces:**
- `RetrievalCase(case_id, gold_citation_id, baseline_candidate_ids, graph_candidate_ids)`.
- `evaluate_retrieval(cases, *, final_k, k=5)` returns a typed result with graph-off/on hit counts, denominators, recalls, `k`, `final_k`, and total unique graph-added candidates.

- [x] Write failing tests for recall computation, paired case validation, fixed final budget, empty input, duplicate IDs, and added-candidate count.
- [x] Run focused tests and confirm collection failure while the metric module was absent.
- [x] Implement minimal typed inputs and pure calculations.
- [x] Run 10 focused tests, all repository tests (9 private-data skips), Ruff, and `git diff --check`.
- [x] Verify runtime SQLite, legal corpus content, and unrelated files were not edited.

**Scope note:** This completes the M8 metric calculation only. Dataset loading, paired pipeline execution, predicted-label orchestration, and any T2 quality result remain open.
