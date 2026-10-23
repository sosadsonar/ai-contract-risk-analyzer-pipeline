"""
risk_assembler.py
-----------------
Ghép dữ liệu clause từ stage trước + câu trả lời của LLM (risk_output_v2) + citation đã resolve
thành file đầy đủ `risk_merged_v1` cho backend. Hàm thuần: không gọi LLM, không đổi input,
không import api/ hay session/ (AI_CONTEXT §8).

Nguồn của từng trường trong output:
- clause_id, clause_number, start_char, end_char, original_text, clause_labels: stage trước
  (canonical). LLM không bao giờ cung cấp span hay quote (INV-01, INV-05).
- risk_labels, evidence_status, citation_ids, explanation: câu trả lời LLM.
- risk_basis = [{label, basis_type}], một-một với risk_labels: backend dựng từ `basis_type`
  (LLM trả, một giá trị cho cả clause) và risk_labels, sau khi kiểm (nhãn, basis_type, vai trò)
  theo bảng taxonomy. Đây là field sản phẩm theo SRS 4.1 / TDD 6.3.
- severity: KHÔNG lấy từ LLM (schema không có trường này). Assembler tra bảng taxonomy:
  SUPPORTED lấy mức cao nhất trong các risk_labels hợp lệ cho vai trò, INSUFFICIENT_EVIDENCE
  là null (INV-06).
- session_id, role, citations, version pin (model_id, prompt_version, risk_taxonomy_version,
  severity_rubric_version): backend qua AssemblerContext. Các version pin KHÔNG lấy từ LLM.

Xử lý theo bảng taxonomy: nếu (risk_label, basis_type, vai trò) rơi vào ô '-' thì nhãn đó bị
gỡ. Hết nhãn thì clause bị loại khỏi `clauses` (không phải rủi ro của vai trò này, gắn
need_review trong diagnostics) thay vì xuất một rủi ro mâu thuẫn với taxonomy.

Input clause upstream (segmentation_v1 join clause_output_v3):
  {"clause_id": "cl_0001", "clause_number": "7.2", "start_char": 1200, "end_char": 1287,
   "original_text": "...", "clause_labels": ["WORKING_CONDITIONS"]}
  Chấp nhận thêm dạng "span": {"start_char", "end_char"}; output luôn là start_char/end_char
  phẳng như entity Clause và API Get Result (TDD §5, §6.3). Offset = Unicode code point,
  end_char exclusive (INV-04).

Output `merged` (risk_merged_v1), không chứa trường dev/eval:
  {"schema_version": "risk_merged_v1", "session_id", "role", "clause_stage": {...},
   "risk_taxonomy_version", "severity_rubric_version", "model_id", "prompt_version",
   "citations": [...chỉ các citation được dùng...],
   "clauses": [{clause_id, clause_number, start_char, end_char, original_text, clause_labels,
                risk_labels, risk_basis, severity, explanation, evidence_status,
                citation_ids}]}
`clauses` theo thứ tự xuất hiện trong hợp đồng. Không có rủi ro thì `clauses` rỗng.

Output `diagnostics` chỉ cho dev/eval/log, KHÔNG đưa vào response sản phẩm (không chứa text):
  {"need_review": [{clause_id, labels, basis_type}], "labels_dropped": [...]}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.enums import BasisType, EvidenceStatus, Role
from app.risk.taxonomy import (
    RISK_TAXONOMY_VERSION,
    SEVERITY_RUBRIC_VERSION,
    invalid_labels_for_role,
    severity_for_labels,
)

AI_SCHEMA_VERSION = "risk_output_v2"
MERGED_SCHEMA_VERSION = "risk_merged_v1"

_REQUIRED_UPSTREAM = ("clause_id", "original_text", "clause_labels")
_REQUIRED_AI_ITEM = (
    "clause_id",
    "basis_type",
    "risk_labels",
    "explanation",
    "evidence_status",
    "citation_ids",
)


class RiskAssemblerError(Exception):
    """Input không hợp lệ để ghép. Orchestrator ánh xạ thành INTERNAL_ERROR / AI_OUTPUT_INVALID."""


@dataclass(frozen=True)
class AssemblerContext:
    """Metadata do backend cung cấp khi ghép."""

    session_id: str
    role: str  # "EMPLOYEE" | "EMPLOYER"
    clause_stage: dict[str, Any]  # version pin / metadata của stage clause classification
    citations: list[dict[str, Any]]  # citation object đã resolve; mỗi cái có "citation_id"
    model_id: str
    prompt_version: str
    risk_taxonomy_version: str = RISK_TAXONOMY_VERSION
    severity_rubric_version: str = SEVERITY_RUBRIC_VERSION


@dataclass(frozen=True)
class AssemblyResult:
    merged: dict[str, Any]
    diagnostics: dict[str, Any]


def _upstream_span(clause: dict[str, Any]) -> tuple[int, int]:
    span = clause.get("span")
    start = span.get("start_char") if isinstance(span, dict) else clause.get("start_char")
    end = span.get("end_char") if isinstance(span, dict) else clause.get("end_char")
    if not (isinstance(start, int) and isinstance(end, int) and 0 <= start < end):
        raise RiskAssemblerError(
            f"clause '{clause.get('clause_id')}' thiếu hoặc sai start/end_char"
        )
    return start, end


def _check_upstream(
    upstream_clauses: list[dict[str, Any]], canonical_text: str | None
) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for clause in upstream_clauses:
        for key in _REQUIRED_UPSTREAM:
            if key not in clause:
                raise RiskAssemblerError(
                    f"upstream clause thiếu trường '{key}': {clause.get('clause_id')}"
                )
        cid = clause["clause_id"]
        if cid in by_id:
            raise RiskAssemblerError(f"clause_id '{cid}' bị trùng trong upstream_clauses")
        start, end = _upstream_span(clause)
        if canonical_text is not None and canonical_text[start:end] != clause["original_text"]:
            raise RiskAssemblerError(
                f"clause '{cid}': canonical_text[start:end] != original_text (INV-03)"
            )
        by_id[cid] = clause
    return by_id


def _check_ai_item(item: dict[str, Any], citation_ids_known: set[str]) -> None:
    for key in _REQUIRED_AI_ITEM:
        if key not in item:
            raise RiskAssemblerError(f"AI item thiếu trường '{key}': {item.get('clause_id')}")
    cid = item["clause_id"]
    if item["basis_type"] not in {b.value for b in BasisType}:
        raise RiskAssemblerError(f"clause '{cid}': basis_type không hợp lệ: {item['basis_type']!r}")
    labels = item["risk_labels"]
    if not isinstance(labels, list) or not labels or len(set(labels)) != len(labels):
        raise RiskAssemblerError(
            f"clause '{cid}': risk_labels phải là list không rỗng, không trùng"
        )
    if not isinstance(item["explanation"], str) or not item["explanation"].strip():
        raise RiskAssemblerError(f"clause '{cid}': explanation rỗng")
    status, cites = item["evidence_status"], item["citation_ids"]
    if status == EvidenceStatus.SUPPORTED.value:
        if not cites:
            raise RiskAssemblerError(f"clause '{cid}': SUPPORTED cần citation_ids (INV-06)")
    elif status == EvidenceStatus.INSUFFICIENT_EVIDENCE.value:
        if cites:
            raise RiskAssemblerError(
                f"clause '{cid}': INSUFFICIENT_EVIDENCE cần citation_ids=[]"
            )
    else:
        raise RiskAssemblerError(f"clause '{cid}': evidence_status không hợp lệ: {status!r}")
    missing = [c for c in cites if c not in citation_ids_known]
    if missing:
        raise RiskAssemblerError(
            f"clause '{cid}': citation chưa resolve trong ctx.citations: {missing}"
        )


def assemble_risk_output(
    upstream_clauses: list[dict[str, Any]],
    ai_response: dict[str, Any],
    ctx: AssemblerContext,
    canonical_text: str | None = None,
) -> AssemblyResult:
    """Ghép upstream + câu trả lời LLM thành risk_merged_v1 (+ diagnostics cho dev/eval).

    Raises:
        RiskAssemblerError: role sai, schema_version sai, clause_id lạ hoặc trùng, item thiếu
            trường hoặc vi phạm SUPPORTED/INSUFFICIENT_EVIDENCE, citation chưa resolve, nhãn
            ngoài taxonomy, hoặc (khi có canonical_text) vi phạm
            canonical_text[start:end] == original_text.
    """
    if ctx.role not in {r.value for r in Role}:
        raise RiskAssemblerError(f"role không hợp lệ: {ctx.role!r}")
    got_version = ai_response.get("schema_version")
    if got_version != AI_SCHEMA_VERSION:
        raise RiskAssemblerError(
            f"AI response có schema_version={got_version!r}, cần '{AI_SCHEMA_VERSION}'"
        )

    upstream = _check_upstream(upstream_clauses, canonical_text)
    order = {c["clause_id"]: i for i, c in enumerate(upstream_clauses)}
    resolved = {c["citation_id"]: c for c in ctx.citations}

    items: dict[str, dict[str, Any]] = {}
    for item in ai_response.get("items", []):
        _check_ai_item(item, set(resolved))
        cid = item["clause_id"]
        if cid in items:
            raise RiskAssemblerError(f"clause_id '{cid}' xuất hiện nhiều hơn một lần trong items[]")
        if cid not in upstream:
            raise RiskAssemblerError(
                f"clause_id '{cid}' có trong AI response nhưng không có trong upstream "
                "(model bịa clause_id hoặc batch không khớp)"
            )
        items[cid] = item

    diagnostics: dict[str, list[dict[str, Any]]] = {"need_review": [], "labels_dropped": []}
    merged_clauses: list[dict[str, Any]] = []
    used_citations: set[str] = set()

    for cid in sorted(items, key=order.__getitem__):
        item, clause = items[cid], upstream[cid]
        basis = item["basis_type"]
        try:
            bad = invalid_labels_for_role(item["risk_labels"], basis, ctx.role)
        except ValueError as exc:  # nhãn ngoài taxonomy
            raise RiskAssemblerError(f"clause '{cid}': {exc}") from exc
        labels = [x for x in item["risk_labels"] if x not in bad]
        if bad:
            diagnostics["labels_dropped"].append(
                {"clause_id": cid, "labels": bad, "basis_type": basis}
            )
        if not labels:
            diagnostics["need_review"].append(
                {"clause_id": cid, "labels": bad, "basis_type": basis}
            )
            continue

        severity = None
        if item["evidence_status"] == EvidenceStatus.SUPPORTED.value:
            table = severity_for_labels(labels, basis, ctx.role)  # còn >= 1 nhãn hợp lệ
            severity = table.value if table is not None else None

        start, end = _upstream_span(clause)
        used_citations.update(item["citation_ids"])
        merged_clauses.append(
            {
                "clause_id": cid,
                "clause_number": clause.get("clause_number"),
                "start_char": start,
                "end_char": end,
                "original_text": clause["original_text"],
                "clause_labels": list(clause["clause_labels"]),
                "risk_labels": labels,
                "risk_basis": [{"label": x, "basis_type": basis} for x in labels],
                "severity": severity,
                "explanation": item["explanation"],
                "evidence_status": item["evidence_status"],
                "citation_ids": list(item["citation_ids"]),
            }
        )

    merged = {
        "schema_version": MERGED_SCHEMA_VERSION,
        "session_id": ctx.session_id,
        "role": ctx.role,
        "clause_stage": ctx.clause_stage,
        "risk_taxonomy_version": ctx.risk_taxonomy_version,
        "severity_rubric_version": ctx.severity_rubric_version,
        "model_id": ctx.model_id,
        "prompt_version": ctx.prompt_version,
        "citations": [c for c in ctx.citations if c["citation_id"] in used_citations],
        "clauses": merged_clauses,
    }
    return AssemblyResult(merged=merged, diagnostics=diagnostics)
