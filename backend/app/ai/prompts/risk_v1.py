"""Prompt Risk Analysis (LLM #2) — SINH từ taxonomy, version pin (TDD §15, Phụ lục C.2, C-15 khung).

Hợp đồng gửi đi (`risk_analysis_request_v2`, TDD §15.1): role, risk_taxonomy (nhãn + định nghĩa),
basis_types, candidates (catalog dedupe theo ID), items[{clause_id, masked_text, clause_labels,
candidate_ids, related_clauses}]. KHÔNG có canonical/original, start/end, structure (INV-04).
Phản hồi model phải trả: `risk_output_v2` (TDD §15.2). Model KHÔNG trả severity, role, span, quote,
model_id, prompt_version, các version pin — backend đóng dấu (INV-05, INV-06).

Nhãn lấy từ `app.risk.taxonomy.RISK_LABELS` (nguồn duy nhất, DEC-20). Câu định nghĩa nhãn đặt ở đây vì
`taxonomy.py` chỉ giữ nhãn + bảng severity; `tests/unit/test_risk_prompt.py` buộc khóa của
RISK_LABEL_DEFINITIONS == RISK_LABELS (đúng thứ tự) nên thêm/xóa nhãn mà quên định nghĩa là test đỏ.
Định nghĩa chép từ cột "Gom từ" của docs/RISK_TAXONOMY_v0.1.md, không chứa số Điều/tên luật.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from app.core.enums import BasisType
from app.risk.taxonomy import (
    MAX_RISK_LABELS_PER_CLAUSE,
    RISK_LABELS,
    RISK_TAXONOMY_VERSION,
)

RISK_PROMPT_VERSION = "risk_prompt_v1"
REQUEST_SCHEMA_VERSION = "risk_analysis_request_v2"
OUTPUT_SCHEMA_VERSION = "risk_output_v2"

RISK_LABEL_DEFINITIONS: dict[str, str] = {
    "CONTRACT_TERM_TYPE": "Loại và thời hạn hợp đồng: quá 36 tháng, ký nối tiếp quá số lần cho phép, tự động hết hạn hoặc gia hạn.",
    "PROBATION": "Thử việc: thời gian thử việc, mức lương thử việc thấp hơn mức luật cho phép, phạt khi hủy thỏa thuận thử việc.",
    "WAGE_AMOUNT_COMPONENTS": "Mức lương và cấu phần: lương dưới mức tối thiểu vùng, gộp phụ cấp vào lương, tiền làm thêm giờ thấp hơn luật, mơ hồ lương gross hay net và thuế.",
    "BONUS_BENEFITS": "Thưởng, phụ cấp, phúc lợi: do công ty toàn quyền quyết định mà không công khai quy chế, hoặc khoản chi cố định đã cam kết.",
    "PAYMENT_TIMING_METHOD": "Kỳ hạn và phương thức trả lương; lương phụ thuộc điều kiện.",
    "WORKING_HOURS_OVERTIME": "Giờ làm việc thường, làm thêm giờ bắt buộc, vượt trần giờ làm thêm.",
    "REST_AND_LEAVE": "Nghỉ giữa ca, nghỉ hằng tuần, phép năm, nghỉ lễ, nghỉ việc riêng, thanh toán ngày phép chưa nghỉ.",
    "SOCIAL_INSURANCE": "Bảo hiểm xã hội, y tế, thất nghiệp: không đóng hoặc đóng thấp, đẩy phần của công ty sang người lao động.",
    "OSH_OBLIGATION": "An toàn vệ sinh lao động: đẩy chi phí bảo hộ, khám sức khỏe, tai nạn lao động sang người lao động.",
    "UNILATERAL_CHANGE": "Đơn phương đổi lương, công việc, địa điểm, ca làm; sửa hợp đồng; mô tả công việc để mở.",
    "PENALTY_DEDUCTION_DAMAGES": "Phạt tiền, khấu trừ lương, bồi thường vượt luật, phạt khi nghỉ việc.",
    "DISCIPLINE_OBLIGATION": "Hình thức và căn cứ kỷ luật, tiêu chí đánh giá, nghĩa vụ áp đặt một chiều.",
    "POST_EMPLOYMENT_RESTRICTION": "Bảo mật, không cạnh tranh, chuyển giao sở hữu trí tuệ, hạn chế sau khi nghỉ việc.",
    "DEPOSIT_DOCUMENT_HELD": "Đặt cọc, ký quỹ, giữ bản chính giấy tờ của người lao động.",
    "DISCRIMINATION_PROTECTED_GROUPS": "Phân biệt đối xử; cấm kết hôn hoặc mang thai; đối xử bất lợi với nhóm được bảo vệ.",
    "TRAINING_COMMITMENT": "Đào tạo: hoàn trả chi phí, thời gian cam kết, lợi dụng đào tạo để ràng buộc.",
    "TERMINATION_GROUNDS_NOTICE": "Căn cứ chấm dứt hợp đồng của mỗi bên, thời hạn báo trước, điều kiện để người lao động nghỉ.",
    "TERMINATION_SETTLEMENT": "Trợ cấp thôi việc và mất việc, thanh toán cuối cùng, trả giấy tờ, bàn giao.",
    "WAIVER_RIGHTS_DISPUTE": "Buộc người lao động từ bỏ quyền khiếu nại, khởi kiện; cấm hoặc hạn chế tham gia công đoàn; loại trừ thẩm quyền giải quyết tranh chấp.",
    "PERSONAL_DATA_PRIVACY": "Thu thập, chia sẻ, giám sát dữ liệu cá nhân của người lao động.",
    "CONTRACT_FORM_RULES": "Hình thức hợp đồng, số bản giữ, nội quy kèm theo, quyền giải thích của công ty.",
}

# Thứ tự ưu tiên khi thỏa nhiều loại: LV, rồi UF, rồi AM (docs/RISK_TAXONOMY_v0.1.md, "Giới hạn đã biết").
BASIS_TYPE_DEFINITIONS: dict[str, str] = {
    BasisType.LEGAL_VIOLATION.value: "Trái quy định cấm hoặc bắt buộc, hoặc vượt ngưỡng pháp luật rõ ràng trong căn cứ được cung cấp.",
    BasisType.UNFAVORABLE.value: "Không trái luật nhưng bất lợi đáng kể cho vai trò đang phân tích.",
    BasisType.AMBIGUOUS.value: "Câu chữ mơ hồ, thiếu điều kiện hoặc mức cụ thể, có thể dẫn đến tranh chấp.",
}

# Schema cho provider structured output = phần model-facing của risk_output_v2 (enum sinh từ code).
# Ràng buộc chéo (SUPPORTED ⇒ citation không rỗng, v.v.) KHÔNG đưa vào đây vì provider không hỗ trợ
# allOf/if-then; adapter kiểm trong `validate_batch_response`.
RESPONSE_SCHEMA: dict = {
    "type": "object",
    "required": ["schema_version", "items"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "string", "enum": [OUTPUT_SCHEMA_VERSION]},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "clause_id",
                    "basis_type",
                    "risk_labels",
                    "citation_ids",
                    "evidence_status",
                    "explanation",
                ],
                "additionalProperties": False,
                "properties": {
                    "clause_id": {"type": "string"},
                    "basis_type": {"type": "string", "enum": list(BASIS_TYPE_DEFINITIONS)},
                    "risk_labels": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_RISK_LABELS_PER_CLAUSE,
                        "uniqueItems": True,
                        "items": {"type": "string", "enum": list(RISK_LABELS)},
                    },
                    "citation_ids": {"type": "array", "uniqueItems": True, "items": {"type": "string"}},
                    "evidence_status": {"type": "string", "enum": ["SUPPORTED", "INSUFFICIENT_EVIDENCE"]},
                    "explanation": {"type": "string"},
                },
            },
        },
    },
}


def build_system_prompt() -> str:
    """Không chứa role, nhãn hay định nghĩa (các phần đó nằm trong request theo TDD §15.1)."""
    return (
        "Bạn phát hiện rủi ro trong từng điều khoản của hợp đồng lao động Việt Nam, theo góc nhìn của vai trò "
        "trong trường `role` (EMPLOYEE = người lao động, EMPLOYER = người sử dụng lao động).\n"
        "Văn bản đã che thông tin cá nhân bằng placeholder (ví dụ <NAME>___, <PHONE>__): coi là giá trị đã ẩn, "
        "không suy đoán, không nhắc lại placeholder.\n\n"
        "Đầu vào là JSON `risk_analysis_request_v2`. Nhãn rủi ro và định nghĩa nằm ở `risk_taxonomy`; loại căn "
        "cứ nằm ở `basis_types`. Chỉ được dùng đúng các nhãn và loại đó.\n"
        "Chọn MỘT basis_type cho cả điều khoản. Nếu điều khoản thỏa nhiều loại, ưu tiên LEGAL_VIOLATION, rồi "
        "UNFAVORABLE, rồi AMBIGUOUS.\n\n"
        "Quy trình cho mỗi điều khoản: (1) chọn basis_type; (2) chọn risk_labels; "
        "(3) chọn citation_ids; (4) viết explanation.\n"
        "Quy tắc:\n"
        "1. Chỉ phân tích điều khoản hiện có trong `items`; không nêu rủi ro do thiếu điều khoản.\n"
        "2. Chỉ đưa vào kết quả điều khoản CÓ rủi ro cho vai trò đang phân tích. Điều khoản không rủi ro, hoặc có "
        "lợi hơn quy định cho vai trò đó, thì không xuất hiện trong kết quả; không có rủi ro nào thì trả `items` rỗng.\n"
        f"3. risk_labels có 1–{MAX_RISK_LABELS_PER_CLAUSE} nhãn, không lặp; thường chỉ một nhãn, chỉ thêm khi thật sự "
        "có vấn đề thứ hai.\n"
        "4. citation_ids chỉ được lấy từ `candidate_ids` của chính điều khoản đó; nội dung căn cứ tra trong "
        "`candidates`. Không dùng, không nhớ, không viện dẫn điều luật nào ngoài các căn cứ được cung cấp.\n"
        "5. evidence_status = SUPPORTED khi có ít nhất một căn cứ trong candidate_ids làm cơ sở (citation_ids "
        "không rỗng). Khi căn cứ không đủ, dùng INSUFFICIENT_EVIDENCE với citation_ids rỗng; không bịa citation.\n"
        "6. `related_clauses` chỉ là ngữ cảnh về điều kiện, phụ thuộc hoặc mâu thuẫn; kết quả vẫn gắn với "
        "clause_id của điều khoản đang xét.\n"
        "7. explanation: tiếng Việt, trung tính, nêu điều khoản gây rủi ro gì cho vai trò đó và vì sao theo "
        "basis_type. Không lời khuyên hay hành động (không sửa, không thương lượng, không yêu cầu); không nêu mức "
        "độ nghiêm trọng; không trích nguyên văn điều khoản; chỉ nhắc Điều hoặc văn bản luật có trong citation_ids; "
        "khi INSUFFICIENT_EVIDENCE thì không nhắc số điều hay tên văn bản pháp luật.\n"
        "8. Không trả severity, role, vị trí ký tự, trích dẫn nguyên văn, model_id, phiên bản prompt hay taxonomy.\n\n"
        f"Trả JSON đúng schema `{OUTPUT_SCHEMA_VERSION}`: {{schema_version, items:[{{clause_id, basis_type, "
        "risk_labels, citation_ids, evidence_status, explanation}]}}; mỗi clause_id tối đa một lần, chỉ dùng "
        "clause_id có trong đầu vào, không thêm trường khác, không dùng Markdown."
    )


def build_request(
    role: str,
    items: list[dict],
    candidates: Mapping[str, dict],
) -> dict:
    """`items` đã ở dạng dict gửi đi; `candidates` chỉ gồm ID mà ít nhất một item tham chiếu (dedupe)."""
    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "role": role,
        "risk_taxonomy": [{"label": n, "definition": RISK_LABEL_DEFINITIONS[n]} for n in RISK_LABELS],
        "basis_types": [{"type": t, "definition": d} for t, d in BASIS_TYPE_DEFINITIONS.items()],
        "candidates": dict(candidates),
        "items": items,
    }


def build_messages(request: dict) -> list[dict]:
    return [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": json.dumps(request, ensure_ascii=False)},
    ]


def prompt_pin() -> str:
    """Giá trị ghi vào `prompt_version`: đổi khi prompt, định nghĩa nhãn HOẶC định nghĩa basis đổi."""
    material = json.dumps(
        [build_system_prompt(), RISK_LABEL_DEFINITIONS, BASIS_TYPE_DEFINITIONS], ensure_ascii=False, sort_keys=False
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:8]
    return f"{RISK_PROMPT_VERSION}+{RISK_TAXONOMY_VERSION}+{digest}"
