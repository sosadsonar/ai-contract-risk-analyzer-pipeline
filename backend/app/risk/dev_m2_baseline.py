"""Dev-only source-text risk baseline; never consults Gold, IDs, or offsets."""

from __future__ import annotations

import re
import unicodedata

from app.risk.dev_injection_candidate import detect_dev_risks_candidate

_OTHER_WORK = re.compile(
    r"(?:công\s+việc|nhiệm\s+vụ|địa\s+điểm\s+làm\s+việc)"
    r".{0,100}?(?:khác|mọi|bất\s+kỳ|tùy\s+ý)"
    r".{0,120}?(?:công\s+ty|ban\s+giám\s+đốc|người\s+sử\s+dụng"
    r"|theo\s+yêu\s+cầu|theo\s+quyết\s+định)",
    re.DOTALL,
)
_ASSIGNMENT = re.compile(
    r"(?:phân\s+công|điều\s+động|điều\s+chuyển)"
    r".{0,90}?(?:công\s+ty|ban\s+giám\s+đốc|người\s+sử\s+dụng)",
    re.DOTALL,
)
_EMPLOYER_CHANGE = re.compile(
    r"(?:công\s+ty|ban\s+giám\s+đốc|người\s+sử\s+dụng)"
    r".{0,80}?(?:có\s+quyền|được\s+quyền|toàn\s+quyền)"
    r".{0,80}?(?:thay\s+đổi|điều\s+chỉnh)"
    r".{0,100}?(?:lương|công\s+việc|địa\s+điểm|chức\s+danh|ca\s+làm)",
    re.DOTALL,
)
_AGREED = re.compile(r"(?:theo\s+thỏa\s+thuận|được\s+sự\s+đồng\s+ý|hai\s+bên\s+thỏa\s+thuận)")


def _has_unilateral_change(text: str) -> bool:
    for pattern in (_OTHER_WORK, _ASSIGNMENT, _EMPLOYER_CHANGE):
        for match in pattern.finditer(text):
            if not _AGREED.search(match.group()):
                return True
    return False


def detect_dev_m2_risks(text: str) -> tuple[tuple[str, str, str], ...]:
    """Return local Dev proxy (role, canonical risk label, basis type)."""
    normalized = unicodedata.normalize("NFC", text).casefold()
    emitted = set()
    for role, legacy_label in detect_dev_risks_candidate(text):
        label = ("DISCIPLINE_OBLIGATION" if legacy_label == "EMPLOYEE_OBLIGATIONS_DISCIPLINE"
                 else legacy_label)
        emitted.add((role, label, "LEGAL_VIOLATION"))
    if _has_unilateral_change(normalized):
        emitted.add(("EMPLOYEE", "UNILATERAL_CHANGE", "AMBIGUOUS"))
    return tuple(sorted(emitted))
