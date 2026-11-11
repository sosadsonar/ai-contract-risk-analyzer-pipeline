"""Đo PII masking theo BRD §7.3 (C-09 b, MS-2): recall theo nhóm + tỷ lệ giữ nguyên trường cần giữ.

Chạy từ gốc repo:  python ai_pipeline/eval/eval_pii.py [--d1 DIR] [--out FILE.md]

Đo trên hai nguồn, khai báo rõ nguồn gold (BRD §8.1):
  * `tests/fixtures/privacy/case_*.json`: văn bản TỔNG HỢP do N3 viết, gold span do người đánh dấu.
    Gold D1/T1 (restricted) đo bằng ai_pipeline/eval/eval_pii_gold.py, không nằm trong file này.
  * D1 (`ai_pipeline/data/data/processed/raw_text/HDLD*.txt`): 6 mẫu đã de-identify (biểu mẫu trống),
    KHÔNG có PII thật nên không đo được recall; chỉ kiểm detector không che nhầm (số span, số ký tự
    đổi) và quét lỏng (số 9-13 chữ số, email) để chắc D1 không còn PII rơi ngoài detector.

Định nghĩa:
  * Gold span "được che" khi các span dự đoán (mọi loại) phủ 100% ký tự của nó. Che thiếu một phần
    vẫn lộ dữ liệu nên không tính. `type_ok` đếm riêng số span đúng cả loại (ảnh hưởng placeholder
    `<PHONE>` vs `<ORG>`, không ảnh hưởng rò rỉ).
  * Trường cần giữ "được giữ" khi KHÔNG có span dự đoán nào chạm vào nó.
  * `known_misses` trong fixture (giới hạn đã biết) vẫn tính là sót; chúng chỉ được loại khỏi test
    hồi quy (tests/unit/test_pii_fixtures_gold.py), không loại khỏi số đo.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.privacy.masker import PII_MASKING_VERSION, mask  # noqa: E402
from app.privacy.pii_types import PiiType  # noqa: E402

FIXTURE_DIR = ROOT / "tests" / "fixtures" / "privacy"
D1_RAW_TEXT = ROOT / "ai_pipeline" / "data" / "data" / "processed" / "raw_text"

# BRD §7.3
GROUPS: dict[str, tuple[frozenset[PiiType], float]] = {
    "A (CCCD/hộ chiếu, SĐT, email, TK ngân hàng, MST)": (
        frozenset(
            {
                PiiType.NATIONAL_ID_OR_PASSPORT,
                PiiType.PHONE,
                PiiType.EMAIL,
                PiiType.BANK_ACCOUNT,
                PiiType.TAX_ID,
            }
        ),
        0.99,
    ),
    "B (họ tên, ngày sinh, địa chỉ, pháp nhân, ngày/nơi cấp, chữ ký)": (
        frozenset(
            {
                PiiType.PERSON_NAME,
                PiiType.DATE_OF_BIRTH,
                PiiType.RESIDENTIAL_ADDRESS,
                PiiType.LEGAL_ENTITY,
                PiiType.ID_ISSUE,
                PiiType.BUSINESS_ADDRESS,
                PiiType.SIGNATURE,
            }
        ),
        0.90,
    ),
}
PRESERVE_THRESHOLD = 0.95


def load_fixtures(directory: Path = FIXTURE_DIR) -> list[dict]:
    paths = sorted(directory.glob("case_*.json"), key=lambda p: p.name)
    if not paths:
        raise FileNotFoundError(f"không có fixture trong {directory}")
    return [json.loads(p.read_text(encoding="utf-8")) for p in paths]


def _coverage(start: int, end: int, spans: list[tuple[int, int]]) -> float:
    covered = sum(max(0, min(end, e) - max(start, s)) for s, e in spans)
    return covered / (end - start) if end > start else 1.0


def _touches(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(s < end and start < e for s, e in spans)


def evaluate_fixtures(cases: list[dict]) -> dict:
    """Trả số đo thô; không ghi file."""
    by_type: dict[str, dict[str, int]] = defaultdict(lambda: {"gold": 0, "masked": 0, "type_ok": 0})
    misses: list[dict] = []
    preserve_total = preserve_kept = 0
    preserve_hit: list[dict] = []
    false_positive: list[dict] = []

    for case in cases:
        text = case["canonical_text"]
        result = mask(text)
        pred = [(s.start, s.end) for s in result.pii_spans]
        for gold in case["pii_spans"]:
            row = by_type[gold["type"]]
            row["gold"] += 1
            if _coverage(gold["start"], gold["end"], pred) >= 1.0:
                row["masked"] += 1
                if any(
                    s.type.value == gold["type"] and s.start <= gold["start"] and gold["end"] <= s.end
                    for s in result.pii_spans
                ):
                    row["type_ok"] += 1
            else:
                misses.append({"case": case["case_id"], **gold})
        for keep in case["preserve_spans"]:
            preserve_total += 1
            if _touches(keep["start"], keep["end"], pred):
                preserve_hit.append({"case": case["case_id"], **keep})
            else:
                preserve_kept += 1
        gold_ranges = [(g["start"], g["end"]) for g in case["pii_spans"]]
        for s in result.pii_spans:
            if not _touches(s.start, s.end, gold_ranges):
                false_positive.append(
                    {"case": case["case_id"], "type": s.type.value, "text": text[s.start : s.end]}
                )

    groups = {}
    for name, (types, threshold) in GROUPS.items():
        gold = sum(by_type[t.value]["gold"] for t in types)
        masked = sum(by_type[t.value]["masked"] for t in types)
        groups[name] = {
            "gold": gold,
            "masked": masked,
            "recall": masked / gold if gold else None,
            "threshold": threshold,
        }
    return {
        "masking_version": PII_MASKING_VERSION,
        "cases": len(cases),
        "by_type": dict(by_type),
        "groups": groups,
        "preserve": {
            "total": preserve_total,
            "kept": preserve_kept,
            "rate": preserve_kept / preserve_total if preserve_total else None,
            "threshold": PRESERVE_THRESHOLD,
            "damaged": preserve_hit,
        },
        "misses": misses,
        "false_positive": false_positive,
    }


_LOOSE = {
    "chuỗi 9-13 chữ số": re.compile(r"(?<!\d)\d{9,13}(?!\d)"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "SĐT dạng lỏng": re.compile(r"(?<!\d)(?:\+?84|0)[\d .-]{8,12}\d"),
}


def scan_d1(directory: Path = D1_RAW_TEXT) -> list[dict]:
    rows = []
    for path in sorted(directory.glob("HDLD*.txt")):
        text = unicodedata.normalize("NFC", path.read_text(encoding="utf-8"))
        result = mask(text)
        changed = sum(1 for a, b in zip(text, result.masked_text) if a != b)
        rows.append(
            {
                "file": path.name,
                "code_points": len(text),
                "spans": len(result.pii_spans),
                "chars_changed": changed,
                "loose": {k: len(p.findall(text)) for k, p in _LOOSE.items()},
            }
        )
    return rows


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def render_markdown(fx: dict, d1: list[dict] | None) -> str:
    out = [
        "# Số đo PII đầu tiên (C-09 b, MS-2)",
        "",
        f"Phiên bản masking: `{fx['masking_version']}`. Ngưỡng: BRD §7.3 (mục tiêu demo, không phải cam kết).",
        "Sinh bởi `python ai_pipeline/eval/eval_pii.py`; số liệu đổi khi detector/fixture đổi.",
        "",
        "## 1. Nguồn gold và cỡ mẫu",
        "",
        f"- Fixture tổng hợp `tests/fixtures/privacy/case_*.json`: {fx['cases']} ca, gold span do N3 đánh dấu tay "
        "(không phải hợp đồng thật, không phải gold của N2). Cỡ mẫu nhỏ: một span sót làm recall nhóm đổi "
        "vài điểm phần trăm, nên các con số dưới đây là **tín hiệu hồi quy, chưa phải số nghiệm thu**.",
        "- D1: 6 mẫu đã de-identify (biểu mẫu trống), **không có PII thật** nên không đo được recall trên D1. "
        "Gold privacy D1 và T1 đo bằng ai_pipeline/eval/eval_pii_gold.py (N2 chạy và điền số, cần restricted/).",
        "",
        "## 2. Recall khi che (gold span phải được phủ 100%)",
        "",
        "| Nhóm | Gold | Đã che | Recall | Ngưỡng | Kết quả |",
        "| :--- | ---: | ---: | ---: | ---: | :--- |",
    ]
    for name, g in fx["groups"].items():
        ok = g["recall"] is not None and g["recall"] >= g["threshold"]
        out.append(
            f"| {name} | {g['gold']} | {g['masked']} | {_pct(g['recall'])} | ≥ {g['threshold'] * 100:.0f}% | "
            f"{'ĐẠT' if ok else 'CHƯA ĐẠT'} |"
        )
    out += ["", "Theo loại (đúng loại = span dự đoán cùng loại phủ cả gold span):", "",
            "| Loại | Gold | Đã che | Đúng loại |", "| :--- | ---: | ---: | ---: |"]
    for t, r in sorted(fx["by_type"].items()):
        out.append(f"| {t} | {r['gold']} | {r['masked']} | {r['type_ok']} |")

    p = fx["preserve"]
    ok = p["rate"] is not None and p["rate"] >= p["threshold"]
    out += [
        "",
        "## 3. Tỷ lệ giữ nguyên trường cần giữ",
        "",
        f"{p['kept']}/{p['total']} = **{_pct(p['rate'])}** (ngưỡng ≥ {p['threshold'] * 100:.0f}%): "
        f"{'ĐẠT' if ok else 'CHƯA ĐẠT'}. Trường bị che nhầm: {len(p['damaged'])}.",
    ]
    for d in p["damaged"]:
        out.append(f"- {d['case']}: `{d['text']}`")
    out.append(f"\nSpan dự đoán không chạm gold nào (che thừa): {len(fx['false_positive'])}.")
    for d in fx["false_positive"]:
        out.append(f"- {d['case']} {d['type']}: `{d['text']}`")

    out += ["", "## 4. Span sót (giới hạn đã biết, đưa vào quyết định OI-12)", ""]
    if fx["misses"]:
        for m in fx["misses"]:
            out.append(f"- {m['case']} {m['type']}: `{m['text']}`" + (f" ({m['reason']})" if "reason" in m else ""))
    else:
        out.append("Không có.")

    if d1 is not None:
        out += ["", "## 5. D1: kiểm tra che nhầm và quét lỏng", "",
                "| Tệp | Code point | Span | Ký tự bị đổi | Quét lỏng (9-13 số / email / SĐT) |",
                "| :--- | ---: | ---: | ---: | :--- |"]
        for r in d1:
            lv = list(r["loose"].values())
            out.append(f"| {r['file']} | {r['code_points']} | {r['spans']} | {r['chars_changed']} | "
                       f"{lv[0]} / {lv[1]} / {lv[2]} |")
        out.append("\n0 span và 0 kết quả quét lỏng nghĩa là D1 đã sạch PII và detector không che nhầm; "
                   "điều này **không** chứng minh recall.")
    out += ["", "## 6. Kết luận cho quyết định OI-12 (local NER)", "",
            "- Trên fixture tổng hợp, regex/heuristic đạt cả hai nhóm và tỷ lệ giữ nguyên, **nhưng** fixture do chính "
            "người viết detector đánh dấu và chỉ có 2 ca giới hạn cố ý (tên không anchor, địa chỉ không anchor). "
            "Con số này không đại diện cho hợp đồng thật.",
            "- Điểm yếu cấu trúc còn lại là nhóm B không có anchor: tên và địa chỉ đứng trong câu văn thường "
            "(vd. người liên hệ, nơi cư trú trong điều khoản). Regex không bắt được; chỉ NER hoặc gold thật mới đo được.",  # noqa: E501
            "- Đề xuất cho MS-2: **chưa chốt bỏ NER**. Điều kiện chốt: chạy lại script này trên gold privacy D1 "
            "(N2) hoặc 2-3 hợp đồng thật đã gán span (T1). Nếu nhóm B < 90% trên gold thật thì mở local NER (OI-12); "
            "nếu ≥ 90% thì giữ regex và ghi giới hạn vào thông báo người dùng (BRD §7.6).",
            "- Rủi ro rò rỉ lớn nhất không nằm ở số đo: placeholder cùng độ dài nên LLM thấy được độ dài tên; "
            "và tên pháp nhân bị che nhưng từ vai trò giữ nguyên (đúng thiết kế TDD §10.2)."]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--d1", type=Path, default=D1_RAW_TEXT, help="thư mục raw_text của D1")
    ap.add_argument("--out", type=Path, help="ghi báo cáo Markdown")
    args = ap.parse_args(argv)

    fx = evaluate_fixtures(load_fixtures())
    d1 = scan_d1(args.d1) if args.d1.exists() else None
    report = render_markdown(fx, d1)
    if args.out:
        args.out.write_text(report, encoding="utf-8", newline="\n")
    else:
        sys.stdout.buffer.write(report.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
