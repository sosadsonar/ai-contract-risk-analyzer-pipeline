"""
Risk taxonomy = nhãn rủi ro + bảng severity theo (nhãn, basis_type, vai trò).
NGUỒN DUY NHẤT trong code (DEC-20), tương tự `app.clause.taxonomy`.

Nội dung nguồn: docs/RISK_TAXONOMY_v0.1.md. Test `tests/unit/test_risk_taxonomy.py` đọc
bảng trong file đó và so với `_ROWS` ở đây, nên sửa một nơi mà quên nơi kia là test đỏ.
Không chép lại danh sách nhãn / bảng severity ở chỗ khác (assembler, prompt, schema).

Quy trình gán nhãn cho một clause có rủi ro (theo vai trò của phiên):
  1. basis_type: LEGAL_VIOLATION | UNFAVORABLE | AMBIGUOUS (một giá trị cho cả clause)
  2. risk_labels: 1..3 nhãn trong RISK_LABELS
  3. severity: do CODE tra bảng theo (nhãn, basis_type, vai trò); nhiều nhãn thì lấy mức cao nhất.
     LLM không trả severity. Chỉ có tra xuôi; không có (và không thể có) tra ngược từ
     (nhãn, vai trò, severity) về basis vì nhiều basis cùng mức (vd HMM: UF và AM đều M).
     Ô '-' nghĩa là tổ hợp đó KHÔNG phải rủi ro của vai trò này (điều khoản có lợi hơn luật
     cho một bên không phải rủi ro của bên đó, BRD 3.2) => kết quả gán sai, cần review.

Cột "clause label tham khảo" chỉ là gợi ý (clause có 1..3 nhãn clause, nhãn OTHER gom nhiều
chủ đề). KHÔNG dùng nó để lọc hay giới hạn nhãn rủi ro.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from app.clause.taxonomy import CLAUSE_LABEL_SET
from app.core.enums import BasisType, Role, Severity

# Tên version theo TDD §15.2. Bản nội dung hiện tại = docs/RISK_TAXONOMY_v0.1.md.
# Đóng băng ở MS-1 (25/10): đổi nhãn hoặc bảng severity thì tăng version có chủ đích.
RISK_TAXONOMY_VERSION = "risk_taxonomy_v02"
SEVERITY_RUBRIC_VERSION = "severity_v01"  # rubric HIGH/MEDIUM/LOW ở SRS 2.3

MAX_RISK_LABELS_PER_CLAUSE = 3

# Mỗi dòng: (risk_label, clause label tham khảo, severity NLĐ, severity NSDLĐ).
# Chuỗi severity có 3 ký tự theo thứ tự (LEGAL_VIOLATION, UNFAVORABLE, AMBIGUOUS);
# H=HIGH, M=MEDIUM, L=LOW, '-'=không phải rủi ro của vai trò này.
# Thứ tự dòng = thứ tự trong doc = thứ tự enum trong risk_output_v2.json.
_ROWS: tuple[tuple[str, str, str, str], ...] = (
    ("CONTRACT_TERM_TYPE", "CONTRACT_TERM", "MLM", "HLM"),
    ("PROBATION", "CONTRACT_TERM", "HLM", "H-M"),
    ("WAGE_AMOUNT_COMPONENTS", "COMPENSATION_BENEFITS", "HMM", "HMM"),
    ("BONUS_BENEFITS", "COMPENSATION_BENEFITS", "MMM", "HML"),
    ("PAYMENT_TIMING_METHOD", "COMPENSATION_BENEFITS", "HMM", "H-M"),
    ("WORKING_HOURS_OVERTIME", "WORKING_TIME", "HMM", "HLL"),
    ("REST_AND_LEAVE", "LEAVE", "HMM", "HLL"),
    ("SOCIAL_INSURANCE", "INSURANCE_SAFETY", "H-M", "H-M"),
    ("OSH_OBLIGATION", "INSURANCE_SAFETY", "H-M", "H-M"),
    ("UNILATERAL_CHANGE", "EMPLOYER_RIGHTS_OBLIGATIONS", "HMM", "MLL"),
    ("PENALTY_DEDUCTION_DAMAGES", "EMPLOYEE_OBLIGATIONS_DISCIPLINE", "HMM", "HLM"),
    ("DISCIPLINE_OBLIGATION", "EMPLOYEE_OBLIGATIONS_DISCIPLINE", "HMM", "HLM"),
    ("POST_EMPLOYMENT_RESTRICTION", "EMPLOYEE_OBLIGATIONS_DISCIPLINE", "MMM", "MLM"),
    ("DEPOSIT_DOCUMENT_HELD", "WORKING_CONDITIONS", "H-M", "H-M"),
    ("DISCRIMINATION_PROTECTED_GROUPS", "WORKING_CONDITIONS", "H-M", "H-M"),
    ("TRAINING_COMMITMENT", "TRAINING", "HMM", "HLM"),
    ("TERMINATION_GROUNDS_NOTICE", "TERMINATION", "HMM", "HMM"),
    ("TERMINATION_SETTLEMENT", "TERMINATION", "HMM", "HLM"),
    ("WAIVER_RIGHTS_DISPUTE", "OTHER", "HMM", "H-L"),
    ("PERSONAL_DATA_PRIVACY", "OTHER", "MMM", "H-M"),
    ("CONTRACT_FORM_RULES", "OTHER", "MMM", "M-M"),
)

_BASIS_ORDER: tuple[str, ...] = (
    BasisType.LEGAL_VIOLATION.value,
    BasisType.UNFAVORABLE.value,
    BasisType.AMBIGUOUS.value,
)
_SEVERITY_CODE: Mapping[str, Severity | None] = MappingProxyType(
    {"H": Severity.HIGH, "M": Severity.MEDIUM, "L": Severity.LOW, "-": None}
)
_SEVERITY_RANK: Mapping[Severity, int] = MappingProxyType(
    {Severity.LOW: 1, Severity.MEDIUM: 2, Severity.HIGH: 3}
)


def _expand() -> dict[str, dict[str, dict[str, Severity | None]]]:
    table: dict[str, dict[str, dict[str, Severity | None]]] = {}
    for label, _clause, employee, employer in _ROWS:
        per_role = {Role.EMPLOYEE.value: employee, Role.EMPLOYER.value: employer}
        table[label] = {
            role: {basis: _SEVERITY_CODE[code] for basis, code in zip(_BASIS_ORDER, codes)}
            for role, codes in per_role.items()
        }
    return table


_SEVERITY_TABLE = _expand()

# Có thứ tự (thứ tự trong doc). Schema risk_output_v2.json phải khớp đúng thứ tự này.
RISK_LABELS: tuple[str, ...] = tuple(row[0] for row in _ROWS)
RISK_LABEL_SET: frozenset[str] = frozenset(RISK_LABELS)

# Gợi ý clause label thường chứa rủi ro này (tham khảo, không ràng buộc).
TYPICAL_CLAUSE_LABEL: Mapping[str, str] = MappingProxyType({row[0]: row[1] for row in _ROWS})

if not set(TYPICAL_CLAUSE_LABEL.values()) <= CLAUSE_LABEL_SET:  # fail sớm khi import
    raise RuntimeError("risk taxonomy tham chiếu clause label không tồn tại")


def severity_for(label: str, basis: str, role: str) -> Severity | None:
    """Severity theo bảng; None nghĩa là '-' (không phải rủi ro của vai trò này).

    Raise ValueError nếu nhãn / basis / role không thuộc taxonomy (khác với '-').
    """
    row = _SEVERITY_TABLE.get(label)
    if row is None:
        raise ValueError(f"Nhãn rủi ro ngoài taxonomy: {label!r}")
    by_basis = row.get(str(getattr(role, "value", role)))
    if by_basis is None:
        raise ValueError(f"Vai trò không hợp lệ: {role!r}")
    basis_key = str(getattr(basis, "value", basis))
    if basis_key not in by_basis:
        raise ValueError(f"basis_type không hợp lệ: {basis!r}")
    return by_basis[basis_key]


def severity_for_labels(labels: Iterable[str], basis: str, role: str) -> Severity | None:
    """Severity của một clause nhiều nhãn: mức cao nhất trong các nhãn hợp lệ cho vai trò.

    Trả None nếu không nhãn nào hợp lệ (tất cả là '-').
    """
    found = [s for s in (severity_for(x, basis, role) for x in labels) if s is not None]
    return max(found, key=_SEVERITY_RANK.__getitem__) if found else None


def invalid_labels_for_role(labels: Iterable[str], basis: str, role: str) -> list[str]:
    """Các nhãn có ô '-' cho (basis, role): gán sai hoặc không phải rủi ro của vai trò."""
    return [x for x in labels if severity_for(x, basis, role) is None]
