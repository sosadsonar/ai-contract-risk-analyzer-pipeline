<!-- nguồn: TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md | mục: 18. Evaluation Harness và gold format | 4048 ký tự | trước: 18_17-logging-quota-rate-limit-retention-va-security.md | sau: 20_19-test-strategy.md -->

# 18. Evaluation Harness và gold format

## 18.1 CLI

```bash
python -m ai_pipeline.evaluation.runner --dataset T1 --config configs/eval.yaml --output evaluation/runs/run_001/
python -m ai_pipeline.evaluation.runner --dataset T2 --metric M8 --graph-enabled true
python -m ai_pipeline.evaluation.runner --dataset T2 --metric M8 --graph-enabled false
```

Harness dùng shared modules trực tiếp, không HTTP, không product quota/rate-limit. Input de-identified. Chi phí ghi eval ledger riêng.

## 18.2 Dataset manifest

```json
{
  "dataset":"T2",
  "dataset_version":"t2_v1",
  "documents":[{
    "doc_id":"t2_001",
    "file":"contracts/t2_001.docx",
    "role_variants":["EMPLOYEE","EMPLOYER"],
    "gold_segmentation":"gold/t2_001.seg.json",
    "gold_clause_labels":"gold/t2_001.clause.json",
    "gold_risks":"gold/t2_001.risk.json",
    "injected_errors":"gold/t2_001.injected.json",
    "privacy_gold":"gold/t2_001.privacy.json"
  }]
}
```

## 18.3 Gold formats

| Artifact | Tối thiểu |
|---|---|
| seg.json | start_char,end_char,gold clause ref, offset_unit |
| clause.json | gold labels, annotator/source, taxonomy_version |
| risk.json | clause ref, role, risk_label, basis_type (gán tay ở mức clause), gold citation_id, source |
| injected.json | injection_id, clause ref, role, risk_label, gold citation_id, insertion span |
| privacy.json | PII gold spans/types + preserve-field spans |
| judge.json | output id, human labels x2, adjudicated label, judge label |
| annotation.json | item id, annotator A/B labels để tính Cohen kappa của gold annotation subset |
| context_trace.json | target clause + related clause IDs/relation + included_in_request (dev/eval only) |

Khi nạp gold clause từ dataset của data repo (bản v06 trở đi): mỗi dòng một nhãn; `clause_text` không gồm heading/phần hành chính; mỗi dòng có `offset_quality` ∈ {`EXACT`, `CONTEXT`}. Dòng `CONTEXT` giữ `span=null` ở phía consumer, **không** được chấm như gold span chính xác (M1, M4); source-reference span riêng chỉ dùng để highlight/đối chiếu. Dataset này là gold **nhãn clause**; gold segmentation cho M1 vẫn do người sửa tay ranh giới (BRD 8.2 quy tắc 3).

## 18.4 Metric implementation mapping

| Chỉ số | Module | Ghi chú |
|---|---|---|
| M1 | metrics/segmentation.py | IoU char >=0.80, greedy decreasing IoU. |
| M2 | metrics/risk_classification.py | Macro-F1 (clause,role,risk label). |
| M3a | metrics/citation_validity.py | candidate + corpus + effectivity. |
| M3b | metrics/citation_relevance.py | human/judge import. |
| M4 | metrics/quote_span.py | exact substring + code-point offset. |
| M5 | metrics/injected_recall.py | clause, role, label. |
| M6 | metrics/judge_calibration.py | Judge-human agreement + kappa. |
| M7 | metrics/clause_classification.py | Macro-F1 per clause label. |
| M8 | metrics/retrieval.py | Recall@5 graph on/off, **cùng final_k**. |
| BRD 7.3 privacy | metrics/privacy.py | PII recall theo nhóm + preserve rate. |
| Annotation agreement | metrics/annotation_agreement.py | Cohen kappa trên >=20% item gán đôi theo BRD 8.2. |
| BL-1 | metrics/baseline_comparison.py | Citation error rate system vs baseline nếu chưa cut. |

## 18.5 M8 protocol - predicted labels là primary

Primary M8 chạy **pipeline thực tế**: segmentation + **predicted clause labels** -> retrieval. Đây là số báo chính vì FR-12 runtime dùng predicted labels. Graph on/off dùng cùng input, model output cache (nếu hợp lệ), same `final_k`, same corpus/config ngoài graph flag.

Có thể chạy thêm `M8-oracle-labels` với gold clause labels để chẩn đoán retriever độc lập khỏi M7, nhưng phải ghi rõ đây là diagnostic, không thay M8 chính.

## 18.6 Clause Graph evidence

FR-31 không có metric chất lượng riêng trong BRD. Harness xuất ContextResolutionTrace và test fixture xác nhận REFERS_TO/PARENT_OF context được đưa vào Risk request. Đây là bằng chứng kỹ thuật; không tuyên bố “graph cải thiện accuracy” nếu chưa có metric/upstream requirement.

Evaluation output luôn ghi version pins, config snapshot và commit. Locked eval cấm override prompt/config ngoài allowlist sau MS-3.
