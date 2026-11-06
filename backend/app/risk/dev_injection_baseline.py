"""Frozen D2 Dev Article 17 text baseline for out-of-sample T2 evaluation.

The patterns reproduce the D2 development OR rule without looking at T2 labels.
This module returns only text-triggered candidate roles and labels, never Gold IDs.
"""

import re
import unicodedata

_DEPOSIT = re.compile(
    r"giữ.{0,25}(giấy tờ|bản chính|văn bằng|chứng chỉ)"
    r"|(?:tiền|tài sản).{0,35}(đặt cọc|ký quỹ|bảo đảm|đảm bảo|nộp|giao)"
    r"|(?:đặt cọc|ký quỹ|bảo đảm|đảm bảo).{0,35}(?:tiền|tài sản)"
)
_DEBT_WORK = re.compile(
    r"(nợ|khoản vay).{0,70}(làm việc|tiếp tục|nghỉ việc|chấm dứt)"
    r"|(làm việc|tiếp tục|nghỉ việc|chấm dứt).{0,70}(nợ|khoản vay)"
)
_EMPLOYEE_DEPOSIT = re.compile(r"(người lao động|nlđ|nhân viên).{0,45}(phải|có nghĩa vụ|nộp|đặt cọc|ký quỹ|giao)")
_EMPLOYER_HOLDS = re.compile(r"(công ty|bên a|người sử dụng lao động).{0,45}(giữ|thu giữ|tạm giữ|nhận)")
_EMPLOYER_DEPOSIT = re.compile(r"(công ty|bên a|người sử dụng lao động).{0,45}(giữ|thu|nhận|yêu cầu|buộc)")
_EMPLOYER_DEBT = re.compile(r"(công ty|bên a|người sử dụng lao động).{0,60}(yêu cầu|buộc|không chấp thuận|quyết định)")
_EMPLOYEE_DEBT = re.compile(r"(người lao động|nlđ|nhân viên).{0,60}(phải|tiếp tục|không được|chưa được)")


def detect_dev_risks(text: str) -> tuple[tuple[str, str], ...]:
    """Return (role, risk label) pairs from contract text only."""
    normalized = unicodedata.normalize("NFC", text).casefold()
    rows = []
    if _DEPOSIT.search(normalized):
        role = (
            "EMPLOYER"
            if _EMPLOYER_HOLDS.search(normalized)
            else "EMPLOYEE"
            if _EMPLOYEE_DEPOSIT.search(normalized)
            else "EMPLOYER"
            if _EMPLOYER_DEPOSIT.search(normalized)
            else None
        )
        if role:
            rows.append((role, "DEPOSIT_DOCUMENT_HELD"))
    if _DEBT_WORK.search(normalized):
        role = (
            "EMPLOYER"
            if _EMPLOYER_DEBT.search(normalized)
            else "EMPLOYEE"
            if _EMPLOYEE_DEBT.search(normalized)
            else None
        )
        if role:
            rows.append((role, "EMPLOYEE_OBLIGATIONS_DISCIPLINE"))
    return tuple(rows)
