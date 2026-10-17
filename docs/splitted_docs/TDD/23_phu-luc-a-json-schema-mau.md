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

## A.2 risk_output_v1

```json
{
  "$id":"risk_output_v1",
  "type":"object",
  "additionalProperties":false,
  "required":["schema_version","items","model_id","prompt_version",
              "risk_taxonomy_version","severity_rubric_version"],
  "properties":{
    "schema_version":{"const":"risk_output_v1"},
    "items":{"type":"array","items":{
      "type":"object","additionalProperties":false,
      "required":["clause_id","risk_labels","severity","explanation",
                  "evidence_status","citation_ids"],
      "properties":{
        "clause_id":{"type":"string"},
        "risk_labels":{"type":"array","uniqueItems":true,"items":{"type":"string"}},
        "severity":{"type":["string","null"],"enum":["HIGH","MEDIUM","LOW",null]},
        "explanation":{"type":"string","minLength":1},
        "evidence_status":{"enum":["SUPPORTED","INSUFFICIENT_EVIDENCE"]},
        "citation_ids":{"type":"array","uniqueItems":true,"items":{"type":"string"}}
      }
    }}
  }
}
```

`risk_basis` **không nằm trong AI schema**; backend derive từ risk taxonomy. Pydantic model thực hiện cross-field validation SUPPORTED/INSUFFICIENT_EVIDENCE. Cùng JSON Schema được truyền làm provider response schema/structured output.
