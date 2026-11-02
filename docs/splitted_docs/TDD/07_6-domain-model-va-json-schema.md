<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 6. Domain model và JSON Schema | 5296 ký tự | trước: 06_5-http-api-contract.md | sau: 08_7-analysis-orchestrator-state-machine-va-retry-res.md -->

# 6. Domain model và JSON Schema

## 6.1 Enum chuẩn

| Enum | Giá trị |
|---|---|
| Role | EMPLOYEE, EMPLOYER |
| SessionStatus | UPLOADED, VALIDATING, REJECTED, PROCESSING, COMPLETED, FAILED, EXPIRED |
| Stage | UPLOAD, EXTRACTION, SCOPE_PRECHECK, PII_MASKING, SEGMENTATION, CLAUSE_GRAPH, CLAUSE_CLASSIFICATION, LEGAL_RETRIEVAL, RISK_ANALYSIS, CITATION_VALIDATION, ASSEMBLY, EXPORT |
| Severity | HIGH, MEDIUM, LOW, null |
| EvidenceStatus | SUPPORTED, INSUFFICIENT_EVIDENCE |
| BasisType | LEGAL_VIOLATION, UNFAVORABLE, AMBIGUOUS |
| LegalEdgeType | PARENT_OF, REFERS_TO, GUIDES |
| ClauseEdgeType | NEXT, PARENT_OF, REFERS_TO |

## 6.2 Session aggregate

```python
class Session:
    session_id: UUID
    role: Role
    status: SessionStatus
    current_stage: Stage | None
    failed_stage: Stage | None
    created_at: datetime
    last_activity_at: datetime
    manual_retry_count: int
    filename: str
    analysis_date: date
    extraction_version: str | None
    canonical_text: str | None
    masked_text: str | None
    pii_spans: list[PiiSpan]              # start/end/type only; no original value
    clauses: list[Clause]
    clause_graph: ClauseGraph | None
    clause_classification_outputs: dict[str, ClauseClassOutput]
    legal_candidates: dict[str, list[LegalCandidate]]
    risk_results: list[RiskResult]
    version_pins: VersionPins
    stage_cache: dict[Stage, StageArtifact]
    last_error: ErrorInfo | None
    active_tasks: set[TaskHandle]
```

Session object chỉ ở memory. `pii_spans` không lưu original PII value/reverse mapping. Processing lease là resource của Orchestrator, không serialize trong Session content.

## 6.3 Clause và RiskResult

```json
Clause {
  "clause_id": "cl_0001",
  "original_text": "...",
  "start_char": 0,
  "end_char": 128,
  "clause_labels": ["COMPENSATION_BENEFITS"]
}

RiskResult {
  "clause_id": "cl_0001",
  "role": "EMPLOYEE",
  "risk_labels": ["PROBATION"],
  "risk_basis": [
    {"label":"PROBATION", "basis_type":"LEGAL_VIOLATION"}
  ],
  "severity": "HIGH",
  "explanation": "...",
  "evidence_status": "SUPPORTED",
  "citation_ids": ["BLLD2019:art26"],
  "version_pins": {...}
}
```

`risk_labels[]` là field nguồn theo SRS. `risk_basis[]` là field **dựng bởi backend** từ `basis_type` trong AI output và `risk_labels`, phải one-to-one với `risk_labels`; AI output không có `risk_basis` và không có `severity`. Severity/explanation/citation vẫn ở cấp clause đúng entity tối thiểu SRS. Nếu nhóm muốn severity riêng cho từng label thì phải sửa SRS trước.

## 6.4 VersionPins

```json
{
  "extraction_version": "extract_v1.1",
  "clause_taxonomy_version": "clause_taxonomy_v03",
  "risk_taxonomy_version": "risk_taxonomy_v01",
  "severity_rubric_version": "severity_v01",
  "corpus_version": "legal_corpus_2026-10-12",
  "data_graph_version": "legal_graph_2026-10-12",
  "clause_prompt_version": "clause_prompt_v1",
  "risk_prompt_version": "risk_prompt_v1",
  "model_id": "<configured-gemini-flash-model>",
  "temperature": 0.0,
  "app_commit": "<git-sha>"
}
```

> **Đối chiếu data (17/10/2026):** `clause_taxonomy_version` là phiên bản taxonomy **nguồn của data** (hiện `clause_taxonomy_v03`, 12 nhãn). Revision định nghĩa dùng trong prompt ở code (`TAXONOMY_VERSION = "v04"` trong `taxonomy.py`, sửa ranh giới nhãn, không thêm/bớt nhãn) được ghi qua `clause_prompt_version` **[Đề xuất]**; không thêm trường mới vào VersionPins vì FR-29 chưa đổi. Nhãn trong ví dụ JSON của TDD là minh họa và phải thuộc 12 nhãn của taxonomy.

## 6.5 Stage schema bắt buộc

| Schema | Trường chính |
|---|---|
| extraction_v1 | filename, role, extraction_version, canonical_text, page_count?, char_count |
| masking_v1 | schema_version, masked_text, pii_spans[{type,start,end}], masking_version |
| segmentation_v1 | schema_version, clauses[{clause_id,original_text,start_char,end_char,structure}], segmentation_version |
| clause_output_v3 | schema_version, items[{clause_id,clause_labels[1..3]}], model_id,prompt_version,taxonomy_version |
| retrieval_v1 | per_clause[{clause_id,candidates[]}], corpus_version,data_graph_version,graph_enabled |
| risk_output_v2 | items[{clause_id,basis_type,risk_labels,citation_ids,evidence_status,explanation}]; không có severity và version pins (backend đóng dấu) |
| risk_merged_v1 | output của `risk_assembler`: clauses[{clause_id,start_char,end_char,original_text,clause_labels,risk_labels,risk_basis,severity,explanation,evidence_status,citation_ids}], citations, version pins; đầu vào của final_result_v1 |
| final_result_v1 | offset_unit, session/role/date, canonical_text, clauses, risks(+risk_basis dựng bởi backend, severity tra bảng), citations, disclaimer, data_notice, version_pins |

`ContextResolutionTrace` là diagnostic artifact cho dev/eval, không phải field bắt buộc của RiskResult/API product.

## 6.6 Validation sau mỗi stage

* Extraction: NFC, canonical non-empty, limits, quality/legacy-font heuristic pass.
* Masking: length equality theo Unicode code point; PII span valid/non-overlap; no reverse mapping.
* Segmentation: clause IDs unique; spans sorted, **non-overlapping partition**; exact substring invariant; no boundary in PII; <=150.
* Clause Classification: every requested clause exactly once; 1..3 labels từ taxonomy; không span/quote; request không có role.
* Retrieval: candidate exists/effective; count <= final_k; graph on/off cùng final_k.
* Risk: labels valid; citation subset candidates; severity/evidence invariant; advice/citation-mention sanitizer pass.
* Assembly: kiểm (label, basis_type, vai trò) theo taxonomy, dựng `risk_basis`, tra severity; no risk without clause; quote/span chỉ từ canonical Clause; add `offset_unit=unicode_code_point`.
