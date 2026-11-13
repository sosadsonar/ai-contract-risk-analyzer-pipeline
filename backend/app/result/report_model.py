"""
report_model.py — C-21(a): Xây dựng ReportModel từ final_result_v1 (TDD §16.1).

Hàm thuần (không gọi LLM, không import api/ hay session/).
Chỉ làm phần model; export_docx sẽ làm ở tuần 5 (C-21 b).

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
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Câu hiển thị khi không có rủi ro (TDD §16.1, PROGRESS.md T5 N5).
# TUYỆT ĐỐI không dùng chữ "an toàn".
NO_RISK_MESSAGE = "Không phát hiện rủi ro trong phạm vi phân tích."

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
    clause: str | None = None  # X-16: tên/số điều khoản pháp lý liên quan


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
    # X-16 / C-21(b): các trường bổ sung với default backward-compatible
    clause_number: str | None = None                           # số/tên điều khoản ("Điều 1" v.v.)
    related_clause_numbers: list[str] = field(default_factory=list)  # điều khoản liên quan
    needs_review: bool = False  # True khi không có risk_labels VÀ severity là null


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


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_ROLE_LABELS = {
    "EMPLOYEE": "Người lao động",
    "EMPLOYER": "Người sử dụng lao động",
}


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
            clause=c.get("clause"),  # X-16: trường tùy chọn
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
    clause_order_map: dict[str, int] | None = None,
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

    # X-16: related_clause_ids → tra cứu clause_number từ clause_map (id lạ an toàn bỏ qua)
    related_clause_numbers: list[str] = []
    for related_id in risk.get("related_clause_ids", []):
        related_clause = clause_map.get(related_id)
        if related_clause is not None:
            cn = related_clause.get("clause_number")
            if cn:
                related_clause_numbers.append(cn)
            elif clause_order_map and related_id in clause_order_map:
                related_clause_numbers.append(f"Điều khoản thứ {clause_order_map[related_id]}")

    # clause_number của clause chính
    clause_number: str | None = clause.get("clause_number")

    # needs_review: không có risk_labels VÀ severity là null
    risk_labels_list = list(risk.get("risk_labels", []))
    needs_review = (not risk_labels_list) and (severity_raw is None)

    return RiskItem(
        clause_id=cid,
        clause_quote=clause.get("original_text", ""),
        clause_start_char=clause.get("start_char", 0),
        risk_labels=risk_labels_list,
        risk_basis=risk_basis_items,
        severity_raw=severity_raw,
        severity_label=severity_label,
        show_severity_badge=not is_insufficient,
        explanation=risk.get("explanation", ""),
        evidence_status=evidence_status,
        citations=citations,
        clause_number=clause_number,
        related_clause_numbers=related_clause_numbers,
        needs_review=needs_review,
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
    clause_list = final_result.get("clauses", [])
    clause_map: dict[str, dict[str, Any]] = {
        c["clause_id"]: c for c in clause_list if "clause_id" in c
    }
    clause_order_map: dict[str, int] = {
        c["clause_id"]: idx + 1 for idx, c in enumerate(clause_list) if "clause_id" in c
    }
    citation_map: dict[str, dict[str, Any]] = {
        c["citation_id"]: c
        for c in final_result.get("citations", [])
        if "citation_id" in c
    }

    # Xây risk items, lọc bỏ None (clause không tìm thấy)
    raw_risks: list[dict[str, Any]] = final_result.get("risks", [])
    risk_items: list[RiskItem] = []
    for raw_risk in raw_risks:
        item = _build_risk_item(raw_risk, clause_map, citation_map, clause_order_map)
        if item is not None:
            risk_items.append(item)

    # Sắp xếp theo thứ tự xuất hiện trong văn bản
    risk_items.sort(key=lambda r: r.clause_start_char)

    no_risk_message: str | None = None
    if not risk_items:
        no_risk_message = NO_RISK_MESSAGE

    return ReportModel(
        title="Phân tích rủi ro hợp đồng lao động",
        general_info=general_info,
        risks=risk_items,
        no_risk_message=no_risk_message,
        disclaimer=disclaimer,
        data_notice=data_notice,
    )

