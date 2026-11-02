"""Recompute SHA-256 receipts for the legal corpus; does not grant approval."""

import hashlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1] / "data" / "legal_corpus"
FILES = ("provisions.jsonl", "edges.jsonl", "label_map.yaml")


def update(root: Path = ROOT) -> None:
    manifest_path = root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["checksums"] = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in FILES}
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    update()
