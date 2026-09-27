"""
Service thật (không mock) cho bước Segmentation + Classification.

Luồng xử lý:
  raw_text --(LLM: Gemini hoặc Qwen/Ollama)--> danh sách clause thô (text + nhãn + score)
           --(tự tìm lại vị trí ký tự trong raw_text)--> gắn span
           --(compute_clause_routing từ config/thresholds.py)--> gắn risk tier + review_zone
           --> JSON đúng schema v2 (ai_pipeline/schemas/contract_v2.json)

Chạy thử: xem ai_pipeline/test_llm_pipeline.py
"""

import re
from typing import Optional

from config.thresholds import RISK_TAXONOMY_MAP, compute_clause_routing
from services.llm_clients import LLMClientError, get_llm_client

CLAUSE_LABELS = list(RISK_TAXONOMY_MAP.keys())

SYSTEM_PROMPT = f"""Bạn là trợ lý pháp lý chuyên phân tích hợp đồng lao động tiếng Việt.

Nhiệm vụ: đọc văn bản hợp đồng được cung cấp, CẮT thành các điều khoản (clause)
theo đúng ranh giới "Điều X" nếu có đánh số, và PHÂN LOẠI đa nhãn (multi-label)
mỗi điều khoản theo đúng danh sách nhãn sau, không được bịa nhãn khác:
{", ".join(CLAUSE_LABELS)}

Định nghĩa ngắn gọn từng nhãn:
- JOB_DUTIES: chức danh, mô tả công việc, địa điểm làm việc.
- WORKING_HOURS_LEAVE: thời giờ làm việc, nghỉ ngơi, phép năm, tăng ca.
- COMPENSATION: lương, phụ cấp, thưởng, hoa hồng, hình thức trả lương.
- BENEFITS_INSURANCE: bảo hiểm xã hội/y tế/thất nghiệp, phúc lợi khác.
- CONFIDENTIALITY_IP: bảo mật thông tin, sở hữu trí tuệ, cam kết không cạnh tranh.
- TERMINATION: điều kiện/thủ tục chấm dứt hợp đồng, thử việc, bồi thường khi chấm dứt.
- DISPUTE_RESOLUTION: luật áp dụng, cơ quan giải quyết tranh chấp.
- OTHER: điều khoản chung khác không thuộc các nhóm trên (hiệu lực hợp đồng, số bản...).

QUAN TRỌNG:
1. `original_text` PHẢI được copy CHÍNH XÁC nguyên văn (giữ nguyên dấu câu, khoảng
   trắng) từ văn bản gốc — vì hệ thống sẽ dùng nó để tìm lại vị trí ký tự, nếu bạn
   diễn giải lại hoặc tóm tắt thì hệ thống sẽ không định vị được.
2. Một điều khoản có thể có nhiều nhãn (multi-label) nếu nội dung bao trùm nhiều ý.
3. `type_scores` là độ tự tin của BẠN cho từng nhãn được gán, từ 0.0 đến 1.0.
4. CHỈ trả về JSON thuần theo đúng định dạng bên dưới, KHÔNG thêm giải thích,
   KHÔNG bọc trong markdown code block.

Định dạng JSON bắt buộc:
{{
  "clauses": [
    {{
      "clause_number": "Điều X hoặc null nếu không đánh số",
      "original_text": "nguyên văn điều khoản",
      "clause_type": ["LABEL1", "LABEL2"],
      "type_scores": {{"LABEL1": 0.0, "LABEL2": 0.0}}
    }}
  ]
}}
"""


def _build_user_prompt(raw_text: str) -> str:
    return f"Hợp đồng lao động cần phân tích:\n\n{raw_text}"


def _locate_span(raw_text: str, clause_text: str) -> Optional[tuple[int, int]]:
    """Tìm vị trí ký tự chính xác của clause_text trong raw_text.

    Trả về None nếu không tìm thấy khớp chính xác (ví dụ LLM đã diễn giải lại
    thay vì copy nguyên văn) — khi đó `span` trong output sẽ là null và cần
    được review thủ công, thay vì đoán bừa một vị trí sai.
    """
    if not clause_text:
        return None
    idx = raw_text.find(clause_text)
    if idx != -1:
        return idx, idx + len(clause_text)

    # Fallback: thử khớp sau khi chuẩn hoá khoảng trắng (LLM đôi khi đổi xuống
    # dòng thành khoảng trắng). Chỉ dùng để PHÁT HIỆN có khớp gần đúng hay không;
    # vẫn trả None vì offset trên bản đã chuẩn hoá không map thẳng về raw_text gốc.
    normalized_raw = re.sub(r"\s+", " ", raw_text)
    normalized_clause = re.sub(r"\s+", " ", clause_text).strip()
    if normalized_clause and normalized_clause in normalized_raw:
        return None  # khớp gần đúng nhưng không tính được offset chính xác -> để None, đánh dấu cần review
    return None


def extract_clauses(
    raw_text: str,
    provider: Optional[str] = None,
    contract_id: str = "UNKNOWN",
) -> dict:
    """Chạy pipeline Clause Segmentation + Classification bằng LLM thật.

    Args:
        raw_text: văn bản hợp đồng thô.
        provider: "gemini" | "qwen_ollama" | None (đọc từ env LLM_PROVIDER).
        contract_id: id gán cho hợp đồng trong output.

    Returns:
        dict đúng schema ai_pipeline/schemas/contract_v2.json, kèm thêm field
        "llm_provider" và "unmatched_span_count" để debug nhanh.

    Raises:
        LLMClientError: nếu gọi LLM thất bại hoặc LLM không trả JSON hợp lệ.
    """
    client = get_llm_client(provider)
    raw_response = client.generate_json(SYSTEM_PROMPT, _build_user_prompt(raw_text))

    llm_clauses = raw_response.get("clauses", [])
    if not isinstance(llm_clauses, list):
        raise LLMClientError(f"Trường 'clauses' trong phản hồi LLM không phải list: {raw_response}")

    final_clauses = []
    unmatched_span_count = 0
    for i, c in enumerate(llm_clauses):
        clause_text = c.get("original_text", "")
        span = _locate_span(raw_text, clause_text)
        if span is None:
            unmatched_span_count += 1

        type_scores = c.get("type_scores", {}) or {}
        # Bỏ qua nhãn không nằm trong taxonomy (phòng khi LLM bịa nhãn) thay vì crash.
        type_scores = {k: v for k, v in type_scores.items() if k in CLAUSE_LABELS}
        routing_info = compute_clause_routing(type_scores)

        final_clauses.append(
            {
                "clause_id": f"clause_{i + 1}",
                "clause_number": c.get("clause_number"),
                "span": {"start_char": span[0], "end_char": span[1]} if span else None,
                "original_text": clause_text,
                "clause_type": c.get("clause_type", list(type_scores.keys())),
                "type_scores": type_scores,
                **routing_info,
            }
        )

    return {
        "contract_id": contract_id,
        "total_clauses": len(final_clauses),
        "clauses": final_clauses,
        "llm_provider": client.provider_name,
        "unmatched_span_count": unmatched_span_count,
    }
