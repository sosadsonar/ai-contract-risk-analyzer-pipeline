<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 15. Risk Analysis, citation validation và assembly | 3643 ký tự | trước: 15_14-legal-corpus-baseline-retrieval-va-data-graph.md | sau: 17_16-export-report.md -->

# 15. Risk Analysis, citation validation và assembly

## 15.1 Risk LLM request - candidate catalog dedupe

Một provider call dùng candidate catalog chung để không lặp full legal text cho mỗi item:

```json
{
  "schema_version":"risk_analysis_request_v2",
  "role":"EMPLOYEE",
  "risk_taxonomy":[
    {"label":"PROBATION","definition":"..."}
  ],
  "basis_types":[
    {"type":"LEGAL_VIOLATION","definition":"..."},
    {"type":"UNFAVORABLE","definition":"..."},
    {"type":"AMBIGUOUS","definition":"..."}
  ],
  "candidates":{
    "BLLD2019:art26":{"content":"...","metadata":{"document_name":"...","article":"26"}}
  },
  "items":[{
    "clause_id":"cl_0001",
    "masked_text":"...",
    "clause_labels":["COMPENSATION_BENEFITS"],
    "candidate_ids":["BLLD2019:art26"],
    "related_clauses":[{"clause_id":"cl_0002","relation":"REFERS_TO","masked_text":"..."}]
  }]
}
```

Candidate order của mỗi item nằm trong `candidate_ids`. Payload không original/span. `risk_taxonomy` cung cấp nhãn và định nghĩa, `basis_types` định nghĩa ba loại căn cứ; model trả `risk_labels` và `basis_type` cho mỗi clause, không trả severity (backend tra bảng).

## 15.2 Risk LLM response

```json
{
  "schema_version":"risk_output_v2",
  "items":[{
    "clause_id":"cl_0001",
    "basis_type":"LEGAL_VIOLATION",
    "risk_labels":["PROBATION"],
    "citation_ids":["BLLD2019:art26"],
    "evidence_status":"SUPPORTED",
    "explanation":"Mức lương thử việc thấp hơn mức tối thiểu trong căn cứ được cung cấp."
  }]
}
```

Gemini call bắt buộc dùng structured output/response schema tương ứng `risk_output_v2` (`ai_pipeline/schemas/risk_output_v2.json`). `model_id`, `prompt_version` và các version pin do backend đóng dấu, không nằm trong response của model.

## 15.3 Runtime validation và advice sanitizer

* clause_id thuộc batch; risk labels thuộc taxonomy; role không do model trả.
* SUPPORTED => citation_ids non-empty.
* INSUFFICIENT_EVIDENCE => citation_ids empty.
* `basis_type` thuộc enum; (label, basis_type, vai trò) không rơi vào ô '-' của taxonomy, nếu rơi thì gỡ nhãn, hết nhãn thì bỏ clause khỏi kết quả và ghi need_review (dev/eval). Severity = mức cao nhất theo bảng taxonomy khi SUPPORTED, null khi INSUFFICIENT_EVIDENCE.
* Citation IDs phải subset candidate IDs; ngoài candidate được log trước khi filter.
* Advice detector **không match từ `nên` đơn lẻ**. Match các pattern có ngữ nghĩa khuyến nghị như `bạn nên`, `NLĐ nên`, `NSDLĐ nên`, `nên sửa/bổ sung/thương lượng/yêu cầu`, `đề nghị sửa`, `khuyến nghị`.
* Explanation legal-reference lint: nếu text nhắc rõ “Điều/Khoản ...” hoặc tên văn bản mà không tương ứng với citation hợp lệ đã chọn, coi là unsupported reference.

Xử lý vi phạm advice/unsupported-reference:

1. Structured retry tối đa 1 lần với validation feedback.
2. Nếu vẫn vi phạm, backend xóa **câu vi phạm** bằng deterministic sentence sanitizer; giữ phần explanation trung tính còn lại.
3. Nếu sanitizer làm explanation rỗng hoặc mất toàn bộ rationale -> `AI_OUTPUT_INVALID` và FAILED. Không fail cả phiên chỉ vì một từ nối “nên” hợp lệ.

## 15.4 Citation Validator

```text
selected_before_filter = risk.citation_ids
valid = []
for cid in selected_before_filter:
  if cid not in candidate_ids:
    log outside_candidate += 1
    continue
  provision = corpus.resolve(cid, analysis_date)
  if provision is effective:
    valid.append(cid)
if valid empty:
  evidence_status = INSUFFICIENT_EVIDENCE
  severity = null
citation_ids = unique(valid)
```

Runtime không tự chấm relevance semantic; M3b là evaluation property.

## 15.5 Result Assembler

* Join RiskResult -> Clause bằng clause_id.
* Quote/start/end chỉ từ canonical Clause.
* Dựng `risk_basis` từ `basis_type` + risk_labels; nhãn ngoài taxonomy là internal error trước publish; tổ hợp (label, basis_type, vai trò) ở ô '-' thì gỡ nhãn (hết nhãn thì bỏ clause). Severity tra bảng taxonomy.
* Citation objects từ validated IDs.
* No-risk -> COMPLETED + exact no-risk message + disclaimer, không khẳng định an toàn.
* Final publish atomically; FAILED không expose partial.
* `ContextResolutionTrace` chỉ dev/eval; không đưa vào product response nếu SRS chưa cập nhật.
