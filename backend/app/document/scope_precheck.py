"""FR-06 local scope decision on a copy of canonical text (TDD §9)."""

import re
import unicodedata
from dataclasses import dataclass

# scope_rules_v2 (SRS OI-03, OPEN_ISSUES_HANDLE_v4 §4.3): R1 negative title prefix, R2 both parties
# on the no-strong-title branch. OI-03 stays OPEN: keywords/thresholds are not locked until the
# independent review set (10 negative / 6 positive, §4.4) is run. Every new prefix needs at least
# one negative case and a positive regression run, and a new SCOPE_RULE_VERSION.
SCOPE_RULE_VERSION = "scope_rules_v2"


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
# R1: first non-empty line of the title window (NFC/casefold copy) starting with one of these
# prefixes is out of scope. A standalone appendix is out of scope; an appendix in the same file
# after the contract is still accepted because only the first line is checked.
_NEGATIVE_TITLE_PREFIXES = (
    "phụ lục", "nội quy", "quy chế", "thỏa ước", "thoả ước", "cam kết", "biên bản", "quyết định",
    "hợp đồng dịch vụ", "hợp đồng mua bán", "hợp đồng thuê", "hợp đồng khoán",
)
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

    first_line = next((line.strip() for line in title.split("\n") if line.strip()), "")
    if first_line.startswith(_NEGATIVE_TITLE_PREFIXES):
        return ScopeDecision(accept=False, score=0, signals=["negative_title"])

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
        or (score >= 4 and employee and employer)  # R2: both parties without a strong title
    )
    return ScopeDecision(accept=accept, score=score, signals=signals)
