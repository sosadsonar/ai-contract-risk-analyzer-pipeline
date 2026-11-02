"""Văn bản TỔNG HỢP dùng chung cho test LLM thật (không PII, AI_CONTEXT §3)."""

from app.ai.clause_adapter import ClauseMasked
from app.ai.risk_adapter import LegalCandidate, RiskItemIn

CLAUSES = [
    ClauseMasked("cl_0001", "Điều 1. Chức danh và công việc\nNgười lao động đảm nhận vị trí Lập trình viên tại văn phòng Công ty."),
    ClauseMasked("cl_0002", "Điều 2. Thời giờ làm việc\nNgười lao động làm việc 8 tiếng một ngày, từ thứ Hai đến thứ Sáu."),
    ClauseMasked("cl_0003", "Điều 3. Tiền lương\nMức lương cơ bản là 15.000.000 đồng/tháng, trả vào ngày 05 hằng tháng."),
]

RISK_CANDIDATES = {
    "SYN:art1": LegalCandidate("SYN:art1", "Thời gian thử việc tối đa 60 ngày đối với công việc có chức danh cần trình độ cao đẳng trở lên.",
                               "Văn bản tổng hợp", "Điều 1"),
}
RISK_ITEMS = [
    RiskItemIn("cl_0001", "Điều 5. Thử việc\nThời gian thử việc là 180 ngày, lương thử việc bằng 50% lương chính thức.",
               ["PROBATION"], ["SYN:art1"]),
]
