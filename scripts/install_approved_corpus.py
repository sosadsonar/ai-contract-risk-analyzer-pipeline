"""Install an approved, hash-pinned internal corpus without publishing law text."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.legal.corpus_loader import load_corpus

BASE = {"provisions.jsonl", "edges.jsonl", "label_map.yaml"}
ALLOWED = BASE | {"review_receipts.json"}


def install(source: Path, target: Path, metadata_path: Path, private_root: Path) -> dict:
    source, target, private_root = source.resolve(), target.resolve(), private_root.resolve()
    if private_root not in target.parents:
        raise ValueError("destination must be below the private directory")
    if target.exists():
        raise FileExistsError(target)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    if metadata.get("usage_scope") != "INTERNAL_REPO_ONLY":
        raise ValueError("installer expects explicit INTERNAL_REPO_ONLY metadata")
    checksums = metadata["release_checksums"]
    if not BASE.issubset(checksums) or not set(checksums).issubset(ALLOWED):
        raise ValueError("unexpected release checksum keys")
    payload = {name: (source / name).read_bytes() for name in checksums}
    for name, data in payload.items():
        if hashlib.sha256(data).hexdigest() != checksums[name]:
            raise ValueError(f"release checksum mismatch: {name}")
    # Validate exactly the file set to install, including any required source receipts.
    payload["manifest.yaml"] = (source / "manifest.yaml").read_bytes()
    private_root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".corpus-install-", dir=private_root) as staged:
        snapshot = Path(staged)
        for name, data in payload.items():
            (snapshot / name).write_bytes(data)
        corpus = load_corpus(snapshot, allow_draft=False)
        if (corpus.corpus_version != metadata["corpus_version"]
                or corpus.graph_version != metadata["graph_version"]):
            raise ValueError("release version differs from pinned metadata")
    target.mkdir(parents=True, exist_ok=False)
    created = []
    try:
        for name, data in payload.items():
            file = target / name
            with file.open("xb") as stream:
                created.append(file)
                stream.write(data)
    except OSError:
        for file in reversed(created):
            file.unlink(missing_ok=True)
        target.rmdir()
        raise
    return {"corpus_version": corpus.corpus_version, "graph_version": corpus.graph_version,
            "release_status": corpus.release_status, "provisions": len(corpus.provisions),
            "installed_at": str(target), "usage_scope": "INTERNAL_REPO_ONLY"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    private = Path(__file__).resolve().parents[1] / ".local"
    print(json.dumps(install(args.source, args.destination, args.metadata, private)))


if __name__ == "__main__":
    main()
