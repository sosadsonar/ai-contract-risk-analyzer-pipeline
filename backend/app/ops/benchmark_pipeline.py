"""X-05 (b): benchmark end-to-end theo stage, có tiêm độ trễ provider (TDD §17.6, OI-05 §2.5).

Đo p50/p90 cho từng stage của `pipeline.analyze` (kể cả LLM #1, retrieval/graph, LLM #2, citation, assembly) và
toàn luồng; đếm actual calls (kể cả retry), token, cost từ ledger. Provider:
  * `fake` + `--latency-ms` — đo overhead cục bộ + mô phỏng độ trễ mạng (không gửi dữ liệu đi đâu);
  * `gemini` — chỉ khi đã có key/model và dữ liệu D1 đã che; số này mới dùng để thay giá trị tạm OI-05.
Báo cáo chỉ chứa số và ID tài liệu; không nội dung, không đường dẫn.

D1 HDLD001–003 là text snapshot (.doc không hỗ trợ upload) ⇒ được dựng thành DOCX trong RAM (mỗi dòng một
paragraph) để đi đúng đường extractor; ghi `source` trong báo cáo.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from time import perf_counter_ns
from typing import Callable, Iterable

from app.ai.provider import InMemoryLedger
from app.core.enums import Stage
from app.ops.benchmark_d1 import percentile
from app.pipeline import PipelineDeps, analyze


@dataclass(frozen=True)
class BenchInput:
    doc_id: str
    data: bytes
    display_name: str
    source: str


class LatencyProvider:
    """Bọc provider, thêm độ trễ cố định mỗi request (provider latency injection)."""

    def __init__(self, inner, latency_s: float):
        self.inner, self.latency_s = inner, latency_s

    async def generate_structured(self, **kw):
        await asyncio.sleep(self.latency_s)
        return await self.inner.generate_structured(**kw)


def _ms(ns: list[int]) -> dict:
    return {"samples": len(ns), "p50_ms": round(percentile(ns, 0.5) / 1e6, 3),
            "p90_ms": round(percentile(ns, 0.9) / 1e6, 3)}


async def _one(inp: BenchInput, deps_factory: Callable[[], PipelineDeps], role: str, clock) -> tuple[dict, dict]:
    deps = deps_factory()
    marks: list[tuple[Stage, int]] = []
    start = clock()
    art = await analyze(inp.data, inp.display_name, role, session_id="bench", analysis_date=date.today(),
                        deps=deps, on_stage=lambda s: marks.append((s, clock())))
    end = clock()
    per_stage = {}
    for (stage, t0), nxt in zip(marks, [m[1] for m in marks[1:]] + [end]):
        per_stage[stage.value] = nxt - t0
    ledger = deps.ledger
    usage = {"calls": getattr(ledger, "calls", 0), "in_tokens": getattr(ledger, "in_tokens", 0),
             "out_tokens": getattr(ledger, "out_tokens", 0), "cost": getattr(ledger, "cost", 0.0),
             "errors": len(getattr(ledger, "errors", [])), "clauses": len(art.final_result["clauses"]),
             "risks": len(art.final_result["risks"])}
    return {"total": end - start, **per_stage}, usage


def benchmark_pipeline(inputs: Iterable[BenchInput], deps_factory: Callable[[], PipelineDeps], *,
                       repeats: int = 3, roles: tuple[str, ...] = ("EMPLOYEE", "EMPLOYER"),
                       clock: Callable[[], int] = perf_counter_ns) -> dict:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    samples: dict[str, list[int]] = {}
    cases = []
    for inp in inputs:
        for role in roles:
            local: dict[str, list[int]] = {}
            usage = None
            for _ in range(repeats):
                timing, usage = asyncio.run(_one(inp, deps_factory, role, clock))
                for key, value in timing.items():
                    local.setdefault(key, []).append(value)
                    samples.setdefault(key, []).append(value)
            cases.append({"id": inp.doc_id, "source": inp.source, "role": role, **usage,
                          "stages": {k: _ms(v) for k, v in local.items()}})
    calls = [c["calls"] for c in cases]
    return {"scope": "end_to_end", "repeats": repeats, "cases": cases,
            "stages": {k: _ms(v) for k, v in samples.items()},
            "calls_max": max(calls) if calls else 0,
            "calls_p95": percentile(calls, 0.95) if calls else 0,
            "reserve_formula": "ceil(1.2 * max(calls_max, 33))",
            "reserve_suggestion": math.ceil(1.2 * max(max(calls) if calls else 0, 33))}


def _docx_from_text(text: str) -> bytes:
    from docx import Document

    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def d1_inputs(data_root: Path) -> list[BenchInput]:
    out = []
    for name in ("HDLD001", "HDLD002", "HDLD003"):
        text = (data_root / f"data/processed/raw_text/{name}.txt").read_text(encoding="utf-8")
        out.append(BenchInput(name, _docx_from_text(text), f"{name}.docx", "word_text_snapshot_as_docx"))
    out.append(BenchInput("HDLD004", (data_root / "data/raw/contracts/HDLD004.docx").read_bytes(), "HDLD004.docx",
                          "docx"))
    return out


def main() -> None:
    from app.ai.dev_fake_client import FAKE_MODEL_ID, DevFakeClient
    from app.ai.factory import make_provider
    from app.core.config import load_settings
    from app.main import load_legal
    from app.session.final_result import resolve_app_commit

    parser = argparse.ArgumentParser(description="End-to-end pipeline benchmark; prints metadata-only JSON")
    parser.add_argument("--data-root", type=Path, default=Path("ai_pipeline/data"))
    parser.add_argument("--provider", choices=("fake", "gemini"), default="fake")
    parser.add_argument("--latency-ms", type=float, default=0.0, help="độ trễ tiêm vào mỗi request")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    cfg = load_settings()
    if args.provider == "fake":
        cfg = cfg.model_copy(update={"APP_ENV": "dev", "GEMINI_MODEL_ID": cfg.GEMINI_MODEL_ID or FAKE_MODEL_ID})
        base = DevFakeClient(app_env="dev")
    else:
        base = make_provider(cfg)
    provider = LatencyProvider(base, args.latency_ms / 1000) if args.latency_ms else base
    corpus, retriever, graph = load_legal(cfg)

    def deps():
        return PipelineDeps(cfg, provider, InMemoryLedger(), corpus, retriever, graph, resolve_app_commit(cfg))

    report = benchmark_pipeline(d1_inputs(args.data_root), deps, repeats=args.repeats)
    report.update(provider=args.provider, latency_ms=args.latency_ms)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
