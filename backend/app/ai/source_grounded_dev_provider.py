"""Dev-only local provider backed by frozen source-text baselines.

This is a diagnostic adapter for the real runner interface. It is not the
product M2 model and must never be selected by ``make_provider``.
"""

from __future__ import annotations

import json

from app.ai.provider import LLMResponse
from app.clause.dev_tfidf_baseline import DevTfidfBaseline, add_source_working_conditions
from app.risk.dev_injection_candidate import _DOCUMENT
from app.risk.dev_m2_baseline import detect_dev_m2_risks

_CITATIONS = {
    "DISCIPLINE_OBLIGATION": "BLLD2019:art17:cl3",
    "UNILATERAL_CHANGE": "BLLD2019:art21:cl1:ptc",
    "BONUS_BENEFITS": "BLLD2019:art21:cl1:ptđ",
    "WORKING_HOURS_OVERTIME": "BLLD2019:art21:cl1:ptg",
    "REST_AND_LEAVE": "BLLD2019:art21:cl1:ptg",
}
_EXPLANATIONS = {
    "DEPOSIT_DOCUMENT_HELD": (
        "Dấu hiệu giữ giấy tờ gốc hoặc yêu cầu bảo đảm khi thực hiện hợp đồng; "
        "cần người rà nguồn và điều luật."
    ),
    "DISCIPLINE_OBLIGATION": (
        "Dấu hiệu buộc tiếp tục làm việc để trả nợ; cần người rà nguồn và điều luật."
    ),
    "UNILATERAL_CHANGE": "Điều khoản có dấu hiệu cho phép thay đổi công việc hoặc điều kiện làm việc một chiều.",
    "BONUS_BENEFITS": "Điều khoản để mức thưởng hoặc phụ cấp phụ thuộc quy định mở của công ty.",
    "WORKING_HOURS_OVERTIME": "Điều khoản để việc làm thêm giờ phụ thuộc yêu cầu mở của công ty.",
    "REST_AND_LEAVE": "Điều khoản để việc nghỉ bù phụ thuộc quyết định mở của công ty.",
}


class SourceGroundedDevProvider:
    """Use local predicted labels and source-only Dev detectors on masked input."""

    def __init__(self, clause_model: DevTfidfBaseline):
        self.clause_model = clause_model
        self.request_count = 0

    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s):
        request = json.loads(messages[1]["content"])
        self.request_count += 1
        if request["schema_version"] == "clause_classification_request_v1":
            texts = [item["masked_text"] for item in request["items"]]
            labels = add_source_working_conditions(texts, self.clause_model.predict(texts))
            data = {"items": [
                {"clause_id": item["clause_id"], "clause_labels": list(row)}
                for item, row in zip(request["items"], labels)
            ]}
        elif request["schema_version"] == "risk_analysis_request_v2":
            role = request["role"]
            items = []
            for item in request["items"]:
                matches = [row for row in detect_dev_m2_risks(item["masked_text"])
                           if row[0] == role]
                if not matches:
                    continue
                # risk_output_v2 permits one item per clause, but up to three
                # labels sharing one basis type can be retained in that item.
                matches.sort(key=lambda row: (row[2] != "LEGAL_VIOLATION", row[1]))
                basis = matches[0][2]
                labels = list(dict.fromkeys(
                    row[1] for row in matches if row[2] == basis))[:3]
                desired = []
                for label in labels:
                    if label == "DEPOSIT_DOCUMENT_HELD":
                        citation = ("BLLD2019:art17:cl1"
                                    if _DOCUMENT.search(item["masked_text"].casefold())
                                    else "BLLD2019:art17:cl2")
                    else:
                        citation = _CITATIONS[label]
                    if citation not in desired:
                        desired.append(citation)
                citations = (desired if all(cid in item["candidate_ids"] for cid in desired)
                             else [])
                items.append({
                    "clause_id": item["clause_id"], "basis_type": basis,
                    "risk_labels": labels, "citation_ids": citations,
                    "evidence_status": "SUPPORTED" if citations else "INSUFFICIENT_EVIDENCE",
                    "explanation": " ".join(_EXPLANATIONS[label] for label in labels),
                })
            data = {"schema_version": "risk_output_v2", "items": items}
        else:
            raise ValueError("unsupported Dev provider request schema")
        return LLMResponse(data, model_id)
