<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 13. Clause Classification LLM | 1983 ký tự | trước: 13_12-clause-graph-va-context-resolver.md | sau: 15_14-legal-corpus-baseline-retrieval-va-data-graph.md -->

# 13. Clause Classification LLM

## 13.1 Request contract

```json
{
  "schema_version":"clause_classification_request_v1",
  "taxonomy_version":"clause_taxonomy_v03",
  "items":[
    {"clause_id":"cl_0001","masked_text":"..."}
  ]
}
```

**Không gửi `role`** cho Clause Classification. FR-11 chỉ cần clause ID + masked clause và optional minimal structural context. Không gửi canonical/original/start/end.

## 13.2 Response contract

```json
{
  "schema_version":"clause_output_v3",
  "items":[
    {"clause_id":"cl_0001","clause_labels":["COMPENSATION_BENEFITS"]}
  ],
  "model_id":"...",
  "prompt_version":"clause_prompt_v1",
  "taxonomy_version":"clause_taxonomy_v03"
}
```

* 1..3 labels, unique, từ source taxonomy.
* Không chấp nhận confidence/type_scores/tier/review_zone/quote/span.
* Missing/duplicate/unknown ID hoặc label invalid -> structured-output retry tối đa 1; sau đó AI_OUTPUT_INVALID.

## 13.3 Prompt policy

System prompt: chỉ phân loại clause; không phân tích risk; không suy diễn PII đã che; chỉ chọn label taxonomy; output theo provider response schema.

## 13.4 LLMProvider abstraction và retry matrix

```python
class LLMProvider(Protocol):
    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s): ...
```

* `GeminiProductClient`: bắt buộc demo/eval, paid tier, explicit model ID, provider structured output/`response_schema`.
* `DevLocalClient` hoặc Gemini dev: optional chỉ `APP_ENV=dev` và de-identified data; không nằm product deployment.

| Lỗi | Auto-retry? | Lý do |
|---|---|---|
| Timeout/network reset | Có, tối đa 1 | Tạm thời. |
| HTTP 429 | Có, tối đa 1 với backoff/jitter | Tạm thời nhưng tính quota/cost. |
| HTTP 5xx | Có, tối đa 1 | Provider transient. |
| HTTP 400/401/403 | Không | Config/request/auth lỗi, retry vô ích. |
| Structured output/schema invalid | Có, tối đa 1 | Repair bằng cùng schema + validation feedback. |

Mỗi **actual provider request**, kể cả retry, tăng call counter/cost ledger.
