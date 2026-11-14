"""M10 — phát hiện mâu thuẫn giữa các điều khoản (BRD §8.3, FR-32, X-27 phần metric của N1).

Quy tắc chấm (BRD): một cặp (a, b) được coi là PHÁT HIỆN khi rủi ro của một trong hai điều có
`related_clause_ids` chứa điều còn lại. Báo recall trên cặp mâu thuẫn cài, tỷ lệ báo nhầm trên cặp đối
chứng nhất quán, và so Graph tắt/mở (cùng D3, cùng cấu hình khác). Không có ngưỡng nghiệm thu (báo cáo).

Mặc định KHÔNG bắt buộc basis_type = AMBIGUOUS (BRD chỉ nêu related_clause_ids); `require_ambiguous=True`
cho chẩn đoán chặt theo FR-32. Khoảng tin cậy: cluster bootstrap theo document (seed cố định).
D3 là hạng mục chẩn đoán giai đoạn 2 (BRD §8.3 ghi chú) — chưa có gói dữ liệu D3 thì không báo đạt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from ai_pipeline.evaluation.metrics.bootstrap import bootstrap_cluster_interval


@dataclass(frozen=True)
class ClausePair:
    pair_id: str
    document_id: str
    clause_a: str
    clause_b: str
    contradictory: bool  # True = cặp cài mâu thuẫn; False = cặp đối chứng nhất quán


@dataclass(frozen=True)
class RiskLink:
    document_id: str
    clause_id: str
    related_clause_ids: tuple[str, ...]
    basis_type: str = ""


@dataclass(frozen=True)
class ContradictionResult:
    detected: int
    contradictory_total: int
    recall: float | None
    false_alarms: int
    control_total: int
    false_alarm_rate: float | None
    missed_pair_ids: tuple[str, ...]
    false_alarm_pair_ids: tuple[str, ...]
    recall_ci95_low: float | None = None
    recall_ci95_high: float | None = None
    false_alarm_ci95_low: float | None = None
    false_alarm_ci95_high: float | None = None
    cluster_count: int = 0

    def to_dict(self) -> dict:
        return dict(self.__dict__, missed_pair_ids=list(self.missed_pair_ids),
                    false_alarm_pair_ids=list(self.false_alarm_pair_ids))


def _links(risks: Iterable[RiskLink], require_ambiguous: bool) -> set[tuple[str, str, str]]:
    out: set[tuple[str, str, str]] = set()
    for r in risks:
        if require_ambiguous and r.basis_type != "AMBIGUOUS":
            continue
        for other in r.related_clause_ids:
            out.add((r.document_id, r.clause_id, other))
    return out


def _flagged(pair: ClausePair, links: set[tuple[str, str, str]]) -> bool:
    return ((pair.document_id, pair.clause_a, pair.clause_b) in links
            or (pair.document_id, pair.clause_b, pair.clause_a) in links)


def evaluate_contradiction(
    pairs: Iterable[ClausePair],
    risks: Iterable[RiskLink],
    *,
    require_ambiguous: bool = False,
    iterations: int = 1000,
    random_seed: int = 0,
) -> ContradictionResult:
    pairs = tuple(pairs)
    ids = [p.pair_id for p in pairs]
    if len(ids) != len(set(ids)):
        raise ValueError("pair_id must be unique")
    for p in pairs:
        if not p.document_id or p.clause_a == p.clause_b:
            raise ValueError("pair needs a document_id and two distinct clauses")
    links = _links(risks, require_ambiguous)
    flags = {p.pair_id: _flagged(p, links) for p in pairs}
    pos = [p for p in pairs if p.contradictory]
    neg = [p for p in pairs if not p.contradictory]
    detected = sum(flags[p.pair_id] for p in pos)
    false_alarms = sum(flags[p.pair_id] for p in neg)

    clusters: dict[str, list[ClausePair]] = {}
    for p in pairs:
        clusters.setdefault(p.document_id, []).append(p)

    def rate(rows, contradictory):
        sel = [p for p in rows if p.contradictory is contradictory]
        return sum(flags[p.pair_id] for p in sel) / len(sel) if sel else None

    rec_ci = bootstrap_cluster_interval(clusters, lambda rows: rate(rows, True),
                                        iterations=iterations, random_seed=random_seed)
    fa_ci = bootstrap_cluster_interval(clusters, lambda rows: rate(rows, False),
                                       iterations=iterations, random_seed=random_seed)
    return ContradictionResult(
        detected, len(pos), detected / len(pos) if pos else None,
        false_alarms, len(neg), false_alarms / len(neg) if neg else None,
        tuple(p.pair_id for p in pos if not flags[p.pair_id]),
        tuple(p.pair_id for p in neg if flags[p.pair_id]),
        rec_ci.low, rec_ci.high, fa_ci.low, fa_ci.high, rec_ci.cluster_count,
    )


def compare_graph_on_off(
    pairs: Iterable[ClausePair],
    risks_by_mode: Mapping[str, Iterable[RiskLink]],
    **kwargs,
) -> dict[str, dict]:
    """M10 Graph tắt/mở: cùng cặp D3, mỗi mode một bộ dự đoán ('graph_off', 'graph_on')."""
    pairs = tuple(pairs)
    if set(risks_by_mode) != {"graph_off", "graph_on"}:
        raise ValueError("risks_by_mode must have exactly graph_off and graph_on")
    return {mode: evaluate_contradiction(pairs, risks, **kwargs).to_dict() for mode, risks in risks_by_mode.items()}
