"""Đo privacy (BRD §7.3) trên gold D1 và T1 bằng detector và evaluate_privacy của repo (G1, N3).

Chạy từ gốc repo:
  python ai_pipeline/eval/eval_pii_gold.py --data-root <repo dữ liệu> [--sets d1,t1] [--t1-docs HDLD005,...]
      [--d1-gold-dir DIR] [--out-json FILE] [--out-md FILE] [--restricted-out FILE]

Ngầm định (đã chốt):
  - Gold D1 gắn với văn bản CANONICAL (masking chạy trên canonical). Văn bản D1 được canonicalize trước khi đo.
    Nếu gold có source_sha256 thì phải khớp sha256 của văn bản canonical (utf-8), không thì mã thoát 2.
  - Gold T1 gắn với văn bản đọc theo read_text (dịch newline như gate). Phải ở dạng NFC.

Nguồn (khớp scripts/evaluate_t1_t2_equivalent_gate.py của N2):
  T1 văn bản: <root>/data/intake/restricted/T1_segmentation_candidate_v01/HDLDxxx.txt
  T1 gold   : <root>/data/intake/restricted/T1_privacy_gold_v01/HDLDxxx.gold_privacy.json
  T1 danh sách mặc định: HDLD005..HDLD013 (cố định, không glob)
  D1 văn bản: <root>/data/processed/raw_text/HDLD00{1..4}.txt
  D1 gold   : chưa xác nhận đường dẫn; truyền bằng --d1-gold-dir (nếu thiếu thì dùng --sets t1).

Đầu ra công khai (--out-json, --out-md): đếm, tỉ lệ, khoảng tin cậy, trạng thái, phiên bản masker,
sha256 của gold, hash_basis. Không có văn bản và không có offset.
Đầu ra hạn chế (--restricted-out): offset span gold bị sót. Không được nằm trong reports/.

Mã thoát: 0 chạy xong (kể cả có FAIL); 2 thiếu dữ liệu, gold sai schema/status/sha, hoặc đường dẫn không hợp lệ.
Số liệu gold thật do N2 chạy và điền. Agent không chạy trên dữ liệu thật.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.document.canonicalizer import canonicalize  # noqa: E402
from app.privacy.masker import PII_MASKING_VERSION, mask  # noqa: E402
from ai_pipeline.eval.eval_pii import PRESERVE_THRESHOLD  # noqa: E402
from ai_pipeline.evaluation.metrics.bootstrap import bootstrap_cluster_interval  # noqa: E402
from ai_pipeline.evaluation.metrics.privacy import (  # noqa: E402
    HIGH_SENSITIVITY_TYPES,
    PreserveSpan,
    PrivacySpan,
    evaluate_privacy,
)

EXIT_OK, EXIT_DATA = 0, 2
D1_DOCS = ("HDLD001", "HDLD002", "HDLD003", "HDLD004")
T1_DOCS = tuple(f"HDLD{i:03}" for i in range(5, 14))
GOLD_STATUS = "GOLD_ADJUDICATED"
GROUP_KEYS = ("high_sensitivity", "standard_sensitivity")
BOOT_ITERATIONS, BOOT_SEED = 1000, 0


class DataError(Exception):
    """Thiếu hoặc sai dữ liệu. Thông báo chỉ chứa tên file hoặc mã tài liệu, không chứa nội dung."""


def _read_text(path: Path, canonical: bool) -> str:
    text = path.read_text(encoding="utf-8")  # như gate: dịch newline, offset theo văn bản đã đọc
    if canonical:
        return canonicalize([text])
    if unicodedata.normalize("NFC", text) != text:
        raise DataError(f"{path.name}: không ở dạng NFC")
    return text


def _read_gold(path: Path, text: str, canonical: bool) -> tuple[dict, str, str]:
    if not path.exists():
        raise DataError(f"thiếu gold: {path.name}")
    gold_raw = path.read_bytes()
    gold = json.loads(gold_raw.decode("utf-8"))
    status = gold.get("status")
    if status is not None and status != GOLD_STATUS:
        raise DataError(f"{path.name}: status={status!r}, cần {GOLD_STATUS}")
    basis = "canonical" if canonical else "text"
    if "source_sha256" in gold:
        if gold["source_sha256"] != hashlib.sha256(text.encode("utf-8")).hexdigest():
            raise DataError(f"{path.name}: source_sha256 không khớp văn bản ({basis})")
    else:
        basis = "absent"
    return gold, hashlib.sha256(gold_raw).hexdigest(), basis


def _coverage(start: int, end: int, spans: list[tuple[int, int]]) -> float:
    covered = sum(max(0, min(end, e) - max(start, s)) for s, e in spans)
    return covered / (end - start) if end > start else 1.0


def _evaluate_doc(doc_id: str, text: str, gold: dict):
    result = mask(text)
    predicted = [PrivacySpan(s.type.value, s.start, s.end) for s in result.pii_spans]
    gold_spans = [
        PrivacySpan(row["pii_type"], row["start_char"], row["end_char"]) for row in gold.get("pii_spans", [])
    ]
    preserve = [PreserveSpan(row["start_char"], row["end_char"]) for row in gold.get("preserve_spans", [])]
    try:
        metric = evaluate_privacy(
            text, result.masked_text, predicted_spans=predicted, gold_pii_spans=gold_spans, preserve_spans=preserve
        )
    except ValueError as exc:  # loại PII lạ, span ngoài biên, v.v.
        raise DataError(f"{doc_id}: gold không hợp lệ ({exc})") from exc
    pred_ranges = [(s.start, s.end) for s in result.pii_spans]
    missed, flags = [], []
    for g in gold_spans:
        ok = _coverage(g.start, g.end, pred_ranges) >= 1.0
        flags.append((_group_of(g.kind), int(ok)))
        if not ok:
            missed.append({"doc_id": doc_id, "pii_type": g.kind, "start_char": g.start, "end_char": g.end})
    return metric, missed, flags


def _group_of(kind: str) -> str:
    return "high_sensitivity" if kind in HIGH_SENSITIVITY_TYPES else "standard_sensitivity"


def _aggregate(rows, clusters) -> dict:
    groups = {}
    for key in GROUP_KEYS:
        gold = sum(getattr(r, key).gold_count for r in rows)
        masked = sum(getattr(r, key).masked_count for r in rows)
        threshold = getattr(rows[0], key).threshold
        if gold == 0:
            status, recall = "NOT_ESTIMABLE", None
        else:
            recall = masked / gold
            status = "PASS" if recall >= threshold else "FAIL"
        ci = bootstrap_cluster_interval(
            clusters[key], lambda rs: (sum(rs) / len(rs)) if rs else None,
            iterations=BOOT_ITERATIONS, random_seed=BOOT_SEED,
        )
        groups[key] = {
            "gold": gold,
            "masked": masked,
            "recall": recall,
            "threshold": threshold,
            "status": status,
            "ci95": {"low": ci.low, "high": ci.high, "clusters": ci.cluster_count,
                     "valid_replicates": ci.valid_replicate_count, "iterations": ci.iterations,
                     "seed": BOOT_SEED},
        }
    p_total = sum(r.preserve_count for r in rows)
    p_kept = sum(r.preserved_count for r in rows)
    p_rate = p_kept / p_total if p_total else None
    return {
        "groups": groups,
        "preserve": {
            "total": p_total,
            "kept": p_kept,
            "rate": p_rate,
            "threshold": PRESERVE_THRESHOLD,
            "status": "NOT_ESTIMABLE" if p_rate is None else ("PASS" if p_rate >= PRESERVE_THRESHOLD else "FAIL"),
        },
    }


def _run_set(name: str, docs, text_dir: Path, gold_dir: Path, canonical: bool, missed_out: list) -> dict:
    if not docs:
        raise DataError(f"{name}: không có tài liệu")
    rows, shas, bases = [], {}, {}
    clusters = {key: {} for key in GROUP_KEYS}
    for doc in docs:
        path = text_dir / f"{doc}.txt"
        if not path.exists():
            raise DataError(f"{name}: thiếu văn bản {doc}")
        text = _read_text(path, canonical)
        gold, sha, basis = _read_gold(gold_dir / f"{doc}.gold_privacy.json", text, canonical)
        shas[doc], bases[doc] = sha, basis
        metric, missed, flags = _evaluate_doc(doc, text, gold)
        rows.append(metric)
        missed_out.extend(missed)
        for key in GROUP_KEYS:
            clusters[key][doc] = [ok for g, ok in flags if g == key]
    return {"docs": list(docs), "gold_sha256": shas, "hash_basis": bases, **_aggregate(rows, clusters)}


def _pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def _render_md(report: dict) -> str:
    lines = [
        "# Đo privacy trên gold D1/T1 (eval_pii_gold)",
        "",
        f"Phiên bản masking: `{report['masking_version']}`. Ngưỡng BRD §7.3: nhóm cao 99%, nhóm chuẩn 90%, "
        f"preserve {PRESERVE_THRESHOLD * 100:.0f}%.",
        "Ngầm định: gold D1 gắn văn bản canonical; gold T1 gắn văn bản đọc theo read_text.",
        "Báo cáo công khai: không có văn bản và offset. Khoảng tin cậy: bootstrap theo tài liệu, 1000 lần, seed 0.",
        "",
    ]
    for name, s in report["sets"].items():
        lines += [f"## {name} ({len(s['docs'])} tài liệu, hash_basis: {sorted(set(s['hash_basis'].values()))})", "",
                  "| Nhóm | Gold | Đã che | Recall | CI 95% | Ngưỡng | Kết quả |",
                  "| :--- | ---: | ---: | ---: | :--- | ---: | :--- |"]
        for key, g in s["groups"].items():
            ci = g["ci95"]
            ci_txt = "n/a" if ci["low"] is None else f"[{ci['low'] * 100:.1f}%, {ci['high'] * 100:.1f}%]"
            lines.append(f"| {key} | {g['gold']} | {g['masked']} | {_pct(g['recall'])} | {ci_txt} | "
                         f"≥ {g['threshold'] * 100:.0f}% | {g['status']} |")
        p = s["preserve"]
        lines += ["", f"Preserve: {p['kept']}/{p['total']} = {_pct(p['rate'])} ({p['status']}).", ""]
    return "\n".join(lines) + "\n"


def _within_reports(path: Path) -> bool:
    try:
        path.resolve().relative_to((ROOT / "reports").resolve())
        return True
    except ValueError:
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", type=Path, required=True, help="gốc repo dữ liệu (chứa data/intake/restricted)")
    ap.add_argument("--sets", default="d1,t1", help="d1,t1 (mặc định cả hai)")
    ap.add_argument("--t1-docs", default=None, help="danh sách T1 ngăn cách bằng dấu phẩy (mặc định HDLD005..013)")
    ap.add_argument("--d1-text-dir", type=Path, default=None)
    ap.add_argument("--d1-gold-dir", type=Path, default=None, help="thư mục gold D1 (chưa xác nhận đường dẫn)")
    ap.add_argument("--t1-text-dir", type=Path, default=None)
    ap.add_argument("--t1-gold-dir", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--out-md", type=Path, default=None)
    ap.add_argument("--restricted-out", type=Path, default=None, help="offset span sót; không nằm trong reports/")
    args = ap.parse_args(argv)

    sets = {s.strip().lower() for s in args.sets.split(",") if s.strip()}
    if not sets or not sets <= {"d1", "t1"}:
        print("ERROR: --sets chỉ nhận d1 và/hoặc t1", file=sys.stderr)
        return EXIT_DATA
    if args.restricted_out and _within_reports(args.restricted_out):
        print("ERROR: --restricted-out không được nằm trong reports/", file=sys.stderr)
        return EXIT_DATA
    t1_docs = tuple(d.strip() for d in args.t1_docs.split(",")) if args.t1_docs else T1_DOCS

    restricted = args.data_root / "data" / "intake" / "restricted"
    t1_text = args.t1_text_dir or restricted / "T1_segmentation_candidate_v01"
    t1_gold = args.t1_gold_dir or restricted / "T1_privacy_gold_v01"
    d1_text = args.d1_text_dir or args.data_root / "data" / "processed" / "raw_text"
    missed: list[dict] = []
    report: dict = {"schema": "pii_gold_eval_v2", "masking_version": PII_MASKING_VERSION, "sets": {}}
    try:
        if "d1" in sets:
            if args.d1_gold_dir is None:
                raise DataError("D1: thiếu --d1-gold-dir (đường dẫn gold D1 chưa xác nhận)")
            report["sets"]["D1"] = _run_set("D1", D1_DOCS, d1_text, args.d1_gold_dir, True, missed)
        if "t1" in sets:
            report["sets"]["T1"] = _run_set("T1", t1_docs, t1_text, t1_gold, False, missed)
    except DataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_DATA

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(_render_md(report), encoding="utf-8")
    if args.restricted_out:
        args.restricted_out.parent.mkdir(parents=True, exist_ok=True)
        args.restricted_out.write_text(json.dumps(missed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not (args.out_json or args.out_md):
        sys.stdout.write(_render_md(report))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
