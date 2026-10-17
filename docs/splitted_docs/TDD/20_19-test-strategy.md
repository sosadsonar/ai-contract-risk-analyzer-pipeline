<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 19. Test strategy | 3254 ký tự | trước: 19_18-evaluation-harness-va-gold-format.md | sau: 21_20-traceability-va-ke-hoach-migration-codebase.md -->

# 19. Test strategy

## 19.1 Test pyramid

| Mức | Ví dụ bắt buộc |
|---|---|
| Unit | canonicalization, code-point offsets, PII placeholder length, legacy-font detector, segmentation partition, graph build, citation ID/effectivity, quota arithmetic. |
| Contract | Pydantic/JSON Schema, Gemini response_schema mock, API error body, risk_basis derivation. |
| Integration | PDF/DOCX -> canonical -> mask -> segment; corpus build; graph fair on/off; retry/lease/cleanup. |
| E2E mock LLM | 6 operations, state transitions, no partial, frontend polling contract, export DOCX. |
| Provider smoke | Gemini paid tier de-identified fixture, retry matrix, token/cost log. |
| Evaluation | M1-M8 + privacy + annotation kappa + BL-1(if enabled), context trace. |

## 19.2 Critical invariant tests

| ID | Invariant | Test |
|---|---|---|
| INV-01 | len(masked)==len(canonical) code points | Privacy fixtures. |
| INV-02 | canonical[start:end]==original | Segmentation fixtures. |
| INV-03 | clause spans non-overlap + boundary not in PII | Nested/list adversarial fixtures. |
| INV-04 | outbound only masked contract text | Transport capture. |
| INV-05 | LLM cannot override span/quote | Malicious extra fields. |
| INV-06 | citation subset candidate + effective corpus | Fake citation. |
| INV-07 | INSUFFICIENT => severity null, citations empty | Risk schema. |
| INV-08 | Clause Graph contains no text | Object/serialization inspection. |
| INV-09 | restart removes session content | Process restart. |
| INV-10 | FAILED never returns final | Error injection. |
| INV-11 | graph off/on same final_k for M8 | Retrieval fixture. |
| INV-12 | JS highlight conversion correct for non-BMP | Browser/unit fixture. |

## 19.3 API/state tests

* ROLE_REQUIRED/RATE/QUOTA/SYSTEM_BUSY pre-admission không tạo session.
* Hai Create đồng thời: chỉ một acquire lease.
* Invalid file sau 201 -> session REJECTED + error_code qua Status.
* REJECTED retry -> INVALID_SESSION_STATE; FAILED retry #1/#2; #3 RETRY_LIMIT_EXCEEDED.
* Retry khi another session active -> SYSTEM_BUSY, counter không tăng.
* Local FAILED retry -> VALIDATING; processing FAILED retry -> PROCESSING.
* Polling status không kéo TTL; Result/Export kéo TTL.
* End Session trả 200 + EXPIRED, cancel tasks, idempotent.
* EXPIRED tombstone 24h rồi SESSION_NOT_FOUND.

## 19.4 Fixture format

Repository fixture tối thiểu:

```text
tests/fixtures/
  extraction/
    pdf_two_column/{input.pdf, expected.json}
    pdf_legacy_tcvn3/{input.pdf, expected_reject.json}
    docx_numbering/{input.docx, expected.json}
  privacy/
    case_001.json
  segmentation/
    nested_article_subclauses.json
    paragraph_fallback.json
  clause_graph/
    refers_contract.json
    excludes_legal_reference.json
  legal_corpus/
    valid/
    invalid_overlap/
    invalid_edge/
  api/
    state_cases.json
```

`expected.json` extraction chứa `canonical_text`, `extraction_version`, `offset_unit`; segmentation fixture chứa input canonical/masked + expected ordered spans/hierarchy; graph fixture chứa clauses + expected edges; privacy fixture chứa canonical + gold PII/preserve spans; API fixture chứa starting state, operation, expected HTTP/code/state. Fixture content có hợp đồng thật phải de-identify thủ công theo BRD 7.6.
