"""Verify human and source receipts before admitting an approved corpus release."""

import hashlib
import json
from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from app.domain.errors import LegalCorpusConflict


def _fail(message: str) -> None:
    raise LegalCorpusConflict(f"review_receipts.json: {message}")


def _today() -> date:
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()


def _date(value: Any) -> date:
    if not isinstance(value, str):
        _fail("missing review/source date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _fail("invalid review/source date")
    if parsed.isoformat() != value:
        _fail("review/source date must be YYYY-MM-DD")
    return parsed


def _reviewed(row: dict) -> None:
    if row.get("decision") != "APPROVED":
        _fail("pending or rejected human decision")
    first, second = row.get("reviewer_n2"), row.get("reviewer_independent")
    if not all(isinstance(x, str) and x.strip() for x in (first, second)) or first == second:
        _fail("two distinct named reviewers required")
    if _date(row.get("reviewed_on")) > _today():
        _fail("future review date")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _items(bundle: dict, field: str) -> list[dict]:
    value = bundle.get(field)
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        _fail(f"{field}: expected list of receipts")
    return value


def _unique_index(rows: list[dict], fields: tuple[str, ...], name: str) -> dict[tuple, dict]:
    indexed = {}
    for row in rows:
        key = tuple(row.get(field) for field in fields)
        if any(not isinstance(part, str) or not part for part in key) or key in indexed:
            _fail(f"{name}: missing or duplicate receipt identity")
        indexed[key] = row
    return indexed


def _source(row: dict, sources: dict[tuple, dict]) -> None:
    if (row.get("source_id"),) not in sources:
        _fail("unknown source ID")
    if not isinstance(row.get("source_locator"), str) or not row["source_locator"].strip():
        _fail("missing official page/article locator")


def validate_review_bundle(corpus: Any, raw: bytes) -> None:
    """Match signed review coverage to exact runtime content, mapping and graph."""
    try:
        bundle = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise LegalCorpusConflict("review_receipts.json: invalid JSON/UTF-8") from exc
    if not isinstance(bundle, dict) or set(bundle) != {"sources", "provisions", "edges", "labels", "release"}:
        _fail("incomplete review bundle")
    sources = _unique_index(_items(bundle, "sources"), ("source_id",), "sources")
    if not sources:
        _fail("empty source register")
    for source in sources.values():
        digest = source.get("source_sha256")
        url = source.get("source_url")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            _fail("invalid source SHA-256")
        if not isinstance(url, str) or urlparse(url).scheme != "https" or not urlparse(url).netloc:
            _fail("official source URL must use HTTPS")
        if _date(source.get("accessed_on")) > _today() or source.get("rights_status") != "APPROVED":
            _fail("source access date or rights decision unverified")

    provisions = _unique_index(_items(bundle, "provisions"), ("citation_id", "version"), "provisions")
    expected_provisions = {(p.citation_id, p.version) for p in corpus.provisions}
    if set(provisions) != expected_provisions:
        _fail("provision review coverage differs from runtime corpus")
    for provision in corpus.provisions:
        receipt = provisions[(provision.citation_id, provision.version)]
        _reviewed(receipt)
        _source(receipt, sources)
        if sources[(receipt["source_id"],)].get("document_id") != provision.document_id:
            _fail("provision document/source mismatch")
        if receipt.get("content_sha256") != hashlib.sha256(provision.content.encode("utf-8")).hexdigest():
            _fail("provision content hash mismatch")
        expected_end = provision.effective_to.isoformat() if provision.effective_to else None
        if (receipt.get("effective_from") != provision.effective_from.isoformat()
                or receipt.get("effective_to") != expected_end):
            _fail("provision effective interval mismatch")
        if not isinstance(receipt.get("amendment_chain"), str) or not receipt["amendment_chain"].strip():
            _fail("missing amendment history review")

    edge_fields = ("from_citation_id", "to_citation_id", "edge_type", "origin")
    edges = _unique_index(_items(bundle, "edges"), edge_fields, "edges")
    if set(edges) != {tuple(getattr(e, field) for field in edge_fields) for e in corpus.edges}:
        _fail("edge review coverage differs from runtime graph")
    for receipt in edges.values():
        _reviewed(receipt)
        _source(receipt, sources)

    labels = _unique_index(_items(bundle, "labels"), ("label", "citation_id"), "labels")
    expected_labels = {(label, cid): weight for label, weights in corpus.label_map.items()
                       for cid, weight in weights.items()}
    if set(labels) != set(expected_labels):
        _fail("label review coverage differs from runtime mapping")
    for key, receipt in labels.items():
        _reviewed(receipt)
        _source(receipt, sources)
        if isinstance(receipt.get("weight"), bool) or receipt.get("weight") != expected_labels[key]:
            _fail("label weight differs from reviewed mapping")
    release = bundle["release"]
    if not isinstance(release, dict):
        _fail("missing release decision")
    _reviewed(release)
    if not isinstance(release.get("note"), str) or not release["note"].strip():
        _fail("missing release decision note")
