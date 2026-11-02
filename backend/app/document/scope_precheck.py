"""FR-06 local scope decision on a copy of canonical text (TDD §9)."""

import re
import unicodedata
from dataclasses import dataclass

SCOPE_RULE_VERSION = "scope_rules_v1"  # Provisional until OI-03 is measured on D1.


@dataclass(frozen=True)
class ScopeDecision:
    accept: bool
    score: int
    signals: list[str]


_TITLE = re.compile(r"\bhợp\s+đồng\s+(?:lao\s+động|thử\s+việc)\b")
_EMPLOYEE = re.compile(r"\bngười\s+lao\s+động\b")
_EMPLOYER = re.compile(r"\b(?:người|bên)\s+sử\s+dụng\s+lao\s+động\b")
_CONTENT = {
    "pay": re.compile(r"\b(?:tiền\s+)?lương\b|\b(?:phụ\s+cấp|thù\s+lao)\b"),
    "hours": re.compile(r"\b(?:thời\s+giờ|giờ|ca)\s+làm\s+việc\b|\bgiờ\s+nghỉ\b"),
    "job": re.compile(r"\b(?:công\s+việc|chức\s+danh|vị\s+trí\s+công\s+việc)\b"),
    "term": re.compile(r"\bthời\s+hạn\b|\bthời\s+gian\s+(?:hợp\s+đồng|thử\s+việc|làm\s+việc)\b"),
}
_HEADING = re.compile(r"(?m)^\s*(?:điều|khoản)\s+\d+(?:[a-zđ])?(?=[\s.:)\-]|$)")
_RIGHTS = re.compile(r"(?m)^\s*(?:quyền\s+(?:và\s+)?nghĩa\s+vụ|quyền|nghĩa\s+vụ)\b")
_NEGATIVE = re.compile(r"\b(?:hóa\s+đơn|mua\s+bán|thuê\s+nhà|hợp\s+đồng\s+dịch\s+vụ|cung\s+cấp\s+dịch\s+vụ)\b")


def precheck(canonical_text: str, cfg) -> ScopeDecision:
    """Score employment signals without changing canonical text or consulting an LLM.

    The title window is sliced in original Unicode code points *before* casefolding;
    NFC/casefold are used only on temporary matching strings, never on offsets.
    """
    title = unicodedata.normalize("NFC", canonical_text[:cfg.SCOPE_TITLE_SCAN_CHARS]).casefold()
    text = unicodedata.normalize("NFC", canonical_text).casefold()
    signals: list[str] = []
    score = 0

    strong_title = bool(_TITLE.search(title))
    if strong_title:
        signals.append("strong_title")
        score += 3

    employee = bool(_EMPLOYEE.search(text))
    employer = bool(_EMPLOYER.search(text))
    if employee:
        signals.append("employee_party")
    if employer:
        signals.append("employer_party")
    if employee and employer:
        score += 2

    content_count = 0
    for name, pattern in _CONTENT.items():
        if pattern.search(text):
            signals.append(f"employment:{name}")
            content_count += 1
    score += min(content_count, 3)

    if len(_HEADING.findall(text)) >= 2 or _RIGHTS.search(text):
        signals.append("structure")
        score += 1

    negative = bool(_NEGATIVE.search(text)) and not (employee or employer)
    if negative:
        signals.append("strong_negative")
        score -= 3

    # Title alone is not enough; deep-body mentions confer no title points.
    employment_signal = employee or employer or content_count > 0
    accept = not negative and (
        (strong_title and employment_signal)
        or (score >= 4 and (employee or employer))
    )
    return ScopeDecision(accept=accept, score=score, signals=signals)
