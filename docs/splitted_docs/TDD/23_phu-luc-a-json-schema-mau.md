<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: Phụ lục A. JSON Schema mẫu | 2142 ký tự | trước: 22_21-open-items-gioi-han-da-biet.md | sau: 24_phu-luc-b-env-example.md -->

# Phụ lục A. JSON Schema mẫu

## A.1 clause_output_v3

```json
{
  "$id":"clause_output_v3",
  "type":"object",
  "additionalProperties":false,
  "required":["schema_version","items","model_id","prompt_version","taxonomy_version"],
  "properties":{
    "schema_version":{"const":"clause_output_v3"},
    "items":{"type":"array","items":{
      "type":"object","additionalProperties":false,
      "required":["clause_id","clause_labels"],
      "properties":{
        "clause_id":{"type":"string","pattern":"^cl_[0-9]{4}$"},
        "clause_labels":{"type":"array","minItems":1,"maxItems":3,"uniqueItems":true,
          "items":{"type":"string","enum":"<generated from taxonomy source>"}}
      }
    }},
    "model_id":{"type":"string"},
    "prompt_version":{"type":"string"},
    "taxonomy_version":{"type":"string"}
  }
}
```

Enum label phải sinh từ source-of-truth taxonomy hoặc có test đối chiếu theo DEC-20.

## A.2 risk_output_v2

```json
{
  "$id":"risk_output_v2",
  "type":"object",
  "additionalProperties":false,
  "required":["schema_version","items"],
  "properties":{
    "schema_version":{"const":"risk_output_v2"},
    "items":{"type":"array","items":{
      "type":"object","additionalProperties":false,
      "required":["clause_id","basis_type","risk_labels","citation_ids","evidence_status","explanation"],
      "properties":{
        "clause_id":{"type":"string","pattern":"^cl_[0-9]{4}$"},
        "basis_type":{"enum":["LEGAL_VIOLATION","UNFAVORABLE","AMBIGUOUS"]},
        "risk_labels":{"type":"array","minItems":1,"maxItems":3,"uniqueItems":true,
          "items":{"type":"string","enum":"<generated from risk taxonomy source>"}},
        "citation_ids":{"type":"array","uniqueItems":true,"items":{"type":"string"}},
        "evidence_status":{"enum":["SUPPORTED","INSUFFICIENT_EVIDENCE"]},
        "explanation":{"type":"string","minLength":10}
      }
    }}
  }
}
```

Schema đầy đủ (kèm `allOf` cho SUPPORTED/INSUFFICIENT_EVIDENCE) nằm ở `ai_pipeline/schemas/risk_output_v2.json`. AI schema **không có** `risk_basis` và `severity`: backend dựng `risk_basis` từ `basis_type` và tra `severity` từ risk taxonomy. `model_id`, `prompt_version` và các version pin do backend đóng dấu. Cross-field validation SUPPORTED/INSUFFICIENT_EVIDENCE do `allOf` hoặc Pydantic thực hiện. Cùng JSON Schema được truyền làm provider response schema/structured output.
