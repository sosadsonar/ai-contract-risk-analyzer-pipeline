"""Closed-corpus, date-aware weighted-label + lexical retrieval (C-12b).

No draft corpus is admitted by default. This module does not produce legal
conclusions or expand graph edges; C-13 consumes its seed/pool separately.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from typing import Sequence

from rank_bm25 import BM25Okapi

from app.clause.taxonomy import validate_labels
from app.domain.errors import LegalCorpusConflict
from app.legal.corpus_loader import LegalCorpus, LegalProvision
from app.legal.corpus_validator import validate_corpus


def _tokens(value: str) -> list[str]:
    """Deterministic Unicode word baseline; Vietnamese word segmentation is future tuning."""
    return re.findall(r"\w+", unicodedata.normalize("NFC", value).casefold(), re.UNICODE)


@dataclass(frozen=True)
class BaselineCandidate:
    citation_id: str
    content: str
    document_name: str
    article: str
    version: str
    effective_from: date
    effective_to: date | None
    origin: str
    rank: int
    baseline_score: float
    bm25_normalized: float


@dataclass(frozen=True)
class BaselineResult:
    baseline_pool: tuple[BaselineCandidate, ...]
    seeds: tuple[BaselineCandidate, ...]


class BaselineRetriever:
    """Return top final_k date-valid candidates, with seed_k only for graph use."""

    def __init__(
        self,
        corpus: LegalCorpus,
        *,
        final_k: int = 8,
        seed_k: int = 3,
        allow_draft: bool = False,
    ) -> None:
        validate_corpus(corpus)
        if corpus.release_status != "APPROVED" and not allow_draft:
            raise LegalCorpusConflict("retriever: corpus awaits Data/Legal reviewer sign-off")
        if (
            isinstance(final_k, bool) or not isinstance(final_k, int) or final_k < 1
            or isinstance(seed_k, bool) or not isinstance(seed_k, int)
            or not 1 <= seed_k <= final_k
        ):
            raise ValueError("retriever: require 1 <= seed_k <= final_k")
        self._corpus = corpus
        self.final_k = final_k
        self.seed_k = seed_k

    def _effective(self, as_of: date) -> list[LegalProvision]:
        active = [
            provision for provision in self._corpus.provisions
            if provision.effective_from <= as_of
            and (provision.effective_to is None or as_of <= provision.effective_to)
        ]
        # Validated versions cannot overlap. Assert again at the selection boundary.
        if len({provision.citation_id for provision in active}) != len(active):
            raise LegalCorpusConflict("retriever: overlapping active provision versions")
        return sorted(active, key=lambda provision: provision.citation_id)

    def retrieve(self, text: str, clause_labels: Sequence[str], *, as_of: date) -> BaselineResult:
        """Normalize BM25 across *date-valid* records, then rank by TDD §14.5.

        For multiple labels, use the strongest explicitly configured weight.
        No inferred label mapping or runtime graph suggestion is used.
        """
        if not isinstance(as_of, date) or isinstance(as_of, datetime):
            raise ValueError("retriever: as_of must be a date")
        if not isinstance(text, str):
            raise ValueError("retriever: query text must be a string")
        validate_labels(clause_labels)
        active = self._effective(as_of)
        if not active:
            return BaselineResult((), ())

        query_tokens = _tokens(text)
        lexical = (
            BM25Okapi([_tokens(provision.content) or [""] for provision in active]).get_scores(query_tokens)
            if query_tokens else [0.0] * len(active)
        )
        # rank-bm25 Okapi can yield negative scores for common words; they must
        # not penalize the configured label signal after normalization.
        positive = [max(0.0, float(score)) for score in lexical]
        denominator = max(positive, default=0.0)
        # X-24: nút Điều có Khoản con chỉ chứa tiêu đề ⇒ không làm seed BM25 (điểm từ vựng = 0); Điều không
        # chia khoản vẫn là nút có nội dung. Nhận diện bằng parent_path, không thêm trường corpus.
        with_children = {":".join(p.parent_path[:-1]) for p in active if len(p.parent_path) > 2}
        ranked = []
        for provision, bm25_score in zip(active, positive):
            if provision.citation_id in with_children:
                bm25_score = 0.0
            lexical_normalized = bm25_score / denominator if denominator > 0 else 0.0
            label_weight = max(
                (self._corpus.label_map.get(label, {}).get(provision.citation_id, 0.0)
                 for label in clause_labels),
                default=0.0,
            )
            score = 0.70 * label_weight + 0.30 * lexical_normalized
            ranked.append((score, lexical_normalized, label_weight, provision))

        ranked.sort(key=lambda item: (-item[0], item[3].citation_id))
        pool = []
        for position, (score, lexical_score, label_weight, provision) in enumerate(ranked[:self.final_k], 1):
            if position <= self.seed_k:
                origin = "SEED_LABEL" if label_weight > 0 else "SEED_LEXICAL"
            else:
                origin = "BASELINE_BACKUP"
            pool.append(BaselineCandidate(
                citation_id=provision.citation_id,
                content=provision.content,
                document_name=provision.document_name,
                article=provision.article,
                version=provision.version,
                effective_from=provision.effective_from,
                effective_to=provision.effective_to,
                origin=origin,
                rank=position,
                baseline_score=score,
                bm25_normalized=lexical_score,
            ))
        return BaselineResult(tuple(pool), tuple(pool[:self.seed_k]))
