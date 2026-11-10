# X-05(a) — D1 local benchmark (W4, provisional)

Run: `cd backend && python -m app.ops.benchmark_d1 --data-root ../ai_pipeline/data --repeats 5`.
Host: Windows 11 build 26200, AMD64 Family 25 Model 68, Python 3.12.2. Source: `ai_pipeline/data` release `v06-rc1`; SHA-256 of **each of the four inputs used** matched its manifest receipt. These are five sequential runs per contract (20 stage samples), not five independent contracts. Timings use `perf_counter_ns`, rounded to milliseconds; p50/p90 are nearest-rank. They depend on the machine, filesystem cache and current code; rerun on deployment hardware.

| D1 contract | Input timed | Local clauses | Planned calls (20/6) | Local total p50 (ms) | Local total p90 (ms) |
| --- | --- | ---: | ---: | ---: | ---: |
| HDLD001 | Word-produced text snapshot → canonicalize | 43 | 11 | 4.003 | 4.246 |
| HDLD002 | Word-produced text snapshot → canonicalize | 47 | 11 | 3.755 | 3.789 |
| HDLD003 | Word-produced text snapshot → canonicalize | 40 | 9 | 4.770 | 4.858 |
| HDLD004 | DOCX → actual extractor + canonicalize + quality gates | 68 | 16 | 36.178 | 42.887 |

| Local stage (all 20 sequential samples pooled) | p50 (ms) | p90 (ms) |
| --- | ---: | ---: |
| Source preparation (different pathways above) | 0.471 | 28.890 |
| Scope precheck | 0.469 | 0.837 |
| PII mask | 2.733 | 4.735 |
| Segmentation | 0.396 | 0.635 |
| Whole local preprocessing (including measured overhead) | 4.246 | 36.178 |

`planned_calls = ceil(n_clause / CLAUSE_BATCH_SIZE) + ceil(n_clause / RISK_BATCH_SIZE)`. Nearest-rank p95 of these four **planned** counts is 16; this is **not** the configured `SESSION_CALL_RESERVE`: no actual LLM call/retry/token/cost measurement exists yet. Local clause counts are from the current segmenter, not adjudicated v06 annotation counts; do not treat them as gold segmentation or compare the two totals as accuracy. `.doc` 001–003 cannot enter the real upload extractor; their hashed text snapshots are canonicalized for local mask/segmentation timing. Source preparation and full preprocessing therefore are not comparable like-for-like with 004, and the three snapshots do not establish `.doc` upload support.

Not measured: LLM #1, retrieval/graphs, LLM #2, assembly, provider latency injection and end-to-end p50/p90. N1 classification and N3 risk are not connected to a real pipeline, the legal corpus is still DRAFT, and no approved paid-provider D1 run was made. Therefore **do not claim** NFR-PERF-01 (120 s), tune batch size/parallelism, or set demo quota from this report. Week 5 X-05 needs the integrated pipeline and a controlled slow-provider/retry case; record actual calls/tokens/cost separately from planned calls.

Privacy: benchmark runs locally in RAM, verifies selected-source hashes before processing, emits only contract IDs, input pathway, counts and durations; does not use labels/gold, network, evaluation ledger or product SQLite. D1 source provenance/privacy review and v06 gold sign-offs remain open; do not forward original text to a provider solely to complete timing.
