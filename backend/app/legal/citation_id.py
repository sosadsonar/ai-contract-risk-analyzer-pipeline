"""Deterministic citation IDs, defined by TDD §14.2."""

import re

_DOCUMENT = re.compile(r"^[A-Z][A-Z0-9_]*$")
_NUMBER = re.compile(r"^[0-9]+$")
_POINT = re.compile(r"^[a-zđ]$")


def make_citation_id(
    document_id: str,
    article: str,
    clause: str | None = None,
    point: str | None = None,
) -> str:
    """Build document:artN[:clN][:ptX]; time versions share the same ID."""
    if not isinstance(document_id, str) or not _DOCUMENT.fullmatch(document_id):
        raise ValueError("invalid document_id")
    if not isinstance(article, str) or not _NUMBER.fullmatch(article):
        raise ValueError("invalid article")
    if clause is not None and (not isinstance(clause, str) or not _NUMBER.fullmatch(clause)):
        raise ValueError("invalid clause")
    if point is not None and (clause is None or not isinstance(point, str) or not _POINT.fullmatch(point)):
        raise ValueError("invalid point or missing clause")
    return ":".join(
        [document_id, f"art{article}"]
        + ([f"cl{clause}"] if clause is not None else [])
        + ([f"pt{point}"] if point is not None else [])
    )
