"""Prompt Clause Classification (LLM #1) — SINH TỪ taxonomy, không gõ tay nhãn/định nghĩa (TDD Phụ lục C.1).

Hợp đồng gửi đi (TDD §13.1): chỉ `clause_id` + `masked_text`. KHÔNG role, canonical, start/end, structure.
Phản hồi mà model phải trả (provider structured output): chỉ `items[{clause_id, clause_labels}]`.
`schema_version`, `model_id`, `prompt_version`, `taxonomy_version` do BACKEND điền khi ghép `clause_output_v3`
(model không được tự khai pin — INV-05; lệch nhỏ so với ví dụ TDD §13.2, đã ghi ở PROGRESS §9).
"""

from __future__ import annotations

import hashlib
import json

from app.clause.taxonomy import (
    CLAUSE_LABELS,
    DATA_TAXONOMY_VERSION,
    LABEL_DEFINITIONS,
    MAX_LABELS_PER_CLAUSE,
    MIN_LABELS_PER_CLAUSE,
    TAXONOMY_VERSION,
)

CLAUSE_PROMPT_VERSION = "clause_prompt_v1"
REQUEST_SCHEMA_VERSION = "clause_classification_request_v1"
OUTPUT_SCHEMA_VERSION = "clause_output_v3"

# Schema cho provider structured output = phần model-facing của clause_output_v3 (enum sinh từ code).
RESPONSE_SCHEMA: dict = {
    "type": "object",
    "required": ["items"],
    "additionalProperties": False,
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["clause_id", "clause_labels"],
                "additionalProperties": False,
                "properties": {
                    "clause_id": {"type": "string"},
                    "clause_labels": {
                        "type": "array",
                        "minItems": MIN_LABELS_PER_CLAUSE,
                        "maxItems": MAX_LABELS_PER_CLAUSE,
                        "uniqueItems": True,
                        "items": {"type": "string", "enum": list(CLAUSE_LABELS)},
                    },
                },
            },
        }
    },
}


def build_system_prompt() -> str:
    labels = "\n".join(f"- {name}: {LABEL_DEFINITIONS[name]}" for name in CLAUSE_LABELS)
    return (
        "Bạn phân loại các điều khoản của hợp đồng lao động Việt Nam theo taxonomy cho sẵn.\n"
        "Chỉ làm một việc: gán nhãn chủ đề cho từng điều khoản. KHÔNG đánh giá rủi ro, KHÔNG đưa lời khuyên, "
        "KHÔNG nêu mức độ chắc chắn.\n"
        "Văn bản đã che thông tin cá nhân bằng các placeholder (ví dụ <NAME>___, <PHONE>__): coi chúng là giá trị "
        "đã ẩn, không suy đoán nội dung gốc.\n\n"
        f"Taxonomy ({DATA_TAXONOMY_VERSION}, định nghĩa {TAXONOMY_VERSION}) — chỉ được dùng đúng các nhãn sau:\n"
        f"{labels}\n\n"
        f"Quy tắc: mỗi điều khoản có {MIN_LABELS_PER_CLAUSE}–{MAX_LABELS_PER_CLAUSE} nhãn, không lặp nhãn; "
        "mặc định một nhãn. Nhãn đầu tiên là nhãn chính = chủ đề chiếm nhiều nội dung thực chất nhất; khi "
        "ngang nhau, chọn chủ đề xuất hiện trước. Chỉ thêm nhãn phụ cho một ý trọn vẹn có chủ đề riêng (một câu "
        "hoặc mệnh đề); nhắc thoáng một từ khóa không đủ. Điều khoản chỉ có tiêu đề gán theo chủ đề của tiêu đề. "
        "OTHER chỉ dùng khi không nhãn nào khác phù hợp và luôn đứng một mình: không bao giờ kết hợp OTHER với "
        "nhãn khác.\n"
        "Đầu vào là JSON {items:[{clause_id, masked_text}]}. Trả JSON đúng schema "
        "{items:[{clause_id, clause_labels}]}: mỗi clause_id ở đầu vào xuất hiện đúng một lần, không thêm "
        "clause_id mới, không thêm trường khác, không dùng Markdown."
    )


def build_request(items: list[tuple[str, str]]) -> dict:
    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "taxonomy_version": DATA_TAXONOMY_VERSION,
        "items": [{"clause_id": cid, "masked_text": text} for cid, text in items],
    }


def build_messages(items: list[tuple[str, str]]) -> list[dict]:
    return [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": json.dumps(build_request(items), ensure_ascii=False)},
    ]


def prompt_pin() -> str:
    """Giá trị ghi vào `prompt_version`/VersionPins.clause_prompt_version: đổi khi prompt HOẶC định nghĩa nhãn đổi."""
    digest = hashlib.sha256(build_system_prompt().encode("utf-8")).hexdigest()[:8]
    return f"{CLAUSE_PROMPT_VERSION}+{TAXONOMY_VERSION}+{digest}"
