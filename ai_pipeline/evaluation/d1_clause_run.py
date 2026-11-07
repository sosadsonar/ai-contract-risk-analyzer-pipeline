"""Chạy pipeline tới Clause Classification trên D1 và đo sơ bộ M1/M7 (PROGRESS W4, N1, MS-2).

    python -m ai_pipeline.evaluation.d1_clause_run --provider mock  --out evaluation/runs/w4_d1_smoke
    python -m ai_pipeline.evaluation.d1_clause_run --provider gemini --out evaluation/runs/w4_d1   # cần GEMINI_*

Luồng mỗi hợp đồng: canonicalize → mask (toàn văn) → segment → build_clause_graph → classify_clauses.
Chỉ MASKED text rời máy (INV-04); báo cáo chỉ ghi ID/số đếm/nhãn, không ghi text hợp đồng (INV-13).

Lưu ý phương pháp (đọc trước khi trích số):
  * D1 = HDLD001–004 trong `clauses_v06.csv` (BRD 0.6 §8.2; dòng `EXACT`, một nhãn/dòng, bỏ heading).
    HDLD005 trở đi là T1 — runner từ chối nạp (không tune/đo trên T1 khi phát triển). Offset của dataset tính trên file
    raw_text, còn canonical_text của pipeline có thể lệch vài ký tự (NFC, rstrip dòng) ⇒ ánh xạ bằng difflib.
  * M7 sơ bộ dùng căn chỉnh IoU ≥ 0.5 (BRD 8.3), macro chỉ tính nhãn ≥ 5 mẫu. Chỉ có ý nghĩa khi
    `--provider gemini|local`; `mock` chỉ để kiểm tra đường ống ⇒ báo cáo ghi `SMOKE_NOT_A_MEASUREMENT`.
  * "M1 proxy" so ranh giới segmentation với span NHÃN của dataset (IoU ≥ 0.80). Dataset tách ngữ nghĩa bên
    trong Điều và bỏ heading, KHÔNG phải gold segmentation ⇒ đây không phải M1 (cần X-04 sửa tay), chỉ là tham chiếu.
  * Không dùng số này để chỉnh theo T1/T2; chỉnh cấu hình chỉ trên D1/D2 và phải version config.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import difflib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from app.ai.clause_adapter import ClauseOutput, classify_clauses, masked_items_from_segmentation
from app.ai.provider import InMemoryLedger, LLMProvider, LLMResponse
from app.clause.graph_builder import ClauseGraph, Diagnostic, build_clause_graph
from app.clause.segmenter import SegmentationResult, segment
from app.core.enums import ClauseEdgeType
from app.document.canonicalizer import canonicalize
from app.privacy.masker import mask

from ai_pipeline.eval.eval_segmentation import evaluate_clause_segmentation
from ai_pipeline.evaluation.metrics.clause_classification import (
    GoldSpan,
    PredClause,
    evaluate_clause_classification,
)

DATA_ROOT = Path("ai_pipeline/data/data")
CLAUSES_CSV = DATA_ROOT / "processed" / "clauses_v06.csv"
RAW_DIR = DATA_ROOT / "processed" / "raw_text"
RUN_SCHEMA = "d1_clause_run_v1"
# BRD 0.6 §8.2: D1 = HDLD001–004 (4 HĐ Dev, 183 điều khoản REVIEWED). HDLD005+ thuộc T1 ⇒ CẤM dùng khi phát triển.
D1_CONTRACTS = ("HDLD001", "HDLD002", "HDLD003", "HDLD004")


# --------------------------------------------------------------------------------------------
# Dữ liệu D1
# --------------------------------------------------------------------------------------------


def offset_mapper(raw: str, canonical: str) -> Callable[[int], int]:
    """Ánh xạ chỉ số trong raw_text → canonical_text (canonicalize chỉ xóa/chuẩn hóa ký tự).

    Vị trí rơi vào vùng bị xóa/thay thì dời tới vị trí kế tiếp còn giữ lại.
    """
    sm = difflib.SequenceMatcher(None, raw, canonical, autojunk=False)
    anchors: list[tuple[int, int, int]] = []  # (raw_lo, raw_hi, canon_lo) cho các khối bằng nhau
    for tag, i1, i2, j1, _j2 in sm.get_opcodes():
        if tag == "equal":
            anchors.append((i1, i2, j1))
    los = [a[0] for a in anchors]

    def f(pos: int) -> int:
        import bisect

        k = bisect.bisect_right(los, pos) - 1
        if k >= 0:
            lo, hi, cj = anchors[k]
            if pos < hi:
                return cj + (pos - lo)
            return cj + (hi - lo)  # ngay sau khối: biên cuối
        return anchors[0][2] if anchors else 0

    return f


def load_d1(
    data_root: Path = DATA_ROOT, contracts: tuple[str, ...] = D1_CONTRACTS
) -> dict[str, tuple[str, list[GoldSpan]]]:
    """{contract_id: (canonical_text, [GoldSpan EXACT trên canonical])} chỉ cho hợp đồng thuộc D1."""
    outside = [c for c in contracts if c not in D1_CONTRACTS]
    if outside:
        raise ValueError(f"{outside} không thuộc D1 (HDLD001–004); HDLD005+ là T1 — không dùng khi phát triển")
    rows = list(csv.DictReader(open(data_root / "processed" / "clauses_v06.csv", encoding="utf-8")))
    out: dict[str, tuple[str, list[GoldSpan]]] = {}
    for cid in contracts:
        raw = (data_root / "processed" / "raw_text" / f"{cid}.txt").read_text(encoding="utf-8")
        canon = canonicalize([raw])
        mp = offset_mapper(raw, canon)
        spans = [
            GoldSpan(mp(int(r["start_offset"])), mp(int(r["end_offset"])), r["clause_type"])
            for r in rows
            if r["contract_id"] == cid and r["offset_quality"] == "EXACT"
        ]
        out[cid] = (canon, spans)
    return out


# --------------------------------------------------------------------------------------------
# Chạy một hợp đồng
# --------------------------------------------------------------------------------------------


@dataclass
class ContractRun:
    contract_id: str
    canonical_len: int
    pii_spans: int
    segmentation: SegmentationResult
    graph: ClauseGraph
    diagnostics: list[Diagnostic]
    output: Optional[ClauseOutput]


async def run_contract(
    contract_id: str,
    canonical: str,
    provider: Optional[LLMProvider],
    ledger,
    cfg,
    cancel: Optional[Callable[[], bool]] = None,
) -> ContractRun:
    m = mask(canonical)
    seg = segment(canonical, m.masked_text, m.pii_spans, max_clauses=cfg.MAX_CLAUSES)
    graph, diags = build_clause_graph(seg.clauses, m.masked_text)
    out = None
    if provider is not None:
        out = await classify_clauses(masked_items_from_segmentation(seg, m.masked_text), provider, ledger, cfg, cancel)
    return ContractRun(contract_id, len(canonical), len(m.pii_spans), seg, graph, diags, out)


# --------------------------------------------------------------------------------------------
# Tổng hợp
# --------------------------------------------------------------------------------------------


def summarize(runs: list[ContractRun], d1: dict[str, tuple[str, list[GoldSpan]]], *, measured: bool) -> dict:
    gold_all: list[GoldSpan] = []
    pred_all: list[PredClause] = []
    seg_gold: list[tuple[int, int]] = []
    seg_pred: list[tuple[int, int]] = []
    per_contract = []
    base = 0
    for r in runs:
        canon, gold = d1[r.contract_id]
        for g in gold:
            gold_all.append(GoldSpan(g.start + base, g.end + base, g.label))
            seg_gold.append((g.start + base, g.end + base))
        labels = {i.clause_id: tuple(i.clause_labels) for i in (r.output.items if r.output else [])}
        for c in r.segmentation.clauses:
            seg_pred.append((c.start_char + base, c.end_char + base))
            if r.output:
                pred_all.append(PredClause(c.start_char + base, c.end_char + base, labels[c.clause_id]))
        edges = r.graph.edges
        per_contract.append({
            "contract_id": r.contract_id,
            "canonical_chars": r.canonical_len,
            "pii_spans": r.pii_spans,
            "clauses": len(r.segmentation.clauses),
            "segmentation_warnings": len(r.segmentation.warnings),
            "gold_exact_spans": len(gold),
            "graph_next": sum(e.edge_type == ClauseEdgeType.NEXT for e in edges),
            "graph_parent_of": sum(e.edge_type == ClauseEdgeType.PARENT_OF for e in edges),
            "graph_diagnostics": [d.code for d in r.diagnostics],
        })
        base += len(canon) + 10
    report = {
        "schema_version": RUN_SCHEMA,
        "mode": "MEASUREMENT_PRELIMINARY_D1" if measured else "SMOKE_NOT_A_MEASUREMENT",
        "per_contract": per_contract,
        "m1_proxy_iou_0_80": evaluate_clause_segmentation(seg_gold, seg_pred),
        "m1_proxy_note": "So với span NHÃN của dataset (không phải gold segmentation) — KHÔNG phải M1.",
        "m7_preliminary": evaluate_clause_classification(gold_all, pred_all) if (measured and pred_all) else None,
    }
    if not measured:
        report["m7_note"] = "Provider giả: chỉ kiểm tra đường ống. Không có số M7."
    return report


class OtherProvider:
    """Provider giả cho smoke: gán OTHER cho mọi clause trong yêu cầu. KHÔNG dùng để đo."""

    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s) -> LLMResponse:
        req = json.loads(messages[1]["content"])
        data = {"items": [{"clause_id": i["clause_id"], "clause_labels": ["OTHER"]} for i in req["items"]]}
        return LLMResponse(data=data, model_id=model_id)


async def run_all(provider: Optional[LLMProvider], cfg, data_root: Path = DATA_ROOT, *, measured: bool):
    d1 = load_d1(data_root)
    ledger = InMemoryLedger()
    runs = [await run_contract(cid, canon, provider, ledger, cfg) for cid, (canon, _g) in d1.items()]
    report = summarize(runs, d1, measured=measured)
    report["cost"] = {"calls": ledger.calls, "in_tokens": ledger.in_tokens, "out_tokens": ledger.out_tokens,
                      "cost": round(ledger.cost, 6), "errors": ledger.errors}
    if runs and runs[0].output:
        o = runs[0].output
        report["version_pins"] = {"model_id": o.model_id, "prompt_version": o.prompt_version,
                                  "taxonomy_version": o.taxonomy_version, "schema_version": o.schema_version}
    return report


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", choices=["gemini", "local", "mock", "none"], default="none")
    ap.add_argument("--out", type=Path, default=Path("evaluation/runs/w4_d1"))
    ap.add_argument("--data-root", type=Path, default=DATA_ROOT)
    args = ap.parse_args(argv)

    from app.ai.factory import make_provider
    from app.core.config import load_settings, validate_for_env

    cfg = load_settings()
    if args.provider == "gemini":
        if not cfg.GEMINI_API_KEY or not cfg.GEMINI_MODEL_ID:
            print("Thiếu GEMINI_API_KEY / GEMINI_MODEL_ID — không chạy được phép đo thật.", file=sys.stderr)
            return 2
        cfg.DEV_LLM_PROVIDER = "gemini"
        provider, measured = make_provider(cfg), True
    elif args.provider == "local":
        cfg.DEV_LLM_PROVIDER = "local"
        validate_for_env(cfg)
        provider, measured = make_provider(cfg), True
    elif args.provider == "mock":
        cfg.GEMINI_MODEL_ID = cfg.GEMINI_MODEL_ID or "smoke-model"
        provider, measured = OtherProvider(), False
    else:
        provider, measured = None, False

    report = asyncio.run(run_all(provider, cfg, args.data_root, measured=measured))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"mode={report['mode']} → {args.out / 'report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
