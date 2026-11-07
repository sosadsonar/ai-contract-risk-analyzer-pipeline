"""M7 sơ bộ: căn chỉnh IoU ≥ 0.5 + macro-F1 (BRD 8.3)."""

from ai_pipeline.evaluation.metrics.clause_classification import (
    GoldSpan,
    PredClause,
    align,
    evaluate_clause_classification,
    iou,
)


def test_iou_and_greedy_alignment_is_one_to_one():
    assert iou((0, 10), (0, 10)) == 1.0 and iou((0, 10), (10, 20)) == 0.0
    gold = [GoldSpan(0, 10, "A"), GoldSpan(10, 20, "B")]
    pred = [PredClause(0, 20, ("A",)), PredClause(0, 9, ("A",))]
    # IoU giảm dần: (g0,p1)=0.9 trước; (g0,p0) bị loại vì g0 đã dùng; (g1,p0)=0.5 còn lại → 1-1
    assert align(gold, pred) == [(0, 1), (1, 0)]


def test_perfect_prediction_gives_macro_f1_one_over_labels_with_support():
    gold = [GoldSpan(i * 10, i * 10 + 9, "A" if i < 5 else "B") for i in range(10)]
    pred = [PredClause(g.start, g.end, (g.label,)) for g in gold]
    r = evaluate_clause_classification(gold, pred)
    assert r["macro_f1"] == 1.0 and r["aligned"] == 10 and r["gold_unmatched"] == r["pred_unmatched"] == 0


def test_multilabel_prediction_counts_gold_hit_but_extra_label_is_fp():
    gold = [GoldSpan(i * 10, i * 10 + 9, "A") for i in range(5)]
    pred = [PredClause(g.start, g.end, ("A", "B")) for g in gold]
    r = evaluate_clause_classification(gold, pred, min_support=5)
    assert r["per_label"]["A"]["recall"] == 1.0 and r["per_label"]["B"]["fp"] == 5
    assert r["macro_labels"] == ["A"] and r["macro_f1"] == 1.0  # B không đủ support → không vào macro


def test_unmatched_gold_is_miss_and_unmatched_pred_is_false_positive():
    gold = [GoldSpan(i * 10, i * 10 + 9, "A") for i in range(5)]
    pred = [PredClause(g.start, g.end, ("A",)) for g in gold[:4]] + [PredClause(500, 510, ("A",))]
    r = evaluate_clause_classification(gold, pred)
    a = r["per_label"]["A"]
    assert (a["tp"], a["fn"], a["fp"]) == (4, 1, 1) and r["gold_unmatched"] == 1 and r["pred_unmatched"] == 1


def test_below_min_support_reported_and_macro_none_when_nothing_scored():
    gold = [GoldSpan(0, 5, "A"), GoldSpan(10, 15, "A")]
    r = evaluate_clause_classification(gold, [PredClause(0, 5, ("A",))])
    assert r["macro_f1"] is None and r["labels_below_min_support"] == ["A"]
