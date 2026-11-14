"""
report_model.py — C-21(a): Xây dựng ReportModel từ final_result_v1 (TDD §16.1).

Hàm thuần (không gọi LLM, không import api/ hay session/). Render DOCX ở `export_docx.py` (C-21 b).

Bổ sung W5 (C-21 b, X-23): tóm tắt (TDD §16.1), số Điều hiển thị thay `cl_xxxx`, "Liên quan: Điều X" (FR-32),
bản ghi "cần xem xét" (needs_review: không nhãn, không severity), số Khoản của citation, cảnh báo BR-15.

Quy tắc:
- Quote clause dùng original_text (KHÔNG dùng masked text).
- Mức độ: severity HIGH/MEDIUM/LOW, hoặc "chưa đủ căn cứ" khi severity là null
  hoặc evidence_status là INSUFFICIENT_EVIDENCE.
- Rủi ro rỗng: câu cố định "Không phát hiện rủi ro trong phạm vi phân tích"
  (không dùng chữ "an toàn").
- Sắp xếp rủi ro theo thứ tự clause xuất hiện trong văn bản (start_char tăng dần).
- Clause không có rủi ro không đưa vào danh sách.
- citation_id không tìm thấy: ghi nhận lỗi rõ ràng trong CitationRef.missing=True.
- disclaimer và data_notice bắt buộc (FR-25).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Câu hiển thị khi không có rủi ro (TDD §16.1, PROGRESS.md T5 N5).
# TUYỆT ĐỐI không dùng chữ "an toàn".
NO_RISK_MESSAGE = "Không phát hiện rủi ro trong phạm vi phân tích."
# BR-15: rủi ro không đủ căn cứ trong kho luật (không gán mức độ).
INSUFFICIENT_MESSAGE = "Có thể có rủi ro, chưa đủ căn cứ trong kho luật, cần đọc kỹ."
# TDD §15.5 / X-22: tổ hợp nhãn – loại căn cứ – vai trò không hợp lệ sau retry.
NEEDS_REVIEW_MESSAGE = "Nghi ngờ, cần xem xét: hệ thống chưa xác định được loại rủi ro phù hợp cho điều khoản này."
_ARTICLE = re.compile(r"^\s*(Điều)\s+(\d+[a-zA-ZđĐ]?)", re.IGNORECASE)

# Nhãn severity hiển thị
_SEVERITY_LABELS: dict[str | None, str] = {
    "HIGH": "Cao",
    "MEDIUM": "Trung bình",
    "LOW": "Thấp",
    None: "chưa đủ căn cứ",
}

_BASIS_TYPE_LABELS: dict[str, str] = {
    "LEGAL_VIOLATION": "Vi phạm pháp luật",
    "UNFAVORABLE": "Bất lợi",
    "AMBIGUOUS": "Mơ hồ / thiếu rõ ràng",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CitationRef:
    """Một citation đã tra cứu từ final_result_v1.citations."""

    citation_id: str
    document_name: str
    article: str
    content: str
    missing: bool = False  # True nếu citation_id không có trong citations dict
    clause: str | None = None  # số Khoản khi nút trích dẫn là Khoản (X-16)

    @property
    def heading(self) -> str:
        """"Khoản 1 Điều 21 Bộ luật Lao động..." — hiển thị nguyên văn Khoản ở thân (X-23)."""
        parts = []
        if self.clause:
            parts.append(f"Khoản {self.clause}")
        if self.article:
            parts.append(f"Điều {self.article}")
        if self.document_name:
            parts.append(self.document_name)
        return " ".join(parts) or self.citation_id


@dataclass
class RiskBasisItem:
    label: str
    basis_type: str
    basis_type_label: str = ""

    def __post_init__(self) -> None:
        self.basis_type_label = _BASIS_TYPE_LABELS.get(self.basis_type, self.basis_type)


@dataclass
class RiskItem:
    """Một mục rủi ro trong báo cáo."""

    clause_id: str
    clause_quote: str          # original_text của clause (không masked)
    clause_start_char: int     # để sắp xếp theo thứ tự xuất hiện
    risk_labels: list[str]
    risk_basis: list[RiskBasisItem]
    severity_raw: str | None   # "HIGH" | "MEDIUM" | "LOW" | None
    severity_label: str        # "Cao" / "Trung bình" / "Thấp" / "chưa đủ căn cứ"
    show_severity_badge: bool  # False khi INSUFFICIENT_EVIDENCE hoặc severity=null
    explanation: str
    evidence_status: str
    citations: list[CitationRef]
    clause_display: str = ""                         # "Điều 5" hoặc "Điều khoản số 3" (thay cl_xxxx)
    related_displays: list[str] = field(default_factory=list)  # "Liên quan: Điều X" (FR-32)
    needs_review: bool = False
    status_message: str | None = None                # BR-15 / cần xem xét


@dataclass
class ReportSummary:
    clause_count: int
    risky_clause_count: int
    high: int
    medium: int
    low: int
    insufficient: int
    needs_review: int


@dataclass
class GeneralInfo:
    role: str           # "EMPLOYEE" | "EMPLOYER"
    role_label: str     # "Người lao động" | "Người sử dụng lao động"
    analysis_date: str  # ISO date string
    session_id: str
    version_pins: dict[str, Any]


@dataclass
class ReportModel:
    """Model đầy đủ cho báo cáo phân tích rủi ro hợp đồng lao động."""

    title: str
    general_info: GeneralInfo
    risks: list[RiskItem]          # đã sắp xếp theo start_char
    no_risk_message: str | None    # None nếu có rủi ro; chuỗi nếu risks rỗng
    disclaimer: str                # bắt buộc (FR-25)
    data_notice: str               # bắt buộc (FR-25)
    summary: ReportSummary | None = None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_ROLE_LABELS = {
    "EMPLOYEE": "Người lao động",
    "EMPLOYER": "Người sử dụng lao động",
}


def clause_display(clause: dict[str, Any], ordinal: int) -> str:
    """"Điều N" nếu clause mở đầu bằng heading Điều; ngược lại "Điều khoản số <thứ tự>" (X-23)."""
    m = _ARTICLE.match(clause.get("original_text", ""))
    return f"Điều {m.group(2)}" if m else f"Điều khoản số {ordinal}"


def _resolve_citation(cid: str, citation_map: dict[str, dict[str, Any]]) -> CitationRef:
    """Tra cứu citation từ map; nếu thiếu thì ghi missing=True và log warning."""
    if cid in citation_map:
        c = citation_map[cid]
        return CitationRef(
            citation_id=cid,
            document_name=c.get("document_name", ""),
            article=c.get("article", ""),
            content=c.get("content", ""),
            missing=False,
            clause=c.get("clause"),
        )
    logger.warning("citation_id '%s' không tìm thấy trong citations; ghi missing=True", cid)
    return CitationRef(
        citation_id=cid,
        document_name="",
        article="",
        content="",
        missing=True,
    )


def _build_risk_item(
    risk: dict[str, Any],
    clause_map: dict[str, dict[str, Any]],
    citation_map: dict[str, dict[str, Any]],
    displays: dict[str, str] | None = None,
) -> RiskItem | None:
    """
    Xây dựng RiskItem từ một entry trong final_result_v1.risks.
    Raises ValueError nếu clause_id không có trong clause_map.
    """
    cid = risk.get("clause_id", "")
    clause = clause_map.get(cid)
    if clause is None:
        # Không bỏ qua âm thầm: nếu mọi risk bị bỏ, báo cáo sẽ sai thành "không phát hiện rủi ro".
        raise ValueError(
            f"risk tham chiếu clause_id '{cid}' không có trong clauses; "
            "final_result không hợp lệ"
        )

    severity_raw: str | None = risk.get("severity")
    evidence_status: str = risk.get("evidence_status", "SUPPORTED")

    # INSUFFICIENT_EVIDENCE hoặc severity=null → không hiện badge, hiện "chưa đủ căn cứ"
    is_insufficient = (
        evidence_status == "INSUFFICIENT_EVIDENCE" or severity_raw is None
    )
    severity_label = "chưa đủ căn cứ" if is_insufficient else _SEVERITY_LABELS.get(severity_raw, str(severity_raw))

    risk_basis_items = [
        RiskBasisItem(label=rb.get("label", ""), basis_type=rb.get("basis_type", ""))
        for rb in risk.get("risk_basis", [])
    ]

    citations = [
        _resolve_citation(citation_id, citation_map)
        for citation_id in risk.get("citation_ids", [])
    ]

    displays = displays or {}
    needs_review = bool(risk.get("needs_review"))
    status_message = NEEDS_REVIEW_MESSAGE if needs_review else (INSUFFICIENT_MESSAGE if is_insufficient else None)
    return RiskItem(
        clause_display=displays.get(cid, cid),
        related_displays=[displays.get(x, x) for x in risk.get("related_clause_ids", [])],
        needs_review=needs_review,
        status_message=status_message,
        clause_id=cid,
        clause_quote=clause.get("original_text", ""),
        clause_start_char=clause.get("start_char", 0),
        risk_labels=list(risk.get("risk_labels", [])),
        risk_basis=risk_basis_items,
        severity_raw=severity_raw,
        severity_label=severity_label,
        show_severity_badge=not is_insufficient,
        explanation=risk.get("explanation", ""),
        evidence_status=evidence_status,
        citations=citations,
    )


# ---------------------------------------------------------------------------
# Hàm công khai
# ---------------------------------------------------------------------------


def build_report_model(final_result: dict[str, Any]) -> ReportModel:
    """
    Xây dựng ReportModel từ dict theo schema final_result_v1.

    Args:
        final_result: dict khớp ai_pipeline/schemas/final_result_v1.json.

    Returns:
        ReportModel đã điền đầy đủ.

    Raises:
        ValueError: nếu thiếu disclaimer/data_notice, hoặc có risk trỏ tới clause_id không tồn tại.
    """
    disclaimer = final_result.get("disclaimer")
    data_notice = final_result.get("data_notice")
    if not disclaimer:
        raise ValueError("final_result thiếu trường 'disclaimer' (FR-25)")
    if not data_notice:
        raise ValueError("final_result thiếu trường 'data_notice' (FR-25)")

    role: str = final_result.get("role", "")
    general_info = GeneralInfo(
        role=role,
        role_label=_ROLE_LABELS.get(role, role),
        analysis_date=final_result.get("analysis_date", ""),
        session_id=final_result.get("session_id", ""),
        version_pins=dict(final_result.get("version_pins", {})),
    )

    # Xây map để tra nhanh
    clause_map: dict[str, dict[str, Any]] = {
        c["clause_id"]: c for c in final_result.get("clauses", []) if "clause_id" in c
    }
    citation_map: dict[str, dict[str, Any]] = {
        c["citation_id"]: c
        for c in final_result.get("citations", [])
        if "citation_id" in c
    }

    ordered = sorted(clause_map.values(), key=lambda c: c.get("start_char", 0))
    displays = {c["clause_id"]: clause_display(c, i) for i, c in enumerate(ordered, 1)}

    # Xây risk items, lọc bỏ None (clause không tìm thấy)
    raw_risks: list[dict[str, Any]] = final_result.get("risks", [])
    risk_items: list[RiskItem] = []
    for raw_risk in raw_risks:
        item = _build_risk_item(raw_risk, clause_map, citation_map, displays)
        if item is not None:
            risk_items.append(item)

    # Sắp xếp theo thứ tự xuất hiện trong văn bản
    risk_items.sort(key=lambda r: r.clause_start_char)

    no_risk_message: str | None = None
    if not risk_items:
        no_risk_message = NO_RISK_MESSAGE

    reviewable = [r for r in risk_items if not r.needs_review]
    summary = ReportSummary(
        clause_count=len(clause_map),
        risky_clause_count=len({r.clause_id for r in risk_items}),
        high=sum(r.severity_raw == "HIGH" and r.show_severity_badge for r in reviewable),
        medium=sum(r.severity_raw == "MEDIUM" and r.show_severity_badge for r in reviewable),
        low=sum(r.severity_raw == "LOW" and r.show_severity_badge for r in reviewable),
        insufficient=sum(not r.show_severity_badge for r in reviewable),
        needs_review=sum(r.needs_review for r in risk_items),
    )

    return ReportModel(
        summary=summary,
        title="Phân tích rủi ro hợp đồng lao động",
        general_info=general_info,
        risks=risk_items,
        no_risk_message=no_risk_message,
        disclaimer=disclaimer,
        data_notice=data_notice,
    )

