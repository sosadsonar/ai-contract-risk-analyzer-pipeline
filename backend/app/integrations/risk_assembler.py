"""
risk_assembler.py
-----------------
Gộp upstream clause data + AI delta response (risk_output_v2) thành merged output.

Quy tắc:
- Chỉ giữ clause CÓ trong AI items[] (clause không rủi ro bị loại bỏ).
- risk_basis lấy thẳng từ AI response (AI xác định bước 1 của quy trình gán nhãn).
- Backend validate (risk_label, risk_basis, role) không được ánh xạ sang '-' trong taxonomy.
- Backend điền: session_id, role, clause_stage, citations (đã resolve).
- Output: dict hợp lệ theo structure risk_merged_v1.

Input upstream clause data format (segmentation_v1 + clause_output_v3 đã join):
{
  "clauses": [
    {
      "clause_id": "cl_0001",
      "clause_number": "7.2",
      "span": {"start_char": 1200, "end_char": 1287},
      "original_text": "...",
      "clause_labels": ["WORKING_CONDITIONS"]
    },
    ...
  ]
}

Input AI response format (risk_output_v2):
{
  "schema_version": "risk_output_v2",
  "model_id": "...",
  "prompt_version": "...",
  "risk_taxonomy_version": "...",
  "severity_rubric_version": "...",
  "items": [
    {
      "clause_id": "cl_0001",
      "risk_basis": "LEGAL_VIOLATION",
      "risk_labels": ["DEPOSIT_DOCUMENT_HELD"],
      "severity": "HIGH",
      "explanation": "...",
      "evidence_status": "SUPPORTED",
      "citation_ids": ["BLLD2019:art17:k1"]
    }
  ]
}

Output (risk_merged_v1) structure:
{
  "schema_version": "risk_merged_v1",
  "session_id": "...",          # điền bởi caller
  "role": "EMPLOYEE",           # điền bởi caller
  "clause_stage": {...},        # điền bởi caller (metadata stage trước)
  "risk_taxonomy_version": "...",
  "severity_rubric_version": "...",
  "model_id": "...",
  "prompt_version": "...",
  "citations": [...],           # điền bởi caller (resolved citation objects)
  "clauses": [                  # chỉ clause có rủi ro
    {
      "clause_id": "cl_0001",
      "clause_number": "7.2",
      "span": {"start_char": 1200, "end_char": 1287},
      "original_text": "...",
      "clause_labels": ["WORKING_CONDITIONS"],
      "risk_basis": "LEGAL_VIOLATION",    # từ AI response
      "risk_labels": ["DEPOSIT_DOCUMENT_HELD"],
      "severity": "HIGH",
      "explanation": "...",
      "evidence_status": "SUPPORTED",
      "citation_ids": ["BLLD2019:art17:k1"]
    }
  ]
}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Bảng validate (risk_label, risk_basis, role) từ RISK_TAXONOMY_v0.1.md.
# Key: (risk_label, risk_basis). Value: {role: severity | None}.
# None = '-' trong bảng = không phải rủi ro cho vai trò này → "need review".
# ---------------------------------------------------------------------------
_TAXONOMY_SEVERITY: dict[tuple[str, str], dict[str, str | None]] = {
    # (risk_label, risk_basis): {"EMPLOYEE": severity|None, "EMPLOYER": severity|None}
    ("CONTRACT_TERM_TYPE",          "LEGAL_VIOLATION"): {"EMPLOYEE": "MEDIUM", "EMPLOYER": "HIGH"},
    ("CONTRACT_TERM_TYPE",          "UNFAVORABLE"):     {"EMPLOYEE": "LOW",    "EMPLOYER": "LOW"},
    ("CONTRACT_TERM_TYPE",          "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("PROBATION",                   "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("PROBATION",                   "UNFAVORABLE"):     {"EMPLOYEE": "LOW",    "EMPLOYER": None},
    ("PROBATION",                   "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("WAGE_AMOUNT_COMPONENTS",      "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("WAGE_AMOUNT_COMPONENTS",      "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("WAGE_AMOUNT_COMPONENTS",      "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("BONUS_BENEFITS",              "LEGAL_VIOLATION"): {"EMPLOYEE": "LOW",    "EMPLOYER": "HIGH"},
    ("BONUS_BENEFITS",              "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("BONUS_BENEFITS",              "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "LOW"},
    ("PAYMENT_TIMING_METHOD",       "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("PAYMENT_TIMING_METHOD",       "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": None},
    ("PAYMENT_TIMING_METHOD",       "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("WORKING_HOURS_OVERTIME",      "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("WORKING_HOURS_OVERTIME",      "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": "LOW"},
    ("WORKING_HOURS_OVERTIME",      "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "LOW"},
    ("REST_AND_LEAVE",              "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("REST_AND_LEAVE",              "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": "LOW"},
    ("REST_AND_LEAVE",              "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "LOW"},
    ("SOCIAL_INSURANCE",            "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("SOCIAL_INSURANCE",            "UNFAVORABLE"):     {"EMPLOYEE": None,     "EMPLOYER": None},
    ("SOCIAL_INSURANCE",            "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("OSH_OBLIGATION",              "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("OSH_OBLIGATION",              "UNFAVORABLE"):     {"EMPLOYEE": None,     "EMPLOYER": None},
    ("OSH_OBLIGATION",              "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("UNILATERAL_CHANGE",           "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "MEDIUM"},
    ("UNILATERAL_CHANGE",           "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": "LOW"},
    ("UNILATERAL_CHANGE",           "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "LOW"},
    ("PENALTY_DEDUCTION_DAMAGES",   "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("PENALTY_DEDUCTION_DAMAGES",   "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": "LOW"},
    ("PENALTY_DEDUCTION_DAMAGES",   "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("DISCIPLINE_OBLIGATION",       "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("DISCIPLINE_OBLIGATION",       "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": "LOW"},
    ("DISCIPLINE_OBLIGATION",       "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("POST_EMPLOYMENT_RESTRICTION", "LEGAL_VIOLATION"): {"EMPLOYEE": "MEDIUM", "EMPLOYER": None},
    ("POST_EMPLOYMENT_RESTRICTION", "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": "LOW"},
    ("POST_EMPLOYMENT_RESTRICTION", "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("DEPOSIT_DOCUMENT_HELD",       "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("DEPOSIT_DOCUMENT_HELD",       "UNFAVORABLE"):     {"EMPLOYEE": None,     "EMPLOYER": None},
    ("DEPOSIT_DOCUMENT_HELD",       "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("DISCRIMINATION_PROTECTED_GROUPS", "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("DISCRIMINATION_PROTECTED_GROUPS", "UNFAVORABLE"):     {"EMPLOYEE": None,     "EMPLOYER": None},
    ("DISCRIMINATION_PROTECTED_GROUPS", "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("TRAINING_COMMITMENT",         "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("TRAINING_COMMITMENT",         "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": "LOW"},
    ("TRAINING_COMMITMENT",         "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("TERMINATION_GROUNDS_NOTICE",  "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("TERMINATION_GROUNDS_NOTICE",  "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("TERMINATION_GROUNDS_NOTICE",  "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("TERMINATION_SETTLEMENT",      "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("TERMINATION_SETTLEMENT",      "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": "LOW"},
    ("TERMINATION_SETTLEMENT",      "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("WAIVER_RIGHTS_DISPUTE",       "LEGAL_VIOLATION"): {"EMPLOYEE": "HIGH",   "EMPLOYER": "HIGH"},
    ("WAIVER_RIGHTS_DISPUTE",       "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": None},
    ("WAIVER_RIGHTS_DISPUTE",       "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "LOW"},
    ("PERSONAL_DATA_PRIVACY",       "LEGAL_VIOLATION"): {"EMPLOYEE": "MEDIUM", "EMPLOYER": "HIGH"},
    ("PERSONAL_DATA_PRIVACY",       "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": None},
    ("PERSONAL_DATA_PRIVACY",       "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("CONTRACT_FORM_RULES",         "LEGAL_VIOLATION"): {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
    ("CONTRACT_FORM_RULES",         "UNFAVORABLE"):     {"EMPLOYEE": "MEDIUM", "EMPLOYER": None},
    ("CONTRACT_FORM_RULES",         "AMBIGUOUS"):       {"EMPLOYEE": "MEDIUM", "EMPLOYER": "MEDIUM"},
}


def validate_risk_basis_labels(
    risk_labels: list[str],
    risk_basis: str,
    role: str,
) -> list[str]:
    """
    Kiểm tra từng (risk_label, risk_basis, role) trong bảng taxonomy.
    Trả về list các label có severity='-' (None) → cần flag "need review".
    Nếu (label, basis) không có trong bảng → RiskAssemblerError (unknown mapping).
    """
    invalid: list[str] = []
    for label in risk_labels:
        key = (label, risk_basis)
        row = _TAXONOMY_SEVERITY.get(key)
        if row is None:
            raise RiskAssemblerError(
                f"Không tìm thấy ({label}, {risk_basis}) trong _TAXONOMY_SEVERITY. "
                "Kiểm tra taxonomy version hoặc cập nhật bảng."
            )
        severity_for_role = row.get(role)
        if severity_for_role is None:
            invalid.append(label)
    return invalid


@dataclass
class AssemblerContext:
    """Metadata mà caller (orchestrator/backend) cung cấp khi gộp."""
    session_id: str
    role: str                        # "EMPLOYEE" | "EMPLOYER"
    clause_stage: dict[str, Any]     # metadata của stage clause classification
    citations: list[dict[str, Any]]  # citation objects đã resolve từ kho luật


class RiskAssemblerError(Exception):
    """Raised khi input không hợp lệ để merge."""


def assemble_risk_output(
    upstream_clauses: list[dict[str, Any]],
    ai_response: dict[str, Any],
    ctx: AssemblerContext,
) -> dict[str, Any]:
    """
    Gộp upstream clause data + AI delta response thành risk_merged_v1.

    Args:
        upstream_clauses: list clause từ stage trước (segmentation + classification đã join).
                          Mỗi item cần: clause_id, clause_number, span, original_text, clause_labels.
        ai_response:      dict parse từ AI response theo schema risk_output_v2.
        ctx:              metadata backend cung cấp (session_id, role, clause_stage, citations).

    Returns:
        dict theo structure risk_merged_v1.

    Raises:
        RiskAssemblerError: khi schema_version sai, clause_id không tồn tại ở upstream,
                            clause_id bị duplicate, hoặc (risk_label, risk_basis) không có
                            trong bảng taxonomy.
    """
    # Validate schema_version
    schema_ver = ai_response.get("schema_version")
    if schema_ver != "risk_output_v2":
        raise RiskAssemblerError(
            f"AI response có schema_version='{schema_ver}', expected 'risk_output_v2'"
        )

    # Build lookup upstream theo clause_id
    upstream_map: dict[str, dict[str, Any]] = {
        cl["clause_id"]: cl for cl in upstream_clauses
    }

    ai_items: list[dict[str, Any]] = ai_response.get("items", [])

    # Kiểm tra duplicate clause_id trong AI response
    seen_ids: set[str] = set()
    for item in ai_items:
        cid = item["clause_id"]
        if cid in seen_ids:
            raise RiskAssemblerError(
                f"clause_id '{cid}' xuất hiện nhiều hơn 1 lần trong AI response items[]"
            )
        seen_ids.add(cid)

    merged_clauses: list[dict[str, Any]] = []
    for item in ai_items:
        cid = item["clause_id"]

        # Clause phải tồn tại ở upstream
        upstream_cl = upstream_map.get(cid)
        if upstream_cl is None:
            raise RiskAssemblerError(
                f"clause_id '{cid}' có trong AI response nhưng không có trong upstream_clauses. "
                "Có thể AI hallucinate clause_id hoặc input batch không khớp."
            )

        risk_labels: list[str] = item["risk_labels"]
        risk_basis: str = item["risk_basis"]   # AI xác định ở bước 1

        # Validate (risk_label, risk_basis, role) trong taxonomy
        # → trả về labels với severity '-': cần flag "need review" ở caller
        invalid_labels = validate_risk_basis_labels(risk_labels, risk_basis, ctx.role)
        if invalid_labels:
            # Không raise hard error ở đây; caller quyết định flag hay reject
            # Gắn vào output để caller xử lý
            item["_need_review"] = invalid_labels

        merged_cl: dict[str, Any] = {
            # --- Upstream fields ---
            "clause_id":     upstream_cl["clause_id"],
            "clause_number": upstream_cl.get("clause_number"),
            "span":          upstream_cl["span"],
            "original_text": upstream_cl["original_text"],
            "clause_labels": upstream_cl["clause_labels"],
            # --- AI fields (từ risk_output_v2) ---
            "risk_basis":       risk_basis,
            "risk_labels":      risk_labels,
            "severity":         item["severity"],
            "explanation":      item["explanation"],
            "evidence_status":  item["evidence_status"],
            "citation_ids":     item["citation_ids"],
        }

        # Đính kèm need_review nếu có
        if "_need_review" in item:
            merged_cl["_need_review"] = item["_need_review"]

        merged_clauses.append(merged_cl)

    return {
        "schema_version":          "risk_merged_v1",
        "session_id":              ctx.session_id,
        "role":                    ctx.role,
        "clause_stage":            ctx.clause_stage,
        "risk_taxonomy_version":   ai_response["risk_taxonomy_version"],
        "severity_rubric_version": ai_response["severity_rubric_version"],
        "model_id":                ai_response["model_id"],
        "prompt_version":          ai_response["prompt_version"],
        "citations":               ctx.citations,
        "clauses":                 merged_clauses,
    }
