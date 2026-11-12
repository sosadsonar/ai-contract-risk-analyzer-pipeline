"""Source-only eligibility for clause classification; segmentation remains unchanged."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping

_ARTICLE_ONE = re.compile(r"(?im)^\s*(?:(?:điều|dieu)\s+1\b|i[.)]\s+)")
_SIGNATURE = re.compile(r"(?im)^\s*đại\s+diện\s+bên\s+[ab]\b")
_HEADING = re.compile(r"(?i)^(?:chương|mục|điều|dieu)\s+(?:\d+[a-z]?|[ivxlcdm]+)\b")
_CONTRACT_TITLE = re.compile(r"(?i)^(?:hợp\s+đồng|cộng\s+hòa|độc\s+lập|số\s*:)\b")


def is_eligible_clause_for_classification(span_text: str, structure_meta: Mapping) -> bool:
    """Decide from source text and document position, never Gold or predicted labels.

    ``structure_meta`` may carry ``before_first_article`` and ``in_signature_block``
    as document-position facts computed from the same source. Unknown position is
    treated conservatively: keep the span.
    """
    text = unicodedata.normalize("NFC", span_text).strip()
    if not text:
        return False
    if structure_meta.get("in_signature_block", False):
        return False
    if structure_meta.get("before_first_article", False):
        return False
    if _SIGNATURE.search(text):
        return False
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) == 1 and (_HEADING.match(lines[0]) or _CONTRACT_TITLE.match(lines[0])):
        # A heading with only a title has no independent normative content.
        return False
    if lines[0].endswith(":") and len(lines) == 1:
        return False
    if len(text) <= 40 and text.endswith(":"):
        # Short multiline chapeau with no completed proposition.
        return False
    return True


def source_position_metadata(clauses: list) -> list[dict[str, bool]]:
    """Compute preamble/signature regions from source-only clause order."""
    first_article = next((i for i, c in enumerate(clauses)
                          if _ARTICLE_ONE.search(c.original_text)), None)
    signature = next((i for i, c in enumerate(clauses)
                      if _SIGNATURE.search(c.original_text)), None)
    return [{"before_first_article": first_article is not None and i < first_article,
             "in_signature_block": signature is not None and i >= signature}
            for i in range(len(clauses))]
