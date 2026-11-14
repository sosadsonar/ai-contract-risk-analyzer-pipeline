"""Source-only Article 17 candidate for Dev; no Gold or T2 text in the rules."""

import re
import unicodedata

from app.risk import dev_injection_baseline as base

_DOCUMENT_TERMS = (
    r"giấy\s+tờ(?:\s+tùy\s+thân|\s+gốc)?|căn\s+cước|cccd|cmnd|chứng\s+minh\s+nhân\s+dân|"
    r"hộ\s+chiếu|sổ\s+hộ\s+khẩu|văn\s+bằng|bằng\s+(?:tốt\s+nghiệp|đại\s+học|cấp)|"
    r"chứng\s+chỉ(?:\s+hành\s+nghề)?|hồ\s+sơ\s+gốc|bằng\s+lái|giấy\s+phép\s+lái\s+xe|"
    r"sổ\s+bảo\s+hiểm|học\s+bạ|bảng\s+điểm|thẻ\s+sinh\s+viên|giấy\s+đăng\s+ký\s+xe|"
    r"cavet\s+xe|sổ\s+đỏ|giấy\s+chứng\s+nhận\s+quyền\s+sử\s+dụng\s+đất"
)
_ORIGINAL = r"(?:bản\s+(?:chính|gốc)|gốc)"
_KEEP = (r"(?:giữ|lưu\s+giữ|tạm\s+giữ|thu\s+giữ|nắm\s+giữ|cất\s+giữ|bảo\s+quản|"
         r"giữ\s+lại|quản\s+lý|lưu\s+tại|nộp|giao\s+nộp|giao|ký\s+gửi|để\s+lại|"
         r"chưa\s+trả|không\s+trả\s+lại|hoãn\s+trả|chỉ\s+trả\s+lại\s+khi|"
         r"hoàn\s+trả\s+khi|trả\s+lại\s+sau\s+khi)")

# Kept as a named pattern for citation selection in the restricted review-packet builder.
_DOCUMENT = re.compile(
    rf"(?:{_ORIGINAL}).{{0,55}}(?:{_DOCUMENT_TERMS})|"
    rf"(?:{_DOCUMENT_TERMS}).{{0,55}}(?:{_ORIGINAL})|giấy\s+tờ\s+gốc|hồ\s+sơ\s+gốc"
)
_RETENTION = re.compile(
    rf"(?:{_KEEP}).{{0,105}}(?:{_DOCUMENT_TERMS})|"
    rf"(?:{_DOCUMENT_TERMS}).{{0,105}}(?:{_KEEP})"
)
_STRONG_KEEP = re.compile(r"giữ|lưu\s+giữ|tạm\s+giữ|thu\s+giữ|quản\s+lý")
_COPY_ONLY = re.compile(r"bản\s+sao|bản\s+chụp|photocopy|sao\s+y")
_COPY_ONLY_RE = _COPY_ONLY
_DOCUMENT_DIRECT = re.compile(
    rf"(?:{_KEEP}).{{0,105}}(?:{_DOCUMENT_TERMS})|"
    rf"(?:{_DOCUMENT_TERMS}).{{0,105}}(?:{_KEEP})"
)
_SECURITY = re.compile(
    r"đặt\s+cọc|ký\s+quỹ|thế\s+chân|thế\s+chấp|cầm\s+cố|"
    r"bảo\s+lãnh\s+bằng\s+tiền|(?:tiền|khoản|tài\s+sản|vật|biện\s+pháp)\s+bảo\s+đảm|"
    r"bảo\s+đảm\s+bằng\s+(?:tiền|tài\s+sản)|tài\s+sản.{0,55}(?:làm\s+)?bảo\s+đảm|"
    r"giữ\s+lại.{0,35}lương.{0,35}bảo\s+đảm|"
    r"khấu\s+trừ.{0,35}(?:lương|tiền).{0,35}bảo\s+đảm|"
    r"nộp.{0,30}(?:khoản\s+)?tiền.{0,45}thực\s+hiện\s+hợp\s+đồng|"
    r"đóng\s+tiền\s+bảo\s+đảm|cam\s+kết\s+bằng\s+tài\s+sản"
    r"|tiền\s+(?:thế\s+chân|trách\s+nhiệm)|quỹ\s+(?:dự\s+phòng\s+rủi\s+ro|trách\s+nhiệm)|"
    r"tài\s+khoản\s+phong\s+tỏa|nộp\s+khoản\s+tiền\s+trách\s+nhiệm|"
    r"(?:tạm\s+giữ|giữ\s+lại|trích|khấu\s+trừ).{0,35}(?:%\s*)?(?:tiền\s+)?lương|"
    r"giao\s+tài\s+sản|cam\s+kết\s+tài\s+sản"
)
_SECURITY_PURPOSE = re.compile(
    r"bảo\s+đảm|đảm\s+bảo|thực\s+hiện\s+hợp\s+đồng|nghỉ\s+việc|"
    r"chấm\s+dứt|bồi\s+thường|trách\s+nhiệm|rủi\s+ro"
)
_SECURITY_DIRECT = re.compile(
    r"đặt\s+cọc|(?:tiền|khoản)\s+cọc|ký\s+quỹ|tiền\s+thế\s+chân|"
    r"quỹ\s+(?:trách\s+nhiệm|dự\s+phòng)|tiền\s+bảo\s+lãnh|"
    r"tài\s+sản\s+thế\s+chấp|cầm\s+cố\s+tài\s+sản|"
    r"(?:phong\s+tỏa\s+)?(?:tài\s+khoản|sổ\s+tiết\s+kiệm)\s+phong\s+tỏa|"
    r"(?:giữ\s+lại|tạm\s+giữ|trích\s+giữ|khấu\s+trừ)[^.;]{0,50}"
    r"(?:lương|thu\s+nhập|thưởng)[^.;]{0,50}"
    r"(?:bảo\s+đảm|làm\s+tin|thế\s+chân|dự\s+phòng|cam\s+kết|ràng\s+buộc)"
)
_EMPLOYMENT_CONTEXT = re.compile(
    r"người\s+lao\s+động|nhân\s+viên|công\s+ty|bên\s+a|bên\s+b|"
    r"hợp\s+đồng|làm\s+việc|nhận\s+việc|thực\s+hiện\s+công\s+việc"
)
_EMPLOYER_CONTEXT = re.compile(r"công\s+ty|bên\s+a|người\s+sử\s+dụng\s+lao\s+động")
_OBLIGATION = re.compile(
    r"phải|buộc|yêu\s+cầu|nộp|đóng|giao|duy\s+trì|giữ\s+lại|khấu\s+trừ|"
    r"(?:cho\s+)?đến\s+khi|chưa\s+được|không\s+được"
)
_WORK = re.compile(
    r"làm\s+việc|tiếp\s+tục\s+làm\s+việc|thực\s+hiện\s+hợp\s+đồng|"
    r"chưa\s+được\s+nghỉ\s+việc|không\s+được\s+chấm\s+dứt|kéo\s+dài\s+thời\s+hạn\s+làm\s+việc|"
    r"thời\s+hạn\s+làm\s+việc.{0,25}kéo\s+dài|thực\s+hiện\s+công\s+việc|"
    r"phục\s+vụ\s+công\s+ty|trừ\s+vào\s+công\s+lao\s+động|nghỉ\s+việc|chấm\s+dứt"
)
_DEBT = re.compile(
    r"trả\s+nợ|thanh\s+toán\s+nợ|hết\s+nợ|còn\s+nợ|khoản\s+nợ|"
    r"nợ|khoản\s+(?:tiền\s+)?vay|khoản\s+tạm\s+ứng|cấn\s+trừ\s+nợ|khấu\s+trừ\s+nợ|"
    r"(?:hoàn\s+trả|bù\s+đắp|trừ\s+dần|thanh\s+toán).{0,35}(?:khoản\s+)?"
    r"(?:tiền|chi\s+phí|tạm\s+ứng)|tiền\s+ứng\s+trước|khấu\s+trừ\s+bằng\s+(?:ngày\s+)?công"
)
_THIRD_PARTY_CREDITOR = re.compile(r"ngân\s+hàng|tổ\s+chức\s+tín\s+dụng|bên\s+thứ\s+ba")
_DEBT_OBLIGATION = re.compile(
    rf"(?:{_WORK.pattern}).{{0,140}}(?:{_DEBT.pattern})|"
    rf"(?:{_DEBT.pattern}).{{0,140}}(?:{_WORK.pattern})"
)
_WORK_RESTRICTION = re.compile(
    r"(?:không\s+được(?:\s+phép)?|chưa\s+được(?:\s+phép)?|không\s+có\s+quyền|"
    r"cấm|bị\s+cấm|không\s+giải\s+quyết(?:\s+cho)?)\s+"
    r"(?:đơn\s+phương\s+)?(?:chấm\s+dứt(?:\s+hợp\s+đồng)?|nghỉ\s+việc|"
    r"thôi\s+việc|rời\s+khỏi\s+công\s+ty|ngừng\s+làm\s+việc)|"
    r"(?:phải|bắt\s+buộc|cam\s+kết|tiếp\s+tục)\s+(?:ở\s+lại\s+)?"
    r"(?:làm\s+việc|công\s+tác|phục\s+vụ|thực\s+hiện\s+hợp\s+đồng)"
)
_FINANCIAL_OBLIGATION = re.compile(
    rf"{_DEBT.pattern}|công\s+nợ|ứng\s+trước|bồi\s+thường|bồi\s+hoàn|"
    r"thiệt\s+hại|nghĩa\s+vụ\s+tài\s+chính|chi\s+phí\s+đào\s+tạo|"
    r"kinh\s+phí\s+đào\s+tạo|khoản\s+tiền\s+còn\s+thiếu"
)

_NEGATED_RETENTION = re.compile(
    r"\bkhông\s+(?:được\s+)?(?:giữ|lưu\s+giữ|tạm\s+giữ|thu\s+giữ|"
    r"yêu\s+cầu\s+(?:giao|nộp))\b"
)
_NEGATED_SECURITY = re.compile(
    r"\bkhông\s+(?:(?:được|phải|cần)\s+)?(?:yêu\s+cầu\s+(?:\w+\s+){0,3})?"
    r"(?:đặt\s+cọc|ký\s+quỹ|thế\s+chân|thế\s+chấp|cầm\s+cố|"
    r"nộp\s+(?:tiền|tài\s+sản)|đóng\s+tiền\s+bảo\s+đảm)\b"
)
_NEGATED_DEBT = re.compile(
    r"\bkhông\s+(?:được\s+)?(?:buộc|yêu\s+cầu).{0,75}(?:làm\s+việc|"
    r"thực\s+hiện\s+hợp\s+đồng).{0,85}(?:nợ|vay|tạm\s+ứng)|"
    r"được\s+(?:quyền\s+)?(?:nghỉ\s+việc|chấm\s+dứt).{0,85}(?:dù|mặc\s+dù).{0,35}còn\s+nợ"
)
_AFFIRMATIVE_AFTER_CONTRAST = re.compile(
    r"(?:nhưng|tuy\s+nhiên).{0,100}(?:giữ|đặt\s+cọc|ký\s+quỹ|buộc|phải\s+làm\s+việc)"
)
_STATUTORY_DOC_OBJECT = re.compile(
    r"giấy\s+tờ|hồ\s+sơ|văn\s+bằng|bằng\s+(?:cấp|tốt\s+nghiệp)|chứng\s+chỉ|"
    r"thẻ\s+(?:căn\s+cước|ngân\s+hàng|atm)|sổ\s+(?:bảo\s+hiểm|tiết\s+kiệm)|"
    r"học\s+bạ|bảng\s+điểm|lý\s+lịch|tài\s+sản\s+cá\s+nhân|"
    r"chứng\s+minh\s+(?:nhân\s+dân|thư)|cmtnd|cmt|gplx|bhxh|"
    r"giấy\s+(?:khai\s+sinh|khám\s+sức\s+khỏe|chứng\s+nhận)|chứng\s+nhận|"
    r"sơ\s+yếu\s+lý\s+lịch|(?:tài\s+liệu|chứng\s+từ|hợp\s+đồng)\s+gốc|"
    r"cavet|cà\s+vẹt"
)
_DOC_NOUN_RE = _STATUTORY_DOC_OBJECT
_STATUTORY_BINDING = re.compile(
    r"cam\s+kết|ràng\s+buộc|làm\s+tin|bảo\s+đảm|trong\s+(?:suốt\s+)?thời\s+gian\s+làm\s+việc|"
    r"khi\s+(?:chấm\s+dứt|nghỉ\s+việc)|đến\s+khi\s+(?:hết|chấm\s+dứt)\s+hợp\s+đồng"
)
_STATUTORY_MONEY_ACTION = re.compile(
    r"\b(?:thu\s+(?:trước|tiền|khoản|phí)|nộp|đóng|giữ|trích|khấu\s+trừ|không\s+hoàn\s+trả)\b"
)
_STATUTORY_MONEY = re.compile(
    r"tiền|lương|thu\s+nhập|thưởng|khoản\s+phí|\b\d[\d.]*\s*đồng\b"
)
_PRECOLLECT_MONEY = re.compile(
    r"(?:thu|nộp|đóng|giao|giữ\s+lại|tạm\s+giữ|trích\s+giữ|trích\s+lại|"
    r"khấu\s+trừ\s+trước|tạm\s+trừ).{0,65}(?:tiền|lương|thu\s+nhập|thưởng|quỹ)"
)
_FORCED_DEBT_WORK = re.compile(
    r"(?:buộc|bắt\s+buộc|phải|tiếp\s+tục|ở\s+lại).{0,30}"
    r"(?:làm\s+việc|công\s+tác|thực\s+hiện\s+hợp\s+đồng).{0,70}"
    r"(?:trả|trừ|khấu\s+trừ|bù\s+đắp|hoàn\s+trả|thanh\s+toán).{0,50}"
    r"(?:nợ|vay|tạm\s+ứng|khoản\s+tiền|chi\s+phí\s+đào\s+tạo)"
)
_LAWFUL_DEDUCTION = re.compile(
    r"bhxh|bhyt|bhtn|bảo\s+hiểm\s+(?:xã\s+hội|y\s+tế|thất\s+nghiệp)|"
    r"thuế\s+(?:thu\s+nhập\s+cá\s+nhân|tncn)|bồi\s+thường\s+thiệt\s+hại\s+(?:dụng\s+cụ|thiết\s+bị)"
)


def _without_negated_action(text: str, pattern: re.Pattern[str]) -> str:
    """Remove only a directly negated action, retaining other clauses in the span."""
    return pattern.sub(" ", text)


def _negated_only(text: str, pattern: re.Pattern[str]) -> bool:
    return bool(pattern.search(text)) and not bool(_AFFIRMATIVE_AFTER_CONTRAST.search(text))


def _propositions(text: str) -> list[str]:
    """Split at sentence punctuation, preserving decimal/thousands separators."""
    parts = [part.strip() for part in re.split(r";|\n|(?<!\d)\.(?!\d)", text)]
    return [part for part in parts if part]


def _evidence_windows(text: str) -> list[str]:
    parts = [part for part in _propositions(text)
             if not ((_COPY_ONLY.search(part) or re.search(r"công\s+chứng|photo", part))
                     and not re.search(r"bản\s+(?:chính|gốc)|hồ\s+sơ\s+gốc", part)
                     and not _SECURITY.search(part))]
    return parts + [f"{a}; {b}" for a, b in zip(parts, parts[1:])]


def _has_document_violation(text: str) -> bool:
    """Apply the copy guard per proposition, never to an entire mixed clause."""
    for part in _evidence_windows(text):
        if not part.strip() or not _RETENTION.search(part):
            continue
        explicit_original = bool(_DOCUMENT.search(part))
        copied_only = bool(_COPY_ONLY.search(part)) and not explicit_original
        if copied_only:
            continue
        if explicit_original or (_DOCUMENT_DIRECT.search(part) and _EMPLOYMENT_CONTEXT.search(text)):
            return True
        if (base._DEPOSIT.search(part) and _STRONG_KEEP.search(part)
                and re.search(_DOCUMENT_TERMS, part)):
            return True
    return False


def _statutory_clause_signals(text: str) -> tuple[bool, bool, bool]:
    """Check each proposition; training commitments alone are not Article 17 debt."""
    document = money = debt = False
    for part in _evidence_windows(text):
        if (_STATUTORY_DOC_OBJECT.search(part) and re.search(_KEEP, part)
                and _STATUTORY_BINDING.search(part) and not _COPY_ONLY.search(part)
                and not re.search(r"(?:công\s+cụ|thiết\s+bị|tài\s+sản)\s+của\s+công\s+ty", part)
                and not re.search(r"xuất\s+trình.{0,35}đối\s+chiếu", part)):
            document = True
        if (_STATUTORY_MONEY_ACTION.search(part) and _STATUTORY_MONEY.search(part)
                and _STATUTORY_BINDING.search(part) and not _LAWFUL_DEDUCTION.search(part)):
            money = True
        if (_PRECOLLECT_MONEY.search(part) and _STATUTORY_BINDING.search(part)
                and not _LAWFUL_DEDUCTION.search(part)):
            money = True
        if (_WORK_RESTRICTION.search(part) and _FINANCIAL_OBLIGATION.search(part)
                and re.search(r"nợ|vay|tạm\s+ứng|ứng\s+trước|tiền\s+đã\s+nhận", part)):
            debt = True
        if _FORCED_DEBT_WORK.search(part):
            debt = True
    return document, money, debt


def _without_lawful_deduction(text: str) -> str:
    return ";".join(" " if _LAWFUL_DEDUCTION.search(part) else part
                    for part in _propositions(text))


def detect_dev_risks_candidate(text: str) -> tuple[tuple[str, str], ...]:
    """Emit both role views for source-supported Article 17 violations only."""
    normalized = unicodedata.normalize("NFC", text).casefold()
    normalized = re.sub(r"[ \t\r\f\v]+", " ", normalized)
    baseline_labels = {label for _, label in base.detect_dev_risks(text)}
    document_text = _without_negated_action(normalized, _NEGATED_RETENTION)
    security_text = _without_lawful_deduction(
        _without_negated_action(normalized, _NEGATED_SECURITY))
    statutory_document, statutory_money, statutory_debt = _statutory_clause_signals(normalized)

    document_violation = _has_document_violation(document_text) or statutory_document
    security_violation = (
        bool(_SECURITY.search(security_text) and _EMPLOYMENT_CONTEXT.search(security_text)
             and (_OBLIGATION.search(security_text) or _SECURITY_PURPOSE.search(security_text)))
        or "DEPOSIT_DOCUMENT_HELD" in baseline_labels and bool(_SECURITY.search(security_text))
        or statutory_money
        or bool(_SECURITY_DIRECT.search(security_text)
                and _EMPLOYMENT_CONTEXT.search(security_text))
    )
    debt_violation = (
        bool(_DEBT_OBLIGATION.search(normalized) and _OBLIGATION.search(normalized))
        or statutory_debt
        or bool(_WORK_RESTRICTION.search(normalized)
                and _FINANCIAL_OBLIGATION.search(normalized)
                and re.search(r"nợ|vay|tạm\s+ứng|ứng\s+trước|tiền\s+đã\s+nhận", normalized))
        or "EMPLOYEE_OBLIGATIONS_DISCIPLINE" in baseline_labels
    ) and (not _THIRD_PARTY_CREDITOR.search(normalized)
           or _EMPLOYER_CONTEXT.search(normalized)) and not _negated_only(
        normalized, _NEGATED_DEBT
    )

    labels = set()
    if document_violation or security_violation:
        labels.add("DEPOSIT_DOCUMENT_HELD")
    if debt_violation:
        labels.add("EMPLOYEE_OBLIGATIONS_DISCIPLINE")  # legacy D2 injection label
    return tuple((role, label) for label in sorted(labels) for role in ("EMPLOYEE", "EMPLOYER"))
