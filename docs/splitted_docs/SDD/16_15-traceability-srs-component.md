<!-- nguồn: SDD_AI_Labor_Contract_Risk_Analyzer_v0.1.md | mục: 15. Traceability: SRS -> Component | 898 ký tự | trước: 15_14-evaluation-architecture.md | sau: 17_16-cac-diem-de-tdd-chot.md -->

# 15. Traceability: SRS -> Component

| Yêu cầu | Component chịu trách nhiệm chính |
|---|---|
| FR-01..06, FR-26..27 | API/Session Controller, Orchestrator, Scope Precheck, Quota/Rate |
| FR-07..10 | Document Processing, PII Masker, Clause Segmenter |
| FR-11, FR-28..29 | Clause Classification Adapter, LLM Client, Orchestrator |
| FR-12, FR-15..16, FR-24, FR-30 | Legal Corpus Manager, Baseline Retriever, Data Graph Service, Citation Validator |
| FR-13..18 | Risk Analysis Adapter, Clause Graph Context Resolver, Citation Validator |
| FR-19..20, FR-22, FR-25 | Result Assembler, Web Frontend, Report Exporter |
| FR-21, FR-23 | Orchestrator, Session Store, Cleanup Scheduler |
| FR-31 | Clause Graph Builder + Context Resolver |
| NFR-SEC / DATA / REL / COST | Cross-cutting: Session Store, LLM Client, RunLog, Config, Deployment |
| EV-01..08 | Evaluation Harness + shared pipeline modules |
