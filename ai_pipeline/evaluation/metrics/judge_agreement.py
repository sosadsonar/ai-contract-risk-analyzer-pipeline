"""M6 — hiệu chuẩn LLM judge so với người chấm (X-08 khung, BRD §8.3: đồng thuận ≥ 0.80 VÀ Cohen κ ≥ 0.6).

Judge (một model Claude, BRD OI-11) chỉ được dùng thay người chấm M3b/M9 khi `passes` = True trên mẫu hiệu
chuẩn 40 output. Module chỉ tính số; không gọi judge, không tự chọn model.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

AGREEMENT_THRESHOLD = 0.80
KAPPA_THRESHOLD = 0.60


@dataclass(frozen=True)
class PairedRating:
    item_id: str
    human: str
    judge: str


def cohen_kappa(pairs: list[PairedRating]) -> float | None:
    n = len(pairs)
    if not n:
        return None
    po = sum(p.human == p.judge for p in pairs) / n
    h, j = Counter(p.human for p in pairs), Counter(p.judge for p in pairs)
    pe = sum(h[c] * j[c] for c in set(h) | set(j)) / (n * n)
    if pe == 1:
        return 1.0 if po == 1 else None
    return (po - pe) / (1 - pe)


def evaluate_judge(pairs: Iterable[PairedRating]) -> dict:
    rows = list(pairs)
    ids = [p.item_id for p in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("item_id must be unique")
    n = len(rows)
    agreement = sum(p.human == p.judge for p in rows) / n if n else None
    kappa = cohen_kappa(rows)
    passes = agreement is not None and kappa is not None and agreement >= AGREEMENT_THRESHOLD and kappa >= KAPPA_THRESHOLD
    return {"metric": "M6", "n": n, "agreement": agreement, "cohen_kappa": kappa,
            "thresholds": {"agreement": AGREEMENT_THRESHOLD, "kappa": KAPPA_THRESHOLD}, "passes": passes,
            "confusion": {f"{a}->{b}": c for (a, b), c in sorted(Counter((p.human, p.judge) for p in rows).items())}}
