"""X-01: risk taxonomy trong code (app.risk.taxonomy) khớp doc RISK_TAXONOMY_v0.1.md (DEC-20)."""

import re
from pathlib import Path

import pytest
from app.clause.taxonomy import CLAUSE_LABEL_SET
from app.core.enums import BasisType, Role, Severity
from app.risk import taxonomy as tx

DOC = Path(__file__).resolve().parents[2] / "docs" / "RISK_TAXONOMY_v0.1.md"
_SEV = {"H": Severity.HIGH, "M": Severity.MEDIUM, "L": Severity.LOW, "-": None}
_BASES = [b.value for b in (BasisType.LEGAL_VIOLATION, BasisType.UNFAVORABLE, BasisType.AMBIGUOUS)]


def _doc_rows():
    """Đọc bảng trong doc: [(label, clause_label, [3 mã NLĐ], [3 mã NSDLĐ])]."""
    rows = []
    for line in DOC.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) == 6 and re.fullmatch(r"[A-Z_]+", cells[0]):
            emp = [x.strip() for x in cells[3].split("/")]
            er = [x.strip() for x in cells[4].split("/")]
            rows.append((cells[0], cells[1], emp, er))
    return rows


def test_21_unique_labels_in_doc_order():
    assert len(tx.RISK_LABELS) == 21
    assert len(set(tx.RISK_LABELS)) == 21
    assert tuple(r[0] for r in _doc_rows()) == tx.RISK_LABELS


def test_doc_table_matches_code_for_every_label_basis_role():
    for label, clause_label, emp, er in _doc_rows():
        for role, codes in ((Role.EMPLOYEE.value, emp), (Role.EMPLOYER.value, er)):
            assert len(codes) == 3, (label, role, codes)
            for basis, code in zip(_BASES, codes):
                assert tx.severity_for(label, basis, role) == _SEV[code], (label, basis, role)
        assert tx.TYPICAL_CLAUSE_LABEL[label] == clause_label


def test_typical_clause_labels_are_real_clause_labels():
    assert set(tx.TYPICAL_CLAUSE_LABEL.values()) <= CLAUSE_LABEL_SET


def test_versions():
    assert tx.RISK_TAXONOMY_VERSION == "risk_taxonomy_v02"
    assert tx.SEVERITY_RUBRIC_VERSION == "severity_v01"


def test_dash_cell_means_not_a_risk_for_role():
    assert tx.severity_for("SOCIAL_INSURANCE", "UNFAVORABLE", "EMPLOYEE") is None
    assert tx.severity_for("PROBATION", "UNFAVORABLE", "EMPLOYER") is None
    labels = ["PROBATION", "BONUS_BENEFITS"]
    assert tx.invalid_labels_for_role(labels, "UNFAVORABLE", "EMPLOYER") == ["PROBATION"]


def test_same_clause_can_differ_by_role():
    assert tx.severity_for("BONUS_BENEFITS", "LEGAL_VIOLATION", "EMPLOYEE") is Severity.MEDIUM
    assert tx.severity_for("BONUS_BENEFITS", "LEGAL_VIOLATION", "EMPLOYER") is Severity.HIGH


def test_severity_for_labels_takes_highest_valid_label():
    # CONTRACT_TERM_TYPE LV nhân viên = MEDIUM, PROBATION LV nhân viên = HIGH
    both = ["CONTRACT_TERM_TYPE", "PROBATION"]
    assert tx.severity_for_labels(both, "LEGAL_VIOLATION", "EMPLOYEE") is Severity.HIGH
    # nhãn '-' bị bỏ qua, không kéo mức xuống
    assert tx.severity_for_labels(["PROBATION", "BONUS_BENEFITS"], "UNFAVORABLE", "EMPLOYER") is (
        Severity.MEDIUM
    )
    assert tx.severity_for_labels(["SOCIAL_INSURANCE"], "UNFAVORABLE", "EMPLOYEE") is None


@pytest.mark.parametrize(
    "args",
    [
        ("NOT_A_LABEL", "LEGAL_VIOLATION", "EMPLOYEE"),
        ("PROBATION", "BAD", "EMPLOYEE"),
        ("PROBATION", "AMBIGUOUS", "ADMIN"),
    ],
)
def test_unknown_inputs_raise_instead_of_looking_like_a_dash(args):
    with pytest.raises(ValueError):
        tx.severity_for(*args)


def test_lv_is_never_below_uf_or_am_within_a_role():
    """Quy tắc rubric: vi phạm pháp luật không thấp hơn bất lợi hay mơ hồ cùng vai trò.
    Đỏ nghĩa là bảng v0.1 vừa bị sửa ra ô vô lý; sửa lại bảng chứ không nới test."""
    rank = {None: 0, Severity.LOW: 1, Severity.MEDIUM: 2, Severity.HIGH: 3}
    bad = []
    for label in tx.RISK_LABELS:
        for role in (Role.EMPLOYEE.value, Role.EMPLOYER.value):
            lv, uf, am = (tx.severity_for(label, b, role) for b in _BASES)
            if rank[lv] < max(rank[uf], rank[am]):
                bad.append((label, role))
    assert bad == []
