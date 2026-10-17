<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 14. Legal Corpus, Baseline Retrieval và Data Graph | 3893 ký tự | trước: 14_13-clause-classification-llm.md | sau: 16_15-risk-analysis-citation-validation-va-assembly.md -->

# 14. Legal Corpus, Baseline Retrieval và Data Graph

## 14.1 Artifact layout

```text
data/legal_corpus/
  manifest.yaml
  provisions.jsonl
  edges.jsonl
  edge_suggestions.jsonl   # optional, không load vào runtime graph
  label_map.yaml
```

`manifest.yaml` chứa corpus_version, graph_version, timezone và checksums.

## 14.2 LegalProvision JSONL

```json
{
  "citation_id":"BLLD2019:art26",
  "document_id":"BLLD2019",
  "document_name":"Bộ luật Lao động 2019",
  "version":"2019",
  "article":"26",
  "clause":null,
  "point":null,
  "parent_path":["BLLD2019","art26"],
  "content":"...",
  "effective_from":"2021-01-01",
  "effective_to":null
}
```

`citation_id` deterministic. Nếu cùng provision có nhiều version theo thời gian, effectivity record chọn bản hiệu lực; overlap -> LEGAL_CORPUS_CONFLICT.

## 14.3 LegalEdge và origin

Runtime LegalEdge chỉ dùng enum SRS `AUTO|MANUAL`:

* PARENT_OF sinh từ `parent_path` khi build -> origin=AUTO; không cần lưu trong `edges.jsonl`.
* `edges.jsonl` chỉ chứa REFERS_TO/GUIDES đã được người phụ trách dữ liệu xác minh -> origin=MANUAL.
* Gợi ý tự động chưa xác minh nằm ở `edge_suggestions.jsonl` và **không được load**. Khi reviewer duyệt, copy thành edge MANUAL.

```json
{"from_citation_id":"BLLD2019:art26","to_citation_id":"BLLD2019:art25",
 "edge_type":"REFERS_TO","origin":"MANUAL"}
```

## 14.4 Corpus validation

* deterministic citation ID, valid effectivity, no overlap.
* edge endpoint tồn tại; PARENT_OF acyclic; enum hợp lệ.
* content UTF-8/NFC non-empty; metadata đủ export.

## 14.5 Baseline retrieval - cùng kích thước graph on/off

`label_map.yaml` khai **trọng số trực tiếp**, không có khái niệm “nhóm label liên quan” ngầm:

```yaml
COMPENSATION_BENEFITS:   # khóa = một trong 12 nhãn clause taxonomy; giá trị chỉ là ví dụ minh họa
  BLLD2019:art26: 1.0
  BLLD2019:art25: 0.6
```

```text
baseline_score(c) = 0.70 * configured_label_weight(c)
                  + 0.30 * bm25_normalized(c)
```

Retriever luôn tính `baseline_pool = top RETRIEVAL_FINAL_K` sau effectivity + dedupe. `seeds = top RETRIEVAL_SEED_K` là subset dùng **chỉ để graph expansion**. Khi graph disabled/fallback, final candidates = baseline_pool (không phải chỉ 3 seed).

## 14.6 Data Graph expansion, hướng cạnh và ranking

Convention edge:

* PARENT_OF: `from=parent`, `to=child`. Expansion được đi cả parent->child và child->parent; tối đa `GRAPH_MAX_CHILDREN_PER_SEED` child, chọn theo baseline/BM25 relevance.
* REFERS_TO: `from=source provision`, `to=referred provision`. Ưu tiên outgoing; incoming được phép như secondary fact-finding, tổng neighbor vẫn bị cap.
* GUIDES: `from=guiding provision`, `to=guided/base provision`. Cho phép traverse cả hai hướng để từ base tìm guidance và ngược lại.
* Tổng graph-only neighbor lấy từ mỗi seed <= `GRAPH_MAX_NEIGHBORS_PER_SEED`.

Scoring default (tune D1/D2):

```text
graph_score = 0.60 * seed.baseline_score + edge_bonus + direction_bonus
edge_bonus:
  REFERS_TO 0.30
  GUIDES     0.25
  PARENT_OF  0.15

direction_bonus:
  preferred direction 0.05
  reverse direction   0.00
```

Final merge:

1. Giữ top `seed_k` seed ở đầu theo baseline score (seed-first SDD).
2. Merge `baseline_pool[seed_k:]` và graph-only neighbors bằng score chuẩn hóa; dedupe citation ID.
3. Take `final_k`.

Do đó graph on/off đều có cùng tối đa `final_k=8`; M8 recall@5 là so sánh top 5 thực sự ở cả hai cấu hình. Risk LLM cũng nhận cùng candidate-count budget, tránh bias do graph-off ít candidate hơn.

Nếu graph runtime lỗi -> baseline_pool + `graph_fallback=true` trong RunLog.

## 14.7 LegalCandidate

```json
{
  "citation_id":"BLLD2019:art26",
  "content":"...",
  "document_name":"Bộ luật Lao động 2019",
  "article":"26",
  "version":"2019",
  "effective_from":"2021-01-01",
  "effective_to":null,
  "origin":"SEED_LABEL|SEED_LEXICAL|BASELINE_BACKUP|GRAPH_PARENT_OF|GRAPH_REFERS_TO|GRAPH_GUIDES",
  "rank":1
}
```
