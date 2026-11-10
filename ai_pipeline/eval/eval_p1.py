"""Đo P1 (N3, X-18), hai lát tách bạch:
  realistic: clean, upper, nfd_input (gần định dạng hợp đồng thật)
  stress   : newline_in_value, digit_groups (biến đổi khó, không phải nghiệm thu)
Chỉ là chẩn đoán: không đặt ngưỡng pass/fail trong CI. Không dùng số P1 để chỉnh detector rồi báo lại
trên cùng seed. Tiền điều kiện: base D1 đã canonical không có span PII.

  python ai_pipeline/eval/eval_p1.py --dir build/p1_v1/17 [--out-md FILE] [--out-json FILE]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.privacy.masker import PII_MASKING_VERSION, mask  # noqa: E402

from ai_pipeline.eval.p1.build_p1 import D1_RAW, load_d1  # noqa: E402
from ai_pipeline.eval.p1.generator import REALISTIC, STRESS, _base_docs  # noqa: E402
from ai_pipeline.evaluation.metrics.privacy import HIGH_SENSITIVITY_TYPES, STANDARD_SENSITIVITY_TYPES  # noqa: E402

THRESH = {"high_sensitivity": 0.99, "standard_sensitivity": 0.90}
GROUP_KINDS = {"high_sensitivity": HIGH_SENSITIVITY_TYPES, "standard_sensitivity": STANDARD_SENSITIVITY_TYPES}


def _covered(start, end, spans):
    cursor = start
    for s, e in sorted(spans):
        if s > cursor:
            break
        cursor = max(cursor, e)
        if cursor >= end:
            return True
    return cursor >= end


def check_base(texts: dict[str, str]) -> None:
    for name, text in _base_docs(texts).items():
        if mask(text).pii_spans:
            raise SystemExit(f"base {name} đã có span PII; không đo được")


def _lane(mutation: str) -> str:
    if mutation in STRESS:
        return "stress"
    if mutation in REALISTIC:
        return "realistic"
    raise ValueError(f"biến đổi lạ: {mutation}")


def run(doc_dir: Path, base: dict[str, str]) -> dict:
    check_base(base)
    kinds = {lane: defaultdict(lambda: [0, 0]) for lane in ("realistic", "stress")}
    misses = {lane: [] for lane in ("realistic", "stress")}
    p_total = p_kept = 0
    for path in sorted(doc_dir.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        text = doc["canonical_text"]
        pred = [(s.start, s.end) for s in mask(text).pii_spans]
        lane = _lane(doc["mutation"])
        for g in doc["gold"]["pii_spans"]:
            ok = _covered(g["start_char"], g["end_char"], pred)
            kinds[lane][g["pii_type"]][0] += 1
            kinds[lane][g["pii_type"]][1] += int(ok)
            if not ok:
                misses[lane].append({"doc": doc["doc_id"], "kind": g["pii_type"],
                                     "mutation": doc["mutation"], "text": g["text"]})
        for p in doc["gold"]["preserve_spans"]:
            p_total += 1
            p_kept += int(not any(s < p["end_char"] and p["start_char"] < e for s, e in pred))
    out = {"masking_version": PII_MASKING_VERSION, "lanes": {}, "preserve": {
        "total": p_total, "kept": p_kept, "rate": (p_kept / p_total) if p_total else None}}
    for lane in ("realistic", "stress"):
        groups = {}
        for gname, members in GROUP_KINDS.items():
            gold = sum(v[0] for k, v in kinds[lane].items() if k in members)
            masked = sum(v[1] for k, v in kinds[lane].items() if k in members)
            groups[gname] = {"gold": gold, "masked": masked, "recall": (masked / gold) if gold else None,
                             "threshold": THRESH[gname]}
        out["lanes"][lane] = {
            "groups": groups,
            "by_kind": {k: {"gold": v[0], "masked": v[1], "recall": (v[1] / v[0]) if v[0] else None}
                        for k, v in sorted(kinds[lane].items())},
            "misses": misses[lane],
        }
    return out


def _pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


def _md(r: dict) -> str:
    out = [f"# P1 (chẩn đoán, không phải nghiệm thu). Masking `{r['masking_version']}`", ""]
    for lane in ("realistic", "stress"):
        d = r["lanes"][lane]
        out += [f"## Lát {lane}", "", "| Nhóm | Gold | Đã che | Recall | Ngưỡng |", "| :--- | ---: | ---: | ---: | ---: |"]
        for k, g in d["groups"].items():
            out.append(f"| {k} | {g['gold']} | {g['masked']} | {_pct(g['recall'])} | ≥ {g['threshold'] * 100:.0f}% |")
        out += ["", "| Loại | Gold | Đã che | Recall |", "| :--- | ---: | ---: | ---: |"]
        for k, v in d["by_kind"].items():
            out.append(f"| {k} | {v['gold']} | {v['masked']} | {_pct(v['recall'])} |")
        out += ["", f"Danh sách sót ({len(d['misses'])}), tối đa 30 dòng (dữ liệu giả):"]
        for m in d["misses"][:30]:
            out.append(f"- {m['doc']} {m['kind']} {m['mutation']}: `{m['text']}`")
        out.append("")
    p = r["preserve"]
    out += [f"Preserve: {p['kept']}/{p['total']} = {_pct(p['rate'])}.", ""]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--d1-dir", type=Path, default=D1_RAW)
    ap.add_argument("--out-md", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    a = ap.parse_args(argv)
    r = run(a.dir / "docs", load_d1(a.d1_dir))
    if a.out_json:
        a.out_json.write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    text = _md(r)
    if a.out_md:
        a.out_md.write_text(text, encoding="utf-8")
    elif not a.out_json:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
