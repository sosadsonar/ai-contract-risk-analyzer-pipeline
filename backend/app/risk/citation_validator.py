"""Citation Validator (TDD §15.4, INV-06, C-15 a).

Với mỗi rủi ro: giữ citation thuộc candidate_ids của CHÍNH clause đó VÀ có hiệu lực tại ngày phân tích
trong corpus đóng; citation ngoài candidate chỉ được đếm (log số lượng, không text) rồi lọc. Hết citation
hợp lệ ⇒ evidence_status = INSUFFICIENT_EVIDENCE (severity null do assembler tra). Runtime không chấm
relevance (M3b là thuộc tính đánh giá).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Iterable, Mapping

from app.legal.corpus_loader import LegalCorpus, LegalProvision

CITATION_VALIDATOR_VERSION = "citation_validator_v1"


@dataclass(frozen=True)
class CitationStats:
    outside_candidate: int = 0
    not_effective: int = 0
    downgraded_to_insufficient: int = 0


def effective_provisions(corpus: LegalCorpus, as_of: date) -> dict[str, LegalProvision]:
    """citation_id → provision có hiệu lực tại `as_of` (effective_to tính bao gồm)."""
    out: dict[str, LegalProvision] = {}
    for p in corpus.provisions:
        if p.effective_from <= as_of and (p.effective_to is None or as_of <= p.effective_to):
            out[p.citation_id] = p
    return out


def validate_citations(items: Iterable, candidate_ids: Mapping[str, Iterable[str]],
                       effective: Mapping[str, LegalProvision]):
    """Trả (items đã lọc citation + hạ INSUFFICIENT khi cần, CitationStats).

    `items` là `RiskItemOut` (dataclass có clause_id, citation_ids, evidence_status).
    """
    outside = not_eff = downgraded = 0
    result = []
    for it in items:
        allowed = set(candidate_ids.get(it.clause_id, ()))
        valid: list[str] = []
        for cid in it.citation_ids:
            if cid not in allowed:
                outside += 1
                continue
            if cid not in effective:
                not_eff += 1
                continue
            if cid not in valid:
                valid.append(cid)
        status = it.evidence_status
        if not valid and status == "SUPPORTED":
            status = "INSUFFICIENT_EVIDENCE"
            downgraded += 1
        result.append(replace(it, citation_ids=valid, evidence_status=status))
    return result, CitationStats(outside, not_eff, downgraded)
