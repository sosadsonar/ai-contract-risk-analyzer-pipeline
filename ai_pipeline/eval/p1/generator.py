"""Bộ sinh P1 (N3, X-18): chèn PII GIẢ vào tài liệu D1 đã canonical, kèm gold offset (code point, NFC).

Ràng buộc:
- KHÔNG import app.privacy.* (kiểm bằng AST trong test). Dùng kho giả pools.py và canonicalizer của
  app.document (không phải detector), để đo không tự chứng minh chính nó.
- Mỗi mẫu là MỘT tài liệu với ĐÚNG MỘT lần chèn (điều chỉnh so với plan: 4 tài liệu gốc không đủ cho
  cỡ mẫu nếu giới hạn 6 lần chèn/tài liệu).
- Vị trí chèn: ranh giới dòng trong 30% đầu văn bản; SIGNATURE chèn ở cuối (khối ký nằm cuối hợp đồng).
- Biến đổi chỉ được gắn nhãn khi áp dụng thật (mutation_applied). Mẫu không đủ điều kiện nhận biến đổi
  thì nhận "clean". Xuống dòng giữa số tách gold thành hai span, ký tự xuống dòng không thuộc span nào.
- Không sinh mẫu "mã số không anchor" làm chuỗi phủ định: PHONE đã bắt dãy 10 chữ số đó (đã ghi nhận).
- Gold: pii_spans[{pii_type, start_char, end_char, text}], preserve_spans[{start_char, end_char, text}].
"""

from __future__ import annotations

import hashlib
import json
import random
import unicodedata
from dataclasses import dataclass

from app.document.canonicalizer import canonicalize

from ai_pipeline.eval.p1 import pools as P

HIGH_KINDS = ("NATIONAL_ID_OR_PASSPORT", "PHONE", "EMAIL", "BANK_ACCOUNT", "TAX_ID")
STANDARD_KINDS = ("PERSON_NAME", "DATE_OF_BIRTH", "RESIDENTIAL_ADDRESS", "BUSINESS_ADDRESS",
                  "LEGAL_ENTITY", "ID_ISSUE", "SIGNATURE")
PRESERVE = "PRESERVE"
MUTATIONS = ("clean", "upper", "nfd_input", "newline_in_value", "digit_groups")
REALISTIC = ("clean", "upper", "nfd_input")
STRESS = ("newline_in_value", "digit_groups")

# Khung nhãn (>= 4 mỗi kiểu). {v} = giá trị.
FRAMES = {
    "TAX_ID": ("Mã số thuế: {v}", "MST: {v}", "Mã số thuế : {v}", "Mã số thuế: {v}"),
    "NATIONAL_ID_OR_PASSPORT": ("CCCD số: {v}", "Số CMND: {v}", "Hộ chiếu số: {v}", "CMND số: {v}"),
    "PHONE": ("SĐT: {v}", "Điện thoại: {v}", "ĐT: {v}", "Liên hệ: {v}"),
    "EMAIL": ("Email: {v}", "Thư điện tử: {v}", "E-mail: {v}", "EMAIL: {v}"),
    "BANK_ACCOUNT": ("STK: {v}", "Số tài khoản: {v}", "Số TK: {v}", "TK ngân hàng: {v}"),
    "PERSON_NAME": ("Họ và tên: {v}", "Họ tên: {v}", "HỌ VÀ TÊN: {v}", "Ông {v}"),
    "DATE_OF_BIRTH": ("Ngày sinh: {v}", "Sinh ngày {v}", "Ngày tháng năm sinh: {v}", "NGÀY SINH: {v}"),
    "RESIDENTIAL_ADDRESS": ("Địa chỉ thường trú: {v}", "Nơi thường trú: {v}", "Địa chỉ cư trú: {v}",
                            "Hộ khẩu thường trú: {v}"),
    "BUSINESS_ADDRESS": ("Địa chỉ trụ sở chính: {v}", "Địa chỉ trụ sở: {v}", "Địa chỉ công ty: {v}",
                         "ĐỊA CHỈ TRỤ SỞ: {v}"),
    "LEGAL_ENTITY": ("Công ty TNHH {v}", "Công ty Cổ phần {v}", "Công ty TNHH MTV {v}", "CÔNG TY TNHH {v}"),
    "ID_ISSUE_DATE": ("Cấp ngày: {v}", "Ngày cấp: {v}", "cấp ngày {v}", "Ngày cấp : {v}"),
    "ID_ISSUE_PLACE": ("Nơi cấp: {v}", "NƠI CẤP: {v}", "Nơi cấp : {v}", "Cấp tại: {v}"),
    "SIGNATURE": ("(Ký, ghi rõ họ tên)\n{v}", "(Ký tên)\n{v}", "Ký tên: {v}", "(Ký và ghi rõ họ tên)\n{v}"),
    PRESERVE: ("Ngày ký: {v}", "Số: {v}", "Lương: {v}", "Chức vụ: {v}"),
}
PRESERVE_VALUES = ("12.000.000 đồng/tháng", "01/2026/HĐLĐ", "02/12/2026", "Giám đốc", "Kế toán trưởng",
                   "Thành phố Hồ Chí Minh", "08 giờ/ngày", "12 tháng", "Phó Giám đốc")


@dataclass(frozen=True)
class Sample:
    kind: str
    doc_id: str
    mutation: str  # biến đổi thật đã áp dụng ("clean" nếu không áp dụng)
    canonical_text: str
    pii_spans: tuple
    preserve_spans: tuple
    raw_nfd: str | None  # chỉ có khi mutation = nfd_input


def _digits(rng, n):
    return "".join(str(rng.randrange(10)) for _ in range(n))


def _mobile(rng):
    return rng.choice(["03", "05", "07", "08", "09"]) + _digits(rng, 8)


def _value(kind: str, rng: random.Random):
    """Trả (khung, giá trị). Khung là khóa của FRAMES."""
    if kind == "TAX_ID":
        if rng.random() < 0.5:
            return "TAX_ID", _digits(rng, 10)
        return "TAX_ID", f"{_digits(rng, 10)}-{_digits(rng, 3)}"
    if kind == "NATIONAL_ID_OR_PASSPORT":
        sub = rng.random()
        if sub < 0.6:
            return "NATIONAL_ID_OR_PASSPORT", rng.choice(P.CCCD_PROVINCE_CODES) + str(rng.randrange(4)) + _digits(rng, 8)
        if sub < 0.8:
            return "NATIONAL_ID_OR_PASSPORT", str(rng.randrange(1, 10)) + _digits(rng, 8)
        return "NATIONAL_ID_OR_PASSPORT", rng.choice("BCDEGHKLMNPRSTUVXYZ") + _digits(rng, 7)
    if kind == "PHONE":
        if rng.random() < 0.8:
            m = _mobile(rng)
            v = [m, f"{m[:4]} {m[4:7]} {m[7:]}", f"{m[:4]}.{m[4:7]}.{m[7:]}", f"+84 {m[1:4]} {m[4:7]} {m[7:]}"][rng.randrange(4)]
        else:
            v = f"024 {_digits(rng, 4)} {_digits(rng, 4)}"
        return "PHONE", v
    if kind == "EMAIL":
        user = rng.choice(P.GIVEN).lower().replace("đ", "d").replace(" ", "") + str(rng.randrange(100))
        user = "".join(ch for ch in unicodedata.normalize("NFD", user) if unicodedata.category(ch) != "Mn")
        return "EMAIL", f"{user}@{rng.choice(P.EMAIL_DOMAINS)}"
    if kind == "BANK_ACCOUNT":
        n = rng.randrange(8, 17)
        raw = _digits(rng, n)
        return "BANK_ACCOUNT", raw if rng.random() < 0.5 else " ".join(raw[i : i + 4] for i in range(0, n, 4))
    if kind == "PERSON_NAME":
        return "PERSON_NAME", _name(rng)
    if kind == "DATE_OF_BIRTH":
        return "DATE_OF_BIRTH", _date(rng, 1950, 2005)
    if kind in ("RESIDENTIAL_ADDRESS", "BUSINESS_ADDRESS"):
        return kind, _address(rng)
    if kind == "LEGAL_ENTITY":
        return "LEGAL_ENTITY", rng.choice(P.COMPANY_NAMES) + (" Việt Nam" if rng.random() < 0.4 else "")
    if kind == "ID_ISSUE":
        if rng.random() < 0.5:
            return "ID_ISSUE_DATE", _date(rng, 2010, 2026)
        return "ID_ISSUE_PLACE", rng.choice(P.ID_ISSUE_PLACES)
    if kind == "SIGNATURE":
        return "SIGNATURE", _name(rng)
    raise ValueError(kind)


def _name(rng):
    parts = [rng.choice(P.SURNAMES)]
    if rng.random() < 0.6:
        parts.append(rng.choice(P.MIDDLE))
    parts.append(rng.choice(P.GIVEN))
    return " ".join(parts)


def _date(rng, y0, y1):
    d, m, y = rng.randrange(1, 29), rng.randrange(1, 13), rng.randrange(y0, y1 + 1)
    if rng.random() < 0.7:
        return f"{d:02d}/{m:02d}/{y}"
    return f"{d:02d} tháng {m:02d} năm {y}"


def _address(rng):
    num = rng.randrange(1, 300)
    return f"{num} {rng.choice(P.STREETS)}, {rng.choice(P.WARDS)}, {rng.choice(P.DISTRICTS)}, {rng.choice(P.PROVINCES)}"


def _choose_mutation(kind: str, value: str, rng: random.Random):
    """Trả (biến đổi, giá trị sau biến đổi, vị trí cắt xuống dòng hoặc None). Chỉ chọn biến đổi áp dụng được."""
    options = ["clean", "upper", "nfd_input"]
    cuts = []
    if kind in HIGH_KINDS and value[:1].isdigit():
        cuts = [i for i in range(3, len(value) - 2) if value[i - 1].isdigit() and value[i].isdigit()]
        if cuts:
            options.append("newline_in_value")
    if value.isdigit() and len(value) >= 9:
        options.append("digit_groups")
    m = options[rng.randrange(len(options))]
    if m == "newline_in_value":
        cut = rng.choice(cuts)
        return m, value[:cut] + "\n" + value[cut:], cut
    if m == "digit_groups":
        return m, " ".join(value[i : i + 3] for i in range(0, len(value), 3)), None
    return m, value, None


def _base_docs(texts: dict[str, str]) -> dict[str, str]:
    return {k: canonicalize([v]) for k, v in sorted(texts.items())}


def generate(texts: dict[str, str], seed: int, n_high: int, n_std: int, n_preserve: int):
    """Sinh mẫu theo thứ tự xác định: cùng seed và cùng đầu vào cho cùng nội dung."""
    base = _base_docs(texts)
    names = sorted(base)
    rng = random.Random(seed)
    plan = [(k, n_high) for k in HIGH_KINDS] + [(k, n_std) for k in STANDARD_KINDS] + [(PRESERVE, n_preserve)]
    samples: list[Sample] = []
    idx = 0
    for kind, count in plan:
        for _ in range(count):
            src = names[rng.randrange(len(names))]
            samples.append(_one(kind, src, base[src], rng, idx, seed))
            idx += 1
    return samples


def _one(kind, src, text, rng, idx, seed):
    lines = text.split("\n")
    if kind == PRESERVE:
        frame_key, value = PRESERVE, rng.choice(PRESERVE_VALUES)
        mutation, cut = "clean", None
    else:
        frame_key, value = _value(kind, rng)
        mutation, value, cut = _choose_mutation(kind, value, rng)
    if kind == "SIGNATURE":
        k = len(lines)  # cuối văn bản
    else:
        k = rng.randrange(1, max(2, int(len(lines) * 0.30)))  # ranh giới dòng trong 30% đầu
    frame = FRAMES[frame_key][rng.randrange(len(FRAMES[frame_key]))]
    prefix, _, suffix = frame.partition("{v}")
    if mutation == "upper":
        prefix = prefix.upper()
    line_text = prefix + value + suffix
    line_start = len("\n".join(lines[:k])) + (1 if k > 0 else 0)
    text_out = "\n".join(lines[:k] + [line_text] + lines[k:])
    value_start = line_start + len(prefix)
    value_end = value_start + len(value)
    if canonicalize([text_out]) != text_out:  # bất biến: offset tính trên văn bản đã canonical
        raise RuntimeError("bất biến canonical bị vi phạm")
    if text_out[value_start:value_end] != value:
        raise RuntimeError("offset chèn không khớp giá trị")
    raw = unicodedata.normalize("NFD", text_out) if mutation == "nfd_input" else None
    if raw is not None and (raw == text_out or canonicalize([raw]) != text_out):
        raise RuntimeError("nfd_input không áp dụng được hoặc không quay về bản NFC")
    if kind == PRESERVE:
        return Sample(kind, f"p1_{seed}_{idx:05d}", mutation, text_out, (),
                      ({"start_char": value_start, "end_char": value_end, "text": value},), raw)
    if cut is None:
        spans = [(value_start, value_end)]
    else:  # ký tự xuống dòng nằm ở value_start + cut, không thuộc span nào
        spans = [(value_start, value_start + cut), (value_start + cut + 1, value_end)]
    pii = tuple({"pii_type": kind, "start_char": s, "end_char": e, "text": text_out[s:e]} for s, e in spans)
    if any("\n" in row["text"] for row in pii):
        raise RuntimeError("gold chứa ký tự xuống dòng")
    return Sample(kind, f"p1_{seed}_{idx:05d}", mutation, text_out, pii, (), raw)


def sample_to_doc(s: Sample) -> dict:
    doc = {
        "doc_id": s.doc_id,
        "kind": s.kind,
        "mutation": s.mutation,
        "mutation_applied": s.mutation != "clean",
        "canonical_text": s.canonical_text,
        "gold": {"pii_spans": list(s.pii_spans), "preserve_spans": list(s.preserve_spans)},
    }
    if s.raw_nfd is not None:
        doc["raw_text_nfd"] = s.raw_nfd
    return doc


def doc_sha256(doc: dict) -> str:
    return hashlib.sha256(json.dumps(doc, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
