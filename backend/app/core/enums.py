"""
Enum chuẩn của hệ thống — MỘT nguồn duy nhất trong code (TDD §6.1, DEC-20).

Không chép lại các giá trị này ở chỗ khác. JSON Schema (ai_pipeline/schemas/*.json)
phải được sinh từ đây hoặc có test đối chiếu (tests/contract/test_schema_enums.py).

Nhãn clause (12 nhãn) KHÔNG nằm ở đây mà ở `app.clause.taxonomy` vì kèm định nghĩa
dùng cho prompt. Nhãn rủi ro (risk taxonomy, OI-01) do Người 3 định nghĩa riêng.
"""

from enum import Enum


class Role(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    EMPLOYER = "EMPLOYER"


class SessionStatus(str, Enum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    REJECTED = "REJECTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class Stage(str, Enum):
    UPLOAD = "UPLOAD"
    EXTRACTION = "EXTRACTION"
    SCOPE_PRECHECK = "SCOPE_PRECHECK"
    PII_MASKING = "PII_MASKING"
    SEGMENTATION = "SEGMENTATION"
    CLAUSE_GRAPH = "CLAUSE_GRAPH"
    CLAUSE_CLASSIFICATION = "CLAUSE_CLASSIFICATION"
    LEGAL_RETRIEVAL = "LEGAL_RETRIEVAL"
    RISK_ANALYSIS = "RISK_ANALYSIS"
    CITATION_VALIDATION = "CITATION_VALIDATION"
    ASSEMBLY = "ASSEMBLY"
    EXPORT = "EXPORT"


class Severity(str, Enum):
    """`None` (không phải thành viên enum) = thiếu căn cứ (INSUFFICIENT_EVIDENCE)."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvidenceStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class BasisType(str, Enum):
    LEGAL_VIOLATION = "LEGAL_VIOLATION"
    UNFAVORABLE = "UNFAVORABLE"
    AMBIGUOUS = "AMBIGUOUS"


class LegalEdgeType(str, Enum):
    PARENT_OF = "PARENT_OF"
    REFERS_TO = "REFERS_TO"
    GUIDES = "GUIDES"


class ClauseEdgeType(str, Enum):
    NEXT = "NEXT"
    PARENT_OF = "PARENT_OF"
    REFERS_TO = "REFERS_TO"
