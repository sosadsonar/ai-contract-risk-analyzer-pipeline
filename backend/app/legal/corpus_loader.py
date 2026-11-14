"""Read the closed legal corpus from data files without network access (C-12a)."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from app.domain.errors import LegalCorpusConflict

_FILES = ("provisions.jsonl", "edges.jsonl", "label_map.yaml")
_REVIEW_FILE = "review_receipts.json"
_LEGACY_VERSIONS = {"legal_corpus_2026-11-14_v02", "fixture_v1"}
_LEGACY_V1_CHECKSUMS = {
    "provisions.jsonl": "f8a3b6b5bd34d0352da1dad05e156b246cd78e470386c5634732073151dfb44b",
    "edges.jsonl": "bce0f9dcf457f130493816ff3e3281268abaf2c1b760696cb49452fe91f9e098",
    "label_map.yaml": "e9b652af68e25ea55f2d7bf32599256aea9a2d1cf4afda416ef880f2a4dc89ad",
}
_PROVISION_KEYS = {
    "citation_id", "document_id", "document_name", "version", "article", "clause",
    "point", "parent_path", "content", "effective_from", "effective_to",
}
_EDGE_KEYS = {"from_citation_id", "to_citation_id", "edge_type", "origin"}


@dataclass(frozen=True)
class LegalProvision:
    citation_id: str
    document_id: str
    document_name: str
    version: str
    article: str
    clause: str | None
    point: str | None
    parent_path: tuple[str, ...]
    content: str
    effective_from: date
    effective_to: date | None


@dataclass(frozen=True)
class LegalEdge:
    from_citation_id: str
    to_citation_id: str
    edge_type: str
    origin: str


@dataclass(frozen=True)
class LegalCorpus:
    corpus_version: str
    graph_version: str
    timezone: str
    release_status: str
    provisions: tuple[LegalProvision, ...]
    edges: tuple[LegalEdge, ...]
    label_map: dict[str, dict[str, float]]


def _date(raw: Any, field: str) -> date | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise LegalCorpusConflict(f"{field}: expected ISO date string")
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise LegalCorpusConflict(f"{field}: invalid ISO date") from exc
    if parsed.isoformat() != raw:
        raise LegalCorpusConflict(f"{field}: expected YYYY-MM-DD")
    return parsed


class _UniqueKeyLoader(yaml.SafeLoader):
    """Reject YAML mappings that silently shadow a previous legal metadata key."""


def _unique_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode) -> dict:
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str):
            raise LegalCorpusConflict("YAML mapping keys must be strings")
        if key in mapping:
            raise LegalCorpusConflict(f"YAML duplicate key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def _read_yaml(raw: bytes, name: str) -> dict:
    try:
        obj = yaml.load(raw.decode("utf-8"), Loader=_UniqueKeyLoader)
    except (UnicodeError, yaml.YAMLError) as exc:
        raise LegalCorpusConflict(f"{name}: invalid YAML/UTF-8") from exc
    if not isinstance(obj, dict):
        raise LegalCorpusConflict(f"{name}: expected mapping")
    return obj


def _read_jsonl(raw: bytes, name: str, required: set[str]) -> list[dict]:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise LegalCorpusConflict(f"{name}: invalid UTF-8") from exc
    result = []
    for line_no, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            def unique_pairs(pairs: list[tuple[str, Any]]) -> dict:
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise LegalCorpusConflict(f"{name}:{line_no}: duplicate JSON key {key}")
                    result[key] = value
                return result

            obj = json.loads(line, object_pairs_hook=unique_pairs)
        except json.JSONDecodeError as exc:
            raise LegalCorpusConflict(f"{name}:{line_no}: invalid JSON") from exc
        if not isinstance(obj, dict) or set(obj) != required:
            raise LegalCorpusConflict(f"{name}:{line_no}: expected fields {sorted(required)}")
        result.append(obj)
    return result


def load_corpus(root: Path, *, allow_draft: bool = False) -> LegalCorpus:
    """Verify SHA-256 before parsing. Draft corpus is never loaded by default."""
    root = Path(root)
    try:
        manifest = _read_yaml((root / "manifest.yaml").read_bytes(), "manifest.yaml")
        checksums = manifest["checksums"]
        status = manifest["release_status"]
        if status not in {"DRAFT", "APPROVED"}:
            raise LegalCorpusConflict("manifest.yaml: invalid release_status")
        needs_review = status == "APPROVED" and manifest["corpus_version"] not in _LEGACY_VERSIONS
        if needs_review and _REVIEW_FILE not in checksums:
            raise LegalCorpusConflict("manifest.yaml: missing review_receipts.json checksum")
        expected_files = set(_FILES) | ({_REVIEW_FILE} if _REVIEW_FILE in checksums else set())
        if not isinstance(checksums, dict) or set(checksums) != expected_files:
            raise LegalCorpusConflict("manifest.yaml: incomplete checksums")
        if manifest["corpus_version"] == "legal_corpus_2026-11-14_v02" and checksums != _LEGACY_V1_CHECKSUMS:
            raise LegalCorpusConflict("manifest.yaml: immutable v1 checksum changed")
        raw = {name: (root / name).read_bytes() for name in expected_files}
        for name in expected_files:
            if checksums[name] != hashlib.sha256(raw[name]).hexdigest():
                raise LegalCorpusConflict(f"{name}: SHA-256 mismatch")
        if status != "APPROVED" and not allow_draft:
            raise LegalCorpusConflict("manifest.yaml: corpus awaits Data/Legal reviewer sign-off")
        provisions = []
        for obj in _read_jsonl(raw["provisions.jsonl"], "provisions.jsonl", _PROVISION_KEYS):
            if not isinstance(obj["parent_path"], list):
                raise LegalCorpusConflict("provisions.jsonl: parent_path must be an array")
            obj["parent_path"] = tuple(obj["parent_path"])
            obj["effective_from"] = _date(obj["effective_from"], "effective_from")
            obj["effective_to"] = _date(obj["effective_to"], "effective_to")
            provisions.append(LegalProvision(**obj))
        edges = [LegalEdge(**obj) for obj in _read_jsonl(raw["edges.jsonl"], "edges.jsonl", _EDGE_KEYS)]
        label_map = _read_yaml(raw["label_map.yaml"], "label_map.yaml")
        corpus = LegalCorpus(
            corpus_version=manifest["corpus_version"],
            graph_version=manifest["graph_version"],
            timezone=manifest["timezone"],
            release_status=status,
            provisions=tuple(provisions),
            edges=tuple(edges),
            label_map=label_map,
        )
        from app.legal.corpus_validator import validate_corpus

        validate_corpus(corpus)
        if corpus.corpus_version == "fixture_v1" and any(p.document_id != "TESTLAW" for p in corpus.provisions):
            raise LegalCorpusConflict("fixture_v1 only permits TESTLAW fixtures")
        if needs_review:
            from app.legal.corpus_review import validate_review_bundle

            validate_review_bundle(corpus, raw[_REVIEW_FILE])
        return corpus
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise LegalCorpusConflict(f"corpus read/metadata error: {exc}") from exc
