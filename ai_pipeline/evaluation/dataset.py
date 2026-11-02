"""Strict, root-contained loader for the evaluation manifest in TDD §18.2."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_GOLD_FIELDS = (
    "gold_segmentation",
    "gold_clause_labels",
    "gold_risks",
    "injected_errors",
    "privacy_gold",
)


@dataclass(frozen=True)
class EvaluationDocument:
    doc_id: str
    source_path: Path
    role_variants: tuple[str, ...]
    gold_segmentation: Any
    gold_clause_labels: Any
    gold_risks: Any
    injected_errors: Any
    privacy_gold: Any


@dataclass(frozen=True)
class EvaluationDataset:
    dataset: str
    dataset_version: str
    manifest_path: Path
    documents: tuple[EvaluationDocument, ...]


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON file: {path.name}") from exc


def _required_text(obj: dict[str, Any], field: str, owner: str) -> str:
    value = obj.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{owner}.{field} must be non-empty text")
    return value


def _resolve_file(root: Path, value: Any, owner: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{owner} must name a non-empty relative path")
    raw_path = Path(value)
    if raw_path.is_absolute() or raw_path.drive:
        raise ValueError(f"{owner} must be relative to dataset root")
    resolved = (root / raw_path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{owner} path escapes dataset root")
    if not resolved.is_file():
        raise ValueError(f"{owner}: referenced file does not exist")
    return resolved


def load_dataset(manifest_path: Path) -> EvaluationDataset:
    """Load manifest/gold JSON while rejecting duplicate keys and path escapes."""
    manifest_path = Path(manifest_path).resolve()
    if not manifest_path.is_file():
        raise ValueError("dataset manifest does not exist")
    manifest = _read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError("dataset manifest must be a JSON object")

    dataset = _required_text(manifest, "dataset", "manifest")
    dataset_version = _required_text(manifest, "dataset_version", "manifest")
    documents_raw = manifest.get("documents")
    if not isinstance(documents_raw, list) or not documents_raw:
        raise ValueError("manifest.documents must be a non-empty array")

    root = manifest_path.parent.resolve()
    seen_doc_ids: set[str] = set()
    documents = []
    for index, item in enumerate(documents_raw):
        owner = f"documents[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{owner} must be a JSON object")
        doc_id = _required_text(item, "doc_id", owner)
        if doc_id in seen_doc_ids:
            raise ValueError("document IDs must be unique")
        seen_doc_ids.add(doc_id)

        role_variants = item.get("role_variants")
        if (
            not isinstance(role_variants, list)
            or not role_variants
            or any(not isinstance(role, str) or not role.strip() for role in role_variants)
            or len(set(role_variants)) != len(role_variants)
        ):
            raise ValueError("role variants must be non-empty and unique")

        source_path = _resolve_file(root, item.get("file"), f"{owner}.file")
        artifacts = {
            field: _read_json(_resolve_file(root, item.get(field), f"{owner}.{field}"))
            for field in _GOLD_FIELDS
        }
        documents.append(EvaluationDocument(
            doc_id=doc_id,
            source_path=source_path,
            role_variants=tuple(role_variants),
            gold_segmentation=artifacts["gold_segmentation"],
            gold_clause_labels=artifacts["gold_clause_labels"],
            gold_risks=artifacts["gold_risks"],
            injected_errors=artifacts["injected_errors"],
            privacy_gold=artifacts["privacy_gold"],
        ))

    return EvaluationDataset(
        dataset=dataset,
        dataset_version=dataset_version,
        manifest_path=manifest_path,
        documents=tuple(documents),
    )
