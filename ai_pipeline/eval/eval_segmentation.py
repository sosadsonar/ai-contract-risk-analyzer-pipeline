from typing import List, Tuple, Dict

"""
LƯU Ý THUẬT TOÁN:
evaluate_clause_segmentation() sử dụng phương pháp Greedy Bipartite Matching 
theo IoU giảm dần. Đây là giải pháp xấp xỉ (Greedy Approximation) thay vì tối ưu toàn 
cục bằng Hungarian Algorithm (Kuhn-Munkres).

Lý do: Trong văn bản hợp đồng lao động chuẩn, các điều khoản có tính chất tuần tự, 
rất hiếm khi xảy ra chồng lấn nhiều tầng phức tạp. Giải pháp Greedy vừa đảm bảo 
tốc độ xử lý O(N*logN) vượt trội trên dataset quy mô 20-100 hợp đồng, vừa đủ 
chính xác để benchmark span-level IoU.
"""

def compute_char_iou(span_a: Tuple[int, int], span_b: Tuple[int, int]) -> float:
    start_inter, end_inter = max(span_a[0], span_b[0]), min(span_a[1], span_b[1])
    intersection = max(0, end_inter - start_inter)
    start_union, end_union = min(span_a[0], span_b[0]), max(span_a[1], span_b[1])
    union = end_union - start_union
    return intersection / union if union > 0 else 0.0

def evaluate_clause_segmentation(gold_spans: List[Tuple[int, int]], pred_spans: List[Tuple[int, int]], iou_threshold: float = 0.80) -> Dict[str, float]:
    if not pred_spans and not gold_spans: return {"f1": 1.0, "tp": 0, "fp": 0, "fn": 0}
    if not pred_spans or not gold_spans: return {"f1": 0.0, "tp": 0, "fp": len(pred_spans), "fn": len(gold_spans)}

    pair_candidates = []
    for g_idx, gold in enumerate(gold_spans):
        for p_idx, pred in enumerate(pred_spans):
            iou = compute_char_iou(gold, pred)
            if iou >= iou_threshold:
                pair_candidates.append((iou, g_idx, p_idx))

    pair_candidates.sort(key=lambda x: x[0], reverse=True)
    matched_gold, matched_pred = set(), set()
    tp = 0

    for iou, g_idx, p_idx in pair_candidates:
        if g_idx not in matched_gold and p_idx not in matched_pred:
            matched_gold.add(g_idx)
            matched_pred.add(p_idx)
            tp += 1

    fp, fn = len(pred_spans) - tp, len(gold_spans) - tp
    precision = tp / len(pred_spans) if pred_spans else 0.0
    recall = tp / len(gold_spans) if gold_spans else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "tp": tp, "fp": fp, "fn": fn}