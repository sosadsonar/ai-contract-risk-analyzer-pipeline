<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 11. Clause Segmentation | 2334 ký tự | trước: 11_10-pii-masking.md | sau: 13_12-clause-graph-va-context-resolver.md -->

# 11. Clause Segmentation

## 11.1 ID, span và partition invariant

`clause_id` = `cl_0001`, `cl_0002`... theo `start_char` tăng dần; unique trong session. `original_text = canonical_text[start:end]`.

**Bắt buộc:** các clause là một partition các vùng được phân tích và **không chồng lấn span**. Với cấu trúc lồng nhau, hierarchy được lưu bằng metadata/PARENT_OF chứ không bằng span chứa span.

## 11.2 Structural heading patterns

```regex
1. Article:        ^\s*Điều\s+(\d+[A-Za-z]?)\s*[.:-]?\s*(.*)$
2. Decimal:        ^\s*(\d+(?:\.\d+){1,3})\s*[.)-]?\s+(.+)$
3. Numbered item:  ^\s*(\d{1,3})[.)]\s+(.+)$
4. Lettered item:  ^\s*([a-zA-ZđĐ])[.)]\s+(.+)$
5. Dash bullet:    ^\s*[-–•]\s+(.+)$
```

Algorithm trước hết nhận các heading/list marker hợp lệ và gán `structure.level/number/parent`. Sau đó **mọi accepted boundary** kết thúc span clause trước đó, bất kể heading kế tiếp là parent hay child. Vì vậy:

* `Điều 5` có các khoản `5.1`, `5.2`: span của clause “Điều 5” chỉ gồm heading + lời dẫn trước `5.1`; không bao trùm text của child.
* `5.1` kết thúc trước `5.2`, không chồng nhau.
* Dash/letter bullet chỉ thành clause riêng khi rule list đủ tin cậy (>=2 siblings hoặc marker cấu trúc rõ); nếu không, nằm trong clause paragraph hiện tại.

Nếu một parent chỉ có heading rồi lập tức tới child, parent clause có thể chỉ gồm heading. Đây vẫn là clause hợp lệ cho hierarchy nhưng evaluation fixture phải nhất quán với annotation guideline.

## 11.3 Fallback paragraph

* Không có heading đáng tin cậy -> split theo paragraph blocks.
* Paragraph <40 chars được gộp với neighbor nếu không phải heading/list.
* Không split giữa line khi không có marker.
* Clause >4.000 chars giữ nguyên baseline và ghi warning; không semantic split bằng LLM.
* Sau segmentation: <=150 clause; spans sorted; `end_i <= start_{i+1}`; không boundary trong placeholder.

## 11.4 Segmentation output schema

```json
{
  "schema_version":"segmentation_v1",
  "segmentation_version":"rules_v1.1",
  "offset_unit":"unicode_code_point",
  "clauses":[
    {"clause_id":"cl_0001","original_text":"...","start_char":0,"end_char":95,
     "structure":{"level":1,"number":"5","parent_clause_id":null}}
  ]
}
```

`structure` là metadata local cho graph builder; public Clause chỉ cần field tối thiểu SRS. Raw original text/structure không gửi LLM nếu không cần.
