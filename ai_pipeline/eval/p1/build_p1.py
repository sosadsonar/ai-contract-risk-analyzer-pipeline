"""Dựng bộ P1 từ D1 raw_text (chỉ D1, không dùng T1). Đầu ra: build/p1_v1/SEED/docs/*.json + manifest.json.

  python -m ai_pipeline.eval.p1.build_p1 --seed 17            # dev
  python -m ai_pipeline.eval.p1.build_p1 --seed 2026          # report (chạy một lần cho mỗi phiên bản masker)

Dữ liệu sinh ra KHÔNG commit (build/ đã nằm trong .gitignore). Chỉ commit mã nguồn.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from ai_pipeline.eval.p1.generator import doc_sha256, generate, sample_to_doc  # noqa: E402

D1_DOCS = ("HDLD001", "HDLD002", "HDLD003", "HDLD004")
D1_RAW = ROOT / "ai_pipeline" / "data" / "data" / "processed" / "raw_text"


def build(out_dir: Path, texts: dict[str, str], seed: int, n_high: int, n_std: int, n_preserve: int) -> dict:
    samples = generate(texts, seed, n_high, n_std, n_preserve)
    docs_dir = out_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    entries, kinds, muts = [], Counter(), Counter()
    for s in samples:
        doc = sample_to_doc(s)
        path = docs_dir / f"{s.doc_id}.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8")
        entries.append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "kind": s.kind, "mutation": s.mutation})
        kinds[s.kind] += 1
        muts[s.mutation] += 1
    manifest = {
        "schema": "p1_manifest_v1",
        "seed": seed,
        "documents": len(entries),
        "by_kind": dict(sorted(kinds.items())),
        "by_mutation": dict(sorted(muts.items())),
        "entries": entries,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


def load_d1(d1_dir: Path = D1_RAW) -> dict[str, str]:
    out = {}
    for doc in D1_DOCS:
        path = d1_dir / f"{doc}.txt"
        if not path.exists():
            raise SystemExit(f"thiếu D1: {path.name}")
        out[doc] = path.read_bytes().decode("utf-8")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n-high", type=int, default=100)
    ap.add_argument("--n-std", type=int, default=50)
    ap.add_argument("--n-preserve", type=int, default=100)
    ap.add_argument("--d1-dir", type=Path, default=D1_RAW)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    out = a.out or (ROOT / "build" / "p1_v1" / str(a.seed))
    m = build(out, load_d1(a.d1_dir), a.seed, a.n_high, a.n_std, a.n_preserve)
    print(f"P1 seed={m['seed']} documents={m['documents']} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
