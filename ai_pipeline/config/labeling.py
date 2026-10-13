"""
Rule chuyển type_scores (điểm tự tin 12 nhãn) -> clause_type (danh sách nhãn
được gán cho clause).

⚠️ ĐÓNG BĂNG: MultiLabelRule + logic resolve_multi_labels. Đổi bất cứ giá trị
nào (secondary_threshold, max_labels, tie-break...) thì phải tăng version
(ml-v1 -> ml-v2) và sửa test khóa giá trị có chủ đích.

secondary_threshold=0.60 và max_labels=3 hiện chỉ là điểm khởi đầu (đề xuất
của Người 1) — chạy trên tập dev gán tay để chỉnh trước khi khóa ml-v1 thật.
"""

from dataclasses import dataclass

from config.taxonomy import CLAUSE_LABELS, CLAUSE_LABEL_SET


@dataclass(frozen=True, slots=True)
class MultiLabelRule:
    version: str = "ml-v1"
    secondary_threshold: float = 0.60  # một ngưỡng chung cho mọi nhãn, không theo tier
    max_labels: int = 3
    # nhãn top-1 luôn được giữ để clause_type không rỗng


MULTI_LABEL_RULE = MultiLabelRule()


def validate_scores(type_scores: dict[str, float]) -> None:
    """Chặn type_scores thiếu/thừa nhãn hoặc ngoài khoảng [0, 1]."""
    if set(type_scores) != CLAUSE_LABEL_SET:
        missing = CLAUSE_LABEL_SET - set(type_scores)
        extra = set(type_scores) - CLAUSE_LABEL_SET
        raise ValueError(
            f"type_scores phải đủ 12 nhãn. Thiếu: {sorted(missing)}, thừa: {sorted(extra)}"
        )
    for label, s in type_scores.items():
        if not 0.0 <= s <= 1.0:
            raise ValueError(f"Score '{label}' = {s} ngoài [0, 1]")


def resolve_multi_labels(
    type_scores: dict[str, float], rule: MultiLabelRule = MULTI_LABEL_RULE
) -> list[str]:
    """Chọn clause_type từ type_scores theo MultiLabelRule.

    - Nhãn top-1 (điểm cao nhất) luôn được giữ, kể cả khi dưới threshold.
    - Các nhãn phụ được thêm vào theo thứ tự điểm giảm dần nếu score >=
      secondary_threshold, tối đa max_labels nhãn.
    - Tie-break theo thứ tự nhãn trong CLAUSE_LABELS (taxonomy.py) khi điểm
      bằng nhau, để kết quả ổn định/tái lập được.
    """
    validate_scores(type_scores)
    ranked = sorted(
        type_scores.items(), key=lambda kv: (-kv[1], CLAUSE_LABELS.index(kv[0]))
    )
    labels = [ranked[0][0]]
    for label, score in ranked[1:]:
        if len(labels) >= rule.max_labels:
            break
        if score >= rule.secondary_threshold:
            labels.append(label)
    return labels


def build_clause(clause_id, clause_number, span, original_text, type_scores) -> dict:
    """Dựng object clause đúng field cho schema v2 (chưa gắn routing risk)."""
    return {
        "clause_id": clause_id,
        "clause_number": clause_number,
        "span": {"start_char": span[0], "end_char": span[1]} if span else None,
        "original_text": original_text,
        "clause_type": resolve_multi_labels(type_scores),
        "type_scores": dict(type_scores),
    }
