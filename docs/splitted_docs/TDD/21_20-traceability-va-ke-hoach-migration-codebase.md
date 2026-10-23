<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 20. Traceability và kế hoạch migration codebase | 1958 ký tự | trước: 20_19-test-strategy.md | sau: 22_21-open-items-gioi-han-da-biet.md -->

# 20. Traceability và kế hoạch migration codebase

## 20.1 SRS -> TDD module

| SRS | Module | TDD |
|---|---|---|
| FR-01..06,26,27 | api/session/orchestrator/scope_precheck/ops | API §5, Orchestrator §7, Scope §9, Ops §17 |
| FR-07,08 | document/\* | §8 |
| FR-09 | clause/segmenter.py | §11 |
| FR-10 | privacy/\* | §10 |
| FR-11,28,29 | ai/clause_adapter.py, ai/client.py | §13, §4 |
| FR-12,24,30 | legal/corpus\*, baseline_retriever.py, data_graph.py | §14 |
| FR-13..18 | ai/risk_adapter.py, legal/citation_validator.py | §15 |
| FR-19,20 | result/assembler.py + frontend contract | §15, §5.9 |
| FR-21 | session/orchestrator.py + ai/client.py | §7 |
| FR-22 | result/exporter.py | §16 |
| FR-23 | session/cleanup.py | §17.4 |
| FR-25 | frontend/export constants | §5.9/§16 |
| FR-31 | clause/graph_builder.py + context_resolver.py | §12 |
| EV-01..08 | evaluation/\* | §18 |

## 20.2 Migration từ snapshot codebase

| Milestone kỹ thuật | SRS Appendix C | Kết quả |
|---|---|---|
| M0 - Schema first | C-04,C-03,C-17 | Tạo enums/source-of-truth taxonomy, schema clause_output_v3/risk_output_v2, pytest skeleton và mocks mới. |
| M1 - Session/API | C-05,C-06,C-16 | InMemorySessionStore, state machine, 6 operation, global lock, metadata-only ops DB. |
| M2 - Local preprocessing | C-08,C-10,C-09,C-01,C-02 | Extractor PDF/DOCX, scope, masking, segmentation; ưu tiên invariant trước AI. |
| M3 - AI classification | C-07,C-11 | Gemini client chuẩn, classification batch. |
| M4 - Legal retrieval | C-12,C-13 | Corpus validator, baseline retriever, Data Graph. |
| M5 - Risk + Clause Graph | C-14,C-15 | Clause Graph context + risk call + citation validation/assembly. |
| M6 - Output/Eval | C-21,C-18,C-19,C-20 | Export DOCX, evaluation metrics, docs/dependency cleanup. |

Nguyên tắc migration: không tiếp tục phát triển trên schema cũ có contract_id/type_scores/review_zone. Mock schema mới phải có trước để backend/frontend/AI có thể làm song song.
