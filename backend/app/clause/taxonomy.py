"""
Clause taxonomy = 12 nhãn `clause_labels` — NGUỒN DUY NHẤT trong code (TDD §3.2, DEC-20).

Semantics nguồn của nhãn là data repo `clause_taxonomy_v03` (ai_pipeline/data/docs/).
Code ở đây chỉ phản ánh: không thêm/bớt nhãn so với v0.2/v0.3, chỉ làm rõ ranh giới
một số cặp nhãn dễ nhầm (xem docs/DATA_LEAD_REVIEW_V03.md).

Hai khái niệm version KHÔNG được lẫn lộn (TDD §6.4):
- DATA_TAXONOMY_VERSION  = "clause_taxonomy_v03": version taxonomy nguồn của data. Đây là giá trị
  ghi vào `taxonomy_version` của clause_output_v3 và VersionPins.clause_taxonomy_version.
- TAXONOMY_VERSION       = "v04": revision của ĐỊNH NGHĨA dùng trong prompt (sửa ranh giới,
  không đổi từ vựng nhãn). Được ghi qua `clause_prompt_version`, không thêm field vào VersionPins.

Prompt của LLM (ai/prompts/clause_v1.py, C-01) phải sinh từ LABEL_DEFINITIONS ở đây.

Quy tắc nhãn cho 1 clause (OI-10 — chờ freeze ở MS-1): 1..3 nhãn, thuộc taxonomy, không trùng.
Không còn `type_scores`, `max_content_risk_tier`, `review_zone` (DEC-17, SRS C-03).

⚠️ ĐÓNG BĂNG ở MS-1 (25/10): đổi 12 nhãn hoặc nội dung định nghĩa thì phải tăng version
và sửa test khóa giá trị (tests/test_data_lead_review.py, tests/unit/test_clause_taxonomy.py)
có chủ đích. Không sửa "âm thầm".
"""

from types import MappingProxyType

DATA_TAXONOMY_VERSION = "clause_taxonomy_v03"

# v04 is a prompt-definition revision; the unchanged data vocabulary/semantics
# remain clause_taxonomy_v03.md. See docs/DATA_LEAD_REVIEW_V03.md.
TAXONOMY_VERSION = "v04"

MIN_LABELS_PER_CLAUSE = 1
MAX_LABELS_PER_CLAUSE = 3

# Nhãn -> định nghĩa ngắn cho LLM. Thứ tự = thứ tự hiển thị trong prompt.
_DEFS = {
    "JOB_INFO": "công việc, chức danh, bộ phận, địa điểm làm việc, nhiệm vụ và phạm vi công việc.",
    "CONTRACT_TERM": (
        "loại và thời hạn hợp đồng lao động, ngày bắt đầu/kết thúc, thời điểm có hiệu lực."
    ),
    "COMPENSATION_BENEFITS": (
        "lương, phụ cấp, thưởng, nâng lương, công tác phí và các chế độ/quyền lợi tài chính "
        "(bản thân mức/hình thức/kỳ hạn trả — không phải nghĩa vụ thanh toán của NSDLĐ)."
    ),
    "WORKING_TIME": (
        "giờ làm việc, lịch làm việc, ca làm, làm thêm giờ/tăng ca, nghỉ giữa ca/nghỉ trong ngày."
    ),
    "LEAVE": "nghỉ hằng tuần, phép năm, nghỉ lễ/Tết, nghỉ bù và các ngày nghỉ khác.",
    "INSURANCE_SAFETY": (
        "BHXH/BHYT/BHTN, mức đóng bảo hiểm, an toàn và vệ sinh lao động, bảo hộ lao động/PPE."
    ),
    "WORKING_CONDITIONS": (
        "công cụ, thiết bị, phương tiện, chỗ ăn/ở và điều kiện vật chất phục vụ công việc."
    ),
    "TRAINING": (
        "đào tạo, bồi dưỡng, học nghề/học văn hóa, cam kết sau đào tạo và hoàn trả chi phí đào tạo."
    ),
    "EMPLOYEE_OBLIGATIONS_DISCIPLINE": (
        "nghĩa vụ, kỷ luật, trách nhiệm vật chất, bồi thường (khi NLĐ phải bồi thường) và nghĩa vụ "
        "thuế của người lao động. Ưu tiên nhãn này khi trọng tâm là NLĐ phải "
        "tuân thủ hướng dẫn, giữ gìn thiết bị, phòng cháy hoặc chấp hành quy định; "
        "nếu topic chính trực tiếp là PPE/an toàn/bảo hiểm thì dùng INSURANCE_SAFETY."
    ),
    "EMPLOYER_RIGHTS_OBLIGATIONS": (
        "quyền và nghĩa vụ quản lý, điều hành của người sử dụng lao động (điều chuyển, quản lý, "
        "yêu cầu bồi thường, phải bồi thường cho NLĐ, và nghĩa vụ thanh toán/đảm bảo "
        "các chế độ đã thỏa thuận). Nếu chấm dứt chỉ là một phần trong danh sách "
        "quyền quản lý tổng quát thì vẫn dùng nhãn này."
    ),
    "TERMINATION": (
        "căn cứ, điều kiện, sa thải/chấm dứt, thủ tục, thời hạn báo trước và hậu quả trực tiếp "
        "của việc chấm dứt hợp đồng lao động."
    ),
    "OTHER": (
        "điều khoản thi hành, sửa đổi/phụ lục, số bản và các nội dung chưa có class phù hợp "
        "(quyền được bồi thường của NLĐ khi chưa có class chuyên biệt)."
    ),
}

LABEL_DEFINITIONS = MappingProxyType(_DEFS)

# Có thứ tự (thứ tự hiển thị trong prompt; tie-break ổn định nếu cần).
CLAUSE_LABELS: tuple[str, ...] = tuple(_DEFS)
CLAUSE_LABEL_SET: frozenset[str] = frozenset(CLAUSE_LABELS)


def validate_labels(labels: list[str]) -> list[str]:
    """Kiểm tra `clause_labels` của một clause: 1..3 nhãn, thuộc taxonomy, không trùng.

    Trả về chính danh sách đã kiểm (giữ nguyên thứ tự; nhãn đầu = nhãn chính).
    Raise ValueError nếu vi phạm — adapter chuyển thành AiOutputInvalid (INV-05).
    """
    if not isinstance(labels, (list, tuple)):
        raise ValueError(f"clause_labels phải là list, nhận {type(labels).__name__}")
    if not MIN_LABELS_PER_CLAUSE <= len(labels) <= MAX_LABELS_PER_CLAUSE:
        raise ValueError(
            f"clause_labels phải có {MIN_LABELS_PER_CLAUSE}..{MAX_LABELS_PER_CLAUSE} nhãn, "
            f"nhận {len(labels)}"
        )
    unknown = [x for x in labels if x not in CLAUSE_LABEL_SET]
    if unknown:
        raise ValueError(f"Nhãn ngoài taxonomy: {unknown}")
    if len(set(labels)) != len(labels):
        raise ValueError(f"clause_labels có nhãn trùng: {list(labels)}")
    return list(labels)
