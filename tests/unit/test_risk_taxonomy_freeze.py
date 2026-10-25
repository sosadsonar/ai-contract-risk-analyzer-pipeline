"""N3: khóa risk taxonomy đã đóng băng ở MS-1 (DEC-10).

Đổi nhãn, bảng severity hoặc version thì test này đỏ có chủ đích. Cách sửa: đổi doc, code, hằng ở
đây, và tăng version, trong cùng một PR.
"""

import hashlib
import re
from pathlib import Path

from app.core.enums import BasisType, Role
from app.risk import taxonomy as tx

ROOT = Path(__file__).resolve().parents[2]


def _find_taxonomy_doc() -> Path:
    """File duy nhất trong docs/ mà tên (viết thường) bắt đầu bằng 'risk_taxonomy' và đuôi .md.
    Assert đúng 1 file; 0 hoặc nhiều hơn 1 thì fail với danh sách tìm thấy."""
    found = sorted(
        p for p in (ROOT / "docs").glob("*.md") if p.name.lower().startswith("risk_taxonomy")
    )
    assert len(found) == 1, f"cần đúng 1 file risk_taxonomy*.md trong docs/, thấy: {found}"
    return found[0]


DOC = _find_taxonomy_doc()

FROZEN_RISK_TAXONOMY_VERSION = "risk_taxonomy_v01"
FROZEN_SEVERITY_RUBRIC_VERSION = "severity_v01"
FROZEN_TABLE_FINGERPRINT = "023478e54594c135be1947769bdfc6df09f5e46a706222128e82c14c133f5af3"

_BASES = (
    BasisType.LEGAL_VIOLATION.value,
    BasisType.UNFAVORABLE.value,
    BasisType.AMBIGUOUS.value,
)
_CODE = {"HIGH": "H", "MEDIUM": "M", "LOW": "L"}


def table_fingerprint() -> str:
    """sha256 hex (utf-8) của chuỗi: với từng nhãn trong RISK_LABELS (đúng thứ tự) một dòng
    f"{label}|{emp}|{er}", nối bằng "\\n", không có "\\n" cuối.
    emp/er = 3 ký tự ghép từ severity_for(label, basis, role) với basis theo thứ tự
    (LEGAL_VIOLATION, UNFAVORABLE, AMBIGUOUS): HIGH->'H', MEDIUM->'M', LOW->'L', None->'-'.
    Chỉ dùng API công khai của app.risk.taxonomy (không đọc _ROWS)."""
    lines = []
    for label in tx.RISK_LABELS:
        cells = []
        for role in (Role.EMPLOYEE.value, Role.EMPLOYER.value):
            sevs = (tx.severity_for(label, basis, role) for basis in _BASES)
            cells.append("".join("-" if s is None else _CODE[s.name] for s in sevs))
        lines.append(f"{label}|{cells[0]}|{cells[1]}")
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def test_frozen_versions():
    assert tx.RISK_TAXONOMY_VERSION == FROZEN_RISK_TAXONOMY_VERSION
    assert tx.SEVERITY_RUBRIC_VERSION == FROZEN_SEVERITY_RUBRIC_VERSION


def test_frozen_table_fingerprint():
    assert table_fingerprint() == FROZEN_TABLE_FINGERPRINT, (
        "Bảng severity hoặc nhãn đã đổi so với bản đóng băng. Nếu đổi có chủ đích: sửa doc, "
        "_ROWS, hằng FROZEN_TABLE_FINGERPRINT, và tăng version trong cùng PR."
    )


def test_doc_versions_match_code():
    text = DOC.read_text(encoding="utf-8")
    matches = re.findall(r"Version: `(risk_taxonomy_v\d+)`, rubric `(severity_v\d+)`", text)
    assert len(matches) == 1, matches
    assert matches[0] == (tx.RISK_TAXONOMY_VERSION, tx.SEVERITY_RUBRIC_VERSION)
