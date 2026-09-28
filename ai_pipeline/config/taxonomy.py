"""
Taxonomy = 12 nhãn clause_type của data repo.

Bản định nghĩa hiện tại phản ánh clarification v0.3
(ai_pipeline/data/docs/clause_taxonomy_v03.md) — KHÔNG thêm/bớt nhãn so với
v0.2, chỉ làm rõ ranh giới một số cặp nhãn dễ nhầm (xem mục 4 của doc đó).

Đây là NGUỒN DUY NHẤT trong code cho danh sách nhãn: SYSTEM_PROMPT của LLM
(ai_pipeline/services/clause_extraction_service.py) được sinh ra từ
LABEL_DEFINITIONS bên dưới, nên đổi nhãn ở đây là prompt tự đổi theo.

⚠️ ĐÓNG BĂNG: đổi TAXONOMY_VERSION, 12 nhãn, hoặc nội dung định nghĩa thì phải
tăng version (v02 -> v03 -> ...) và sửa test khóa giá trị (test_pipeline /
test_llm_pipeline) có chủ đích. Không sửa "âm thầm".
"""

from types import MappingProxyType

TAXONOMY_VERSION = "v03"

# Nhãn -> định nghĩa ngắn cho LLM. Thứ tự = thứ tự hiển thị trong prompt.
_DEFS = {
    "JOB_INFO": "công việc, chức danh, bộ phận, địa điểm làm việc, nhiệm vụ và phạm vi công việc.",
    "CONTRACT_TERM": "loại và thời hạn hợp đồng lao động, ngày bắt đầu/kết thúc, thời điểm có hiệu lực.",
    "COMPENSATION_BENEFITS": (
        "lương, phụ cấp, thưởng, nâng lương, công tác phí và các chế độ/quyền lợi tài chính "
        "(bản thân mức/hình thức/kỳ hạn trả — không phải nghĩa vụ thanh toán của NSDLĐ)."
    ),
    "WORKING_TIME": "giờ làm việc, lịch làm việc, ca làm, làm thêm giờ/tăng ca, nghỉ giữa ca/nghỉ trong ngày.",
    "LEAVE": "nghỉ hằng tuần, phép năm, nghỉ lễ/Tết, nghỉ bù và các ngày nghỉ khác.",
    "INSURANCE_SAFETY": "BHXH/BHYT/BHTN, mức đóng bảo hiểm, an toàn và vệ sinh lao động, bảo hộ lao động/PPE.",
    "WORKING_CONDITIONS": "công cụ, thiết bị, phương tiện, chỗ ăn/ở và điều kiện vật chất phục vụ công việc.",
    "TRAINING": "đào tạo, bồi dưỡng, học nghề/học văn hóa, cam kết sau đào tạo và hoàn trả chi phí đào tạo.",
    "EMPLOYEE_OBLIGATIONS_DISCIPLINE": (
        "nghĩa vụ, kỷ luật, trách nhiệm vật chất, bồi thường (khi NLĐ phải bồi thường) và nghĩa vụ "
        "thuế của người lao động (kể cả cam kết bảo mật/không cạnh tranh nếu có)."
    ),
    "EMPLOYER_RIGHTS_OBLIGATIONS": (
        "quyền và nghĩa vụ quản lý, điều hành của người sử dụng lao động (điều chuyển, quản lý, "
        "yêu cầu bồi thường, và nghĩa vụ thanh toán/đảm bảo các chế độ đã thỏa thuận)."
    ),
    "TERMINATION": "căn cứ, điều kiện, thủ tục, thời hạn báo trước và hậu quả của việc chấm dứt hợp đồng lao động.",
    "OTHER": (
        "điều khoản thi hành, sửa đổi/phụ lục, số bản, hiệu lực và các nội dung không thuộc "
        "các nhóm trên (kể cả giải quyết tranh chấp và quyền được bồi thường của NLĐ khi chưa có "
        "class chuyên biệt, nếu có)."
    ),
}

LABEL_DEFINITIONS = MappingProxyType(_DEFS)

# Có thứ tự (dùng để tie-break khi resolve multi-label ở labeling.py).
CLAUSE_LABELS: tuple[str, ...] = tuple(_DEFS)
CLAUSE_LABEL_SET: frozenset[str] = frozenset(CLAUSE_LABELS)
