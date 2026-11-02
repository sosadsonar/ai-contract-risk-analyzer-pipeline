# C-13(b) Data Graph Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement TDD §14.6 graph expansion, ranking, fair final candidate merge, and safe fallback using fixtures only.

**Architecture:** Extend `DataGraph` with one-hop candidate expansion and a small orchestration function that obtains the baseline pool, applies graph expansion when enabled, and falls back to that pool on graph errors. Preserve the current corpus loader, candidate dataclasses, and draft-corpus gates.

**Tech Stack:** Python, pytest, existing legal corpus dataclasses, Ruff.

**Spec:** `docs/superpowers/specs/2026-10-28-c13b-data-graph-expansion-design.md`; normative ranking rules in TDD §14.6.

## Global Constraints

- Use TDD §14.6 defaults: seed multiplier 0.60; edge bonuses REFERS_TO 0.30, GUIDES 0.25, PARENT_OF 0.15; preferred-direction bonus 0.05.
- One hop only; enforce per-seed total-neighbor and PARENT_OF-child caps.
- Preserve seed-first ordering and return at most the same `final_k` as baseline retrieval.
- Graph disabled/absent returns the complete baseline pool; graph runtime failure returns that pool with `graph_fallback=True`.
- Do not modify legal corpus content/status/checksums, SQLite, runtime pipeline wiring, or tune from evaluation data.

## Review Focus

- A neighbor inactive on the analysis date must not be returned; verify both edge endpoints are date-filtered.
- Multiple seeds reaching the same citation must deduplicate without evicting seeds.
- Equal graph scores must sort deterministically by citation ID.
- Invalid caps or mismatched seed/pool inputs must fail clearly and be safely caught by the graph fallback boundary.
- Failure to build the baseline is not a graph failure and must not be swallowed by graph fallback.

---

### Task 1: Implement C-13(b) graph expansion and merge

**Files:**
- Modify: `backend/app/legal/data_graph.py`
- Modify: `tests/unit/test_data_graph.py`

**Interfaces:**
- Consume existing `BaselineResult`, `BaselineCandidate`, `DataGraph.neighbors()`, and runtime config fields.
- Produce `DataGraph.expand(seeds, pool, cfg)` and module-level `get_candidates(retriever, graph, masked_text, labels, analysis_date, cfg)` returning retrieval candidates and a graph fallback flag.

- [x] Add failing tests for edge direction bonuses, child/total caps, dedupe, seed-first ordering, graph-off behavior, and graph-error fallback.
- [x] Run focused tests and confirm failures for missing direction bonus/cap and invalid-cap validation.
- [x] Implement minimal expansion, scoring, deterministic merge, and fallback orchestration.
- [x] Re-run focused tests (35 graph/retriever tests), all repository tests (9 private-data skips), and Ruff.
- [x] Inspect final diff/status; corpus and SQLite were not edited by this task, and unrelated dirty files remain untouched.
