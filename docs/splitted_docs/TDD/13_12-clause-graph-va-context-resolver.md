<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 12. Clause Graph và Context Resolver | 2225 ký tự | trước: 12_11-clause-segmentation.md | sau: 14_13-clause-classification-llm.md -->

# 12. Clause Graph và Context Resolver

## 12.1 Graph build

| Edge | Cách dựng | Validation |
|---|---|---|
| NEXT | `clauses[i] -> clauses[i+1]` theo span | Node tồn tại; no self-loop. |
| PARENT_OF | từ hierarchy numbering | Parent level < child level; no cycle. |
| REFERS_TO | local regex/reference parser trên masked clause | Chỉ tạo khi resolve đúng duy nhất tới clause trong cùng contract. |

REFERS_TO phải loại trừ dẫn chiếu **văn bản pháp luật**. Không tạo contract edge nếu pattern có các context như `Bộ luật`, `Luật`, `Nghị định`, `Thông tư`, `văn bản pháp luật`, hoặc dạng `Điều 26 Bộ luật Lao động` / `Điều 26 của Bộ luật...`. Chỉ resolve “Điều/Khoản ...” khi số đó tồn tại trong contract structure index và reference context không chỉ ra external legal document. Ambiguous -> bỏ edge + diagnostic.

Graph object chỉ lưu node IDs + ClauseEdge; không text.

## 12.2 Context resolution

```text
resolve_context(target):
  1. outgoing REFERS_TO targets
  2. incoming REFERS_TO sources
  3. direct parent và direct children PARENT_OF
  4. previous NEXT rồi next NEXT
  deduplicate, bỏ target
  lấy tối đa CLAUSE_GRAPH_MAX_RELATED và max context chars
```

Risk prompt dùng related clauses chỉ cho điều kiện/phụ thuộc/mâu thuẫn của **target clause**. Output vẫn target `clause_id`.

`CLAUSE_GRAPH_ENABLED=false` chỉ dùng dev/eval/test: graph build/context resolver bị bypass nhưng segmentation, original_text/span phải giống hệt. Demo require true theo FR-31.

## 12.3 ContextResolutionTrace - bằng chứng nghiệm thu

Để chứng minh Clause Graph thực sự tham gia Validation & Reasoning mà không tự đổi SRS RiskResult, dev/eval tạo ephemeral diagnostic:

```json
{
  "target_clause_id":"cl_0007",
  "related":[
    {"clause_id":"cl_0002","relation":"REFERS_TO"},
    {"clause_id":"cl_0006","relation":"NEXT_PREV"}
  ],
  "included_in_risk_request":true,
  "context_chars":842
}
```

Trace không chứa contract text, không persist trong product runtime, và không xuất cho end user. Evaluation/demo evidence gồm: graph fixture đúng; trace cho biết ID context đã đưa vào LLM #2; graph on/off không đổi span; graph cleanup cùng session. Nếu nhóm muốn `related_clause_ids` trong RiskResult product, phải cập nhật SRS trước.
