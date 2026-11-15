"""Lint explanation của Risk LLM (TDD §15.3, C-15 a): advice detector, unsupported-reference, sanitizer.

* `detect_advice`: KHÔNG match từ "nên" đơn lẻ (từ nối hợp lệ: "nên dẫn đến", "vì vậy nên"...). Chỉ match
  cụm mang nghĩa khuyến nghị: "bạn nên", "NLĐ/NSDLĐ nên", "người lao động nên", "nên sửa/bổ sung/thương
  lượng/yêu cầu/...", "đề nghị sửa/bổ sung", "khuyến nghị", "khuyên".
* `detect_unsupported_reference`: explanation nhắc rõ "Điều N"/"Khoản K Điều N" hoặc tên văn bản pháp luật
  mà không tương ứng citation hợp lệ đã chọn ⇒ vi phạm. "điều khoản số N của hợp đồng" không phải dẫn
  chiếu luật (FR-13).
* `sanitize_explanation`: xóa đúng CÂU vi phạm (tách câu tất định), giữ phần trung tính còn lại; trả None
  nếu không còn rationale (caller ⇒ AI_OUTPUT_INVALID).

Hàm thuần, không log nội dung (INV-13): kết quả chỉ là cờ/mã, không trả lại đoạn văn bản vi phạm.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

LINT_VERSION = "risk_lint_v1"
MIN_EXPLANATION_CHARS = 10

_ADVICE = re.compile(
    r"\b(?:bạn|anh|chị|nlđ|nsdlđ|nsdld|nld|người\s+lao\s+động|người\s+sử\s+dụng\s+lao\s+động|"
    r"công\s+ty|doanh\s+nghiệp|hai\s+bên|các\s+bên)\s+(?:cần\s+|nên\s+|phải\s+)?nên\b"
    r"|\bnên\s+(?:sửa|sửa\s+đổi|bổ\s+sung|thương\s+lượng|đàm\s+phán|yêu\s+cầu|đề\s+nghị|cân\s+nhắc|"
    r"xem\s+xét\s+lại|xem\s+lại|từ\s+chối|không\s+ký|ký|làm\s+rõ|ghi\s+rõ|loại\s+bỏ|tham\s+khảo|liên\s+hệ|hỏi)\b"
    r"|\bđề\s+nghị\s+(?:sửa|bổ\s+sung|điều\s+chỉnh|thương\s+lượng|làm\s+rõ)\b"
    r"|\bkhuyến\s+nghị\b|\bkhuyên\b",
    re.IGNORECASE,
)

_LAW_REF = re.compile(
    r"(?:\bkhoản\s+(?P<item>\d{1,3})\s+(?:của\s+)?)?\bđiều\s+(?P<article>\d{1,3}[a-zđ]?)\b(?P<after>.{0,40})",
    re.IGNORECASE,
)
_CONTRACT_SELF = re.compile(r"^\s*(?:của\s+)?(?:hợp\s+đồng|hđ|hđlđ)\b", re.IGNORECASE)
_LAW_NAME = re.compile(
    r"\b(?:bộ\s+luật|luật|nghị\s+định|thông\s+tư|nghị\s+quyết|blld|bllđ|nđ-cp|tt-blđtbxh)\b", re.IGNORECASE
)
_CITATION_ARTICLE = re.compile(r":art(\d+[a-zđ]?)(?::cl(\d+))?", re.IGNORECASE)
_SENTENCE = re.compile(r"[^.!?;\n]+(?:[.!?;]+|$)")


def detect_advice(text: str) -> bool:
    return bool(_ADVICE.search(text or ""))


def _cited(citation_ids: Iterable[str]) -> tuple[set[str], set[tuple[str, str]]]:
    articles: set[str] = set()
    items: set[tuple[str, str]] = set()
    for cid in citation_ids:
        m = _CITATION_ARTICLE.search(cid)
        if m:
            articles.add(m.group(1).lower())
            if m.group(2):
                items.add((m.group(1).lower(), m.group(2)))
    return articles, items


def detect_unsupported_reference(text: str, citation_ids: Iterable[str]) -> bool:
    """True nếu explanation nhắc Điều/Khoản/tên văn bản luật không khớp citation hợp lệ đã chọn."""
    text = text or ""
    cites = list(citation_ids)
    articles, items = _cited(cites)
    for m in _LAW_REF.finditer(text):
        if _CONTRACT_SELF.match(m.group("after")):
            continue  # "Điều 5 của hợp đồng": dẫn chiếu nội bộ
        art = m.group("article").lower()
        if art not in articles:
            return True
        if m.group("item") and (art, m.group("item")) not in items and any(a == art for a, _ in items):
            return True
    return bool(_LAW_NAME.search(text)) and not cites


def _bad_sentence(sentence: str, citation_ids: list[str]) -> bool:
    return detect_advice(sentence) or detect_unsupported_reference(sentence, citation_ids)


def lint_explanation(text: str, citation_ids: Iterable[str]) -> list[str]:
    """Mã vi phạm (không chứa text): 'advice', 'unsupported_reference'."""
    cites = list(citation_ids)
    codes = []
    if detect_advice(text):
        codes.append("advice")
    if detect_unsupported_reference(text, cites):
        codes.append("unsupported_reference")
    return codes


def sanitize_explanation(text: str, citation_ids: Iterable[str]) -> Optional[str]:
    """Xóa câu vi phạm; None nếu phần còn lại không đủ làm rationale."""
    cites = list(citation_ids)
    kept = [s.strip() for s in _SENTENCE.findall(text or "") if s.strip() and not _bad_sentence(s, cites)]
    out = " ".join(kept).strip()
    return out if len(out) >= MIN_EXPLANATION_CHARS else None
