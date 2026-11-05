"""Local D1 timing only; never sends contract content to a provider or writes it to disk."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter_ns
from typing import Callable, TypeVar

from app.clause.segmenter import segment
from app.core.config import Settings
from app.document.canonicalizer import canonicalize
from app.document.extractor import extract
from app.document.scope_precheck import precheck
from app.privacy.masker import mask

_D1 = ("HDLD001", "HDLD002", "HDLD003", "HDLD004")
_STAGES = ("source_prepare", "scope_precheck", "pii_mask", "segmentation", "local_preprocessing")

T = TypeVar("T")


def percentile(values: list[int], fraction: float) -> int:
    """Nearest-rank percentile, including the maximum for p90 when n=4."""
    if not values or not 0 < fraction <= 1:
        raise ValueError("nonempty samples and 0 < fraction <= 1 required")
    return sorted(values)[math.ceil(len(values) * fraction) - 1]


def _stats(values: list[int]) -> dict[str, float | int]:
    return {
        "samples": len(values),
        "p50_ms": round(percentile(values, 0.5) / 1_000_000, 3),
        "p90_ms": round(percentile(values, 0.9) / 1_000_000, 3),
    }


def _timed(fn: Callable[[], T], clock: Callable[[], int]) -> tuple[T, int]:
    before = clock()
    result = fn()
    elapsed = clock() - before
    if elapsed < 0:
        raise ValueError("monotonic clock moved backwards")
    return result, elapsed


def benchmark_d1(data_root: Path, *, repeats: int = 5, cfg: Settings | None = None,
                 clock: Callable[[], int] = perf_counter_ns) -> dict:
    """Time actual local stages on 001-004, with no gold-label or network use.

    DOC 001-003 have no supported extractor: their hashed Word-produced text
    snapshots are canonicalized locally. DOCX 004 goes through the real extractor.
    Report contains counts and timings only; no content or paths.
    """
    if repeats < 1:
        raise ValueError("repeats must be positive")
    cfg = cfg or Settings()
    receipt = json.loads((data_root / "data/releases/v06-rc1/manifest.json").read_text(encoding="utf-8"))
    if receipt["release_id"] != "v06-rc1":
        raise ValueError("unexpected D1 release")

    files = []
    for name in _D1:
        kind = "docx" if name == "HDLD004" else "word_text_snapshot"
        relative = (f"data/raw/contracts/{name}.docx" if kind == "docx"
                    else f"data/processed/raw_text/{name}.txt")
        path = data_root / relative
        expected = receipt["files"][relative]
        with path.open("rb") as source:
            actual = hashlib.file_digest(source, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"D1 input hash mismatch: {name}")
        files.append((name, kind, path))

    stage_samples: dict[str, list[int]] = {stage: [] for stage in _STAGES}
    cases = []
    for name, kind, path in files:
        samples: dict[str, list[int]] = {stage: [] for stage in _STAGES}
        clause_count = None
        for _ in range(repeats):
            start = clock()
            if kind == "docx":
                extracted, elapsed = _timed(lambda: extract(path, "docx", max_docx_chars=cfg.MAX_DOCX_CHARS,
                                                             max_upload_bytes=cfg.MAX_UPLOAD_MB * 1024 * 1024), clock)
                text = extracted.canonical_text
            else:
                text, elapsed = _timed(lambda: canonicalize([path.read_text(encoding="utf-8")]), clock)
            samples["source_prepare"].append(elapsed)
            scope, elapsed = _timed(lambda: precheck(text, cfg), clock)
            if not scope.accept:
                raise ValueError(f"D1 input out of scope: {name}")
            samples["scope_precheck"].append(elapsed)
            masking, elapsed = _timed(lambda: mask(text), clock)
            samples["pii_mask"].append(elapsed)
            segmentation, elapsed = _timed(lambda: segment(text, masking.masked_text,
                                                            masking.pii_spans, max_clauses=cfg.MAX_CLAUSES), clock)
            samples["segmentation"].append(elapsed)
            samples["local_preprocessing"].append(clock() - start)
            count = len(segmentation.clauses)
            if clause_count is not None and clause_count != count:
                raise ValueError(f"nondeterministic segmentation: {name}")
            clause_count = count
        for stage in _STAGES:
            stage_samples[stage].extend(samples[stage])
        planned = (math.ceil(clause_count / cfg.CLAUSE_BATCH_SIZE)
                   + math.ceil(clause_count / cfg.RISK_BATCH_SIZE))
        cases.append({"id": name, "source": kind, "clauses": clause_count,
                      "planned_calls": planned, "stages": {stage: _stats(samples[stage]) for stage in _STAGES}})

    return {"release": "v06-rc1", "scope": "local_only", "repeats": repeats,
            "batch_sizes": {"clause": cfg.CLAUSE_BATCH_SIZE, "risk": cfg.RISK_BATCH_SIZE},
            "cases": cases, "stages": {stage: _stats(stage_samples[stage]) for stage in _STAGES},
            "planned_calls_p95": percentile([case["planned_calls"] for case in cases], 0.95),
            "unmeasured": ["llm_1", "retrieval_graphs", "llm_2", "assembly", "provider_latency_injection"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Time local D1 preprocessing; print metadata-only JSON")
    parser.add_argument("--data-root", type=Path, default=Path("ai_pipeline/data"))
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(benchmark_d1(args.data_root, repeats=args.repeats), ensure_ascii=False))


if __name__ == "__main__":
    main()
