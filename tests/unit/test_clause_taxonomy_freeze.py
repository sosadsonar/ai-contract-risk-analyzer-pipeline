"""N1: khóa clause taxonomy tại MS-1 (BRD §8.2 quy tắc 5, SRS DEC-10/OI-10).

Đổi nhãn, định nghĩa, version hoặc giới hạn 1..3 nhãn thì test này đỏ CÓ CHỦ ĐÍCH. Cách sửa trong
CÙNG một PR: (1) sửa `taxonomy.py`, (2) tăng version, (3) cập nhật hằng FROZEN_* dưới đây,
(4) cập nhật `docs/CLAUSE_TAXONOMY_FREEZE.md` §1 và ghi lý do vào PROGRESS.md §9,
(5) review bắt buộc của N1 + N2 + N3. Sau MS-1 mọi thay đổi làm mất giá trị các số đo đã có.
"""

import hashlib
from pathlib import Path

from app.clause import taxonomy as tx

ROOT = Path(__file__).resolve().parents[2]
FREEZE_DOC = ROOT / "docs" / "CLAUSE_TAXONOMY_FREEZE.md"

FROZEN_DATA_TAXONOMY_VERSION = "clause_taxonomy_v03"
FROZEN_PROMPT_TAXONOMY_VERSION = "v04"
FROZEN_LABELS = (
    "JOB_INFO",
    "CONTRACT_TERM",
    "COMPENSATION_BENEFITS",
    "WORKING_TIME",
    "LEAVE",
    "INSURANCE_SAFETY",
    "WORKING_CONDITIONS",
    "TRAINING",
    "EMPLOYEE_OBLIGATIONS_DISCIPLINE",
    "EMPLOYER_RIGHTS_OBLIGATIONS",
    "TERMINATION",
    "OTHER",
)
FROZEN_FINGERPRINT = "2449733fe397438f4aa9ebee9bf2568c8f7708c2a10f837fbb46283b889390c2"


def taxonomy_fingerprint() -> str:
    """sha256 hex (utf-8) của: dòng đầu `data_ver|prompt_ver|min|max`, rồi mỗi nhãn (đúng thứ tự
    CLAUSE_LABELS) một dòng `LABEL|định nghĩa`; nối bằng "\\n", không có "\\n" cuối."""
    lines = [
        f"{tx.DATA_TAXONOMY_VERSION}|{tx.TAXONOMY_VERSION}"
        f"|{tx.MIN_LABELS_PER_CLAUSE}|{tx.MAX_LABELS_PER_CLAUSE}"
    ]
    lines += [f"{label}|{tx.LABEL_DEFINITIONS[label]}" for label in tx.CLAUSE_LABELS]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def test_frozen_versions_and_vocabulary():
    assert tx.DATA_TAXONOMY_VERSION == FROZEN_DATA_TAXONOMY_VERSION
    assert tx.TAXONOMY_VERSION == FROZEN_PROMPT_TAXONOMY_VERSION
    assert tx.CLAUSE_LABELS == FROZEN_LABELS


def test_frozen_multi_label_bounds():
    assert (tx.MIN_LABELS_PER_CLAUSE, tx.MAX_LABELS_PER_CLAUSE) == (1, 3)  # OI-10


def test_frozen_fingerprint():
    assert taxonomy_fingerprint() == FROZEN_FINGERPRINT, (
        "Clause taxonomy đã đổi so với bản đóng băng MS-1. Nếu đổi có chủ đích: tăng version, sửa "
        "FROZEN_*, docs/CLAUSE_TAXONOMY_FREEZE.md và PROGRESS.md §9 trong cùng PR."
    )


def test_freeze_doc_records_the_frozen_state():
    text = FREEZE_DOC.read_text(encoding="utf-8")
    assert FROZEN_FINGERPRINT in text
    assert FROZEN_DATA_TAXONOMY_VERSION in text and f"`{FROZEN_PROMPT_TAXONOMY_VERSION}`" in text
    for label in FROZEN_LABELS:
        assert f"`{label}`" in text, f"freeze doc thiếu nhãn {label}"
