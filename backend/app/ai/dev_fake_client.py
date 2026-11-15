"""DevFakeClient — provider tất định, không mạng, CHỈ `APP_ENV=dev`/test (X-19).

Mục đích: chạy được toàn pipeline qua HTTP (smoke, ghép frontend N5, CI) khi chưa có Gemini key. Không phải
mô hình phân loại: luật từ khóa thô, KHÔNG dùng để đo M2/M7 hay báo cáo chất lượng.
  * LLM #1 (`clause_analysis_request_*`): nhãn theo từ khóa đầu tiên khớp, không khớp ⇒ OTHER.
  * LLM #2 (`risk_analysis_request_*`): chỉ báo rủi ro cho vài mẫu từ khóa rõ (giữ bản chính giấy tờ, đặt cọc,
    thử việc), dùng candidate đầu tiên nếu có (SUPPORTED) hoặc INSUFFICIENT_EVIDENCE.
"""

from __future__ import annotations

import json

from app.ai.provider import LLMResponse

FAKE_MODEL_ID = "dev-fake-provider"

_CLAUSE_RULES = (
    ("thử việc", "CONTRACT_TERM"), ("thời hạn", "CONTRACT_TERM"), ("lương", "COMPENSATION_BENEFITS"),
    ("phụ cấp", "COMPENSATION_BENEFITS"), ("giờ làm", "WORKING_TIME"), ("làm thêm", "WORKING_TIME"),
    ("nghỉ phép", "LEAVE"), ("nghỉ lễ", "LEAVE"), ("bảo hiểm", "INSURANCE_SAFETY"), ("đào tạo", "TRAINING"),
    ("chấm dứt", "TERMINATION"), ("kỷ luật", "EMPLOYEE_OBLIGATIONS_DISCIPLINE"),
    ("bản chính", "EMPLOYEE_OBLIGATIONS_DISCIPLINE"), ("công việc", "JOB_INFO"), ("chức danh", "JOB_INFO"),
)
_RISK_RULES = (
    ("bản chính", "DEPOSIT_DOCUMENT_HELD", "LEGAL_VIOLATION",
     "Điều khoản cho phép giữ bản chính giấy tờ của người lao động, trái quy định cấm trong căn cứ."),
    ("đặt cọc", "DEPOSIT_DOCUMENT_HELD", "LEGAL_VIOLATION",
     "Điều khoản yêu cầu người lao động đặt cọc, trái quy định cấm trong căn cứ."),
    ("thử việc", "PROBATION", "AMBIGUOUS",
     "Thời gian hoặc mức lương thử việc cần đối chiếu với loại công việc để xác định mức áp dụng."),
)


class DevFakeClient:
    def __init__(self, *, app_env: str) -> None:
        if app_env != "dev":
            raise ValueError("DevFakeClient chỉ dùng trong APP_ENV=dev")

    def __repr__(self) -> str:
        return "DevFakeClient()"

    async def generate_structured(self, *, model_id, messages, response_schema, timeout_s) -> LLMResponse:
        request = json.loads(messages[1]["content"])
        if str(request.get("schema_version", "")).startswith("risk_analysis_request"):
            data = self._risk(request)
        else:
            data = self._classify(request)
        return LLMResponse(data=data, model_id=FAKE_MODEL_ID, in_tokens=0, out_tokens=0, usage_known=False)

    @staticmethod
    def _classify(request: dict) -> dict:
        items = []
        for it in request["items"]:
            text = it["masked_text"].lower()
            label = next((lab for key, lab in _CLAUSE_RULES if key in text), "OTHER")
            items.append({"clause_id": it["clause_id"], "clause_labels": [label]})
        return {"items": items}

    @staticmethod
    def _risk(request: dict) -> dict:
        items = []
        for it in request["items"]:
            text = it["masked_text"].lower()
            for key, label, basis, why in _RISK_RULES:
                if key in text:
                    cites = list(it.get("candidate_ids", []))[:1]
                    items.append({"clause_id": it["clause_id"], "basis_type": basis, "risk_labels": [label],
                                  "citation_ids": cites,
                                  "evidence_status": "SUPPORTED" if cites else "INSUFFICIENT_EVIDENCE",
                                  "explanation": why})
                    break
        return {"schema_version": "risk_output_v2", "items": items}
