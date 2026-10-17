<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 3. Stack triển khai và cấu trúc repository | 2974 ký tự | trước: 03_2-cac-quyet-dinh-ky-thuat-tdd.md | sau: 05_4-configuration-secret-va-startup.md -->

# 3. Stack triển khai và cấu trúc repository

## 3.1 Stack đề xuất

| Layer | Công nghệ / thư viện | Vai trò |
|---|---|---|
| Runtime | Python 3.12 | Một runtime chung cho backend và ai_pipeline. |
| HTTP API | FastAPI + Uvicorn | 6 operation bắt buộc, multipart upload, streaming export. |
| Schema | Pydantic v2 + JSON Schema | Validate API và structured output; sinh schema versioned. |
| PDF | PyMuPDF | Extraction, page count, block/coordinate reading. |
| DOCX | python-docx + lxml | Paragraph/table + OOXML numbering/tracked change/textbox. |
| Unicode | unicodedata (stdlib) | NFC normalization. |
| Lexical retrieval | rank-bm25 | BM25 trên legal corpus; deterministic, local. |
| Graph | dict/list adjacency index | Không graph DB; 1-hop expansion. |
| Operational metadata | sqlite3 (stdlib) | RunLog/quota/rate/tombstone; không contract content. |
| Export | python-docx; PDF renderer tùy môi trường | DOCX first, PDF cut item. |
| Test | pytest + pytest-asyncio | Unit/integration/contract/eval fixtures. |
| Eval | Python CLI + JSON/CSV | M1-M8, privacy, annotation kappa, BL-1 và graph on/off. |

## 3.2 Cấu trúc package

```text
backend/
  app/
    main.py
    api/
      routes/sessions.py
      deps.py
      errors.py
    core/
      config.py
      enums.py
      clock.py
      security.py
    domain/
      models.py
      schemas.py
      errors.py
    session/
      store.py
      cleanup.py
      lock.py
      orchestrator.py
    document/
      extractor.py
      pdf_extractor.py
      docx_extractor.py
      canonicalizer.py
      quality.py
      scope_precheck.py
    privacy/
      pii_types.py
      detector.py
      masker.py
    clause/
      segmenter.py
      structure_parser.py
      graph_builder.py
      context_resolver.py
      taxonomy.py
    ai/
      provider.py
      gemini_client.py
      dev_local_client.py       # optional dev only
      clause_adapter.py
      risk_adapter.py
      prompts/
        clause_v1.py
        risk_v1.py
    legal/
      corpus_loader.py
      corpus_validator.py
      citation_id.py
      baseline_retriever.py
      data_graph.py
      citation_validator.py
    result/
      assembler.py
      exporter.py
    ops/
      runlog.py
      quota.py
      rate_limit.py
      metadata_db.py

ai_pipeline/
  schemas/
    extraction_v1.json
    masking_v1.json
    segmentation_v1.json
    clause_output_v3.json
    retrieval_v1.json
    risk_output_v1.json
    final_result_v1.json
  evaluation/
    runner.py
    metrics/
    gold/

data/
  legal_corpus/
    manifest.yaml
    provisions.jsonl
    edges.jsonl
    edge_suggestions.jsonl
    label_map.yaml
  docs/
    clause_taxonomy/
    risk_taxonomy/
    severity_rubric/

tests/
  unit/
  integration/
  contract/
  fixtures/
```

Không tạo package explanation AI riêng vì explanation nằm trong Risk Analysis LLM call #2. Không có `contract_id/analysis_id`. Frontend framework không bị TDD khóa; contract tích hợp bắt buộc nằm ở §5.9.
