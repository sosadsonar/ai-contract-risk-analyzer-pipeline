"""
Che dữ liệu nhạy cảm (PII masking) - BẢN NHÁP spike trước C-09, chưa nối vào pipeline.

Tuân thủ TDD §10 (và INV-02, INV-03, INV-04):
- Chạy trên TOÀN BỘ canonical_text trước segmentation, placeholder cùng độ dài (Unicode code point).
- Không có bảng ánh xạ placeholder -> giá trị gốc; chỉ giữ pii_spans[{type,start,end}].
- Không NER/LLM; chỉ regex có anchor + heuristic. Từ chỉ vai trò (NLĐ, NSDLĐ, "Công ty" dùng như
  đại từ) KHÔNG bị mask; chỉ mask phần giá trị đi sau anchor.

Cấu trúc đích sau C-09 (TDD §3.2): app/privacy/{pii_types,detector,masker}.py và boundary_guard
ở clause/segmenter.py. File này giữ một chỗ cho tới lúc đó.

Giới hạn đã biết (cần đo trên D1, SRS OI-12):
- Tên người chỉ bắt được khi có anchor (Họ và tên:, Ông/Bà, Đại diện:, Người lao động:).
  Tên đứng một mình trong câu không bị bắt.
- Số điện thoại bàn có mã vùng 02x chưa hỗ trợ; chỉ di động 10 số (hoặc +84).
- Tên pháp nhân dừng ở dấu , ; : ( ) hoặc từ nối (có, do, được, là...), nên "Co., Ltd" sau dấu
  phẩy còn sót.
- Địa chỉ cần anchor có dấu ':' và có từ hành chính/đường phố trong giá trị.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

PII_MASKING_VERSION = "pii_draft_0.2"


# ==============================================================================
# 1. PII TYPES, PLACEHOLDER (TDD §10.1)
# ==============================================================================


class PiiType(str, Enum):
    PERSON_NAME = "PERSON_NAME"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    NATIONAL_ID_OR_PASSPORT = "NATIONAL_ID_OR_PASSPORT"
    RESIDENTIAL_ADDRESS = "RESIDENTIAL_ADDRESS"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    LEGAL_ENTITY = "LEGAL_ENTITY"


@dataclass(frozen=True)
class PiiSpan:
    """Vị trí PII trên canonical_text (code point, end exclusive)."""

    type: PiiType
    start: int
    end: int


@dataclass(frozen=True)
class MaskResult:
    """Kết quả che PII. Không lưu bảng ánh xạ ngược."""

    masked_text: str
    pii_spans: list[PiiSpan]


TYPE_TAG: dict[PiiType, str] = {
    PiiType.PERSON_NAME: "<NAME>",
    PiiType.DATE_OF_BIRTH: "<DOB>",
    PiiType.NATIONAL_ID_OR_PASSPORT: "<ID>",
    PiiType.RESIDENTIAL_ADDRESS: "<ADDR>",
    PiiType.PHONE: "<PHONE>",
    PiiType.EMAIL: "<EMAIL>",
    PiiType.BANK_ACCOUNT: "<BANK>",
    PiiType.LEGAL_ENTITY: "<ORG>",
}

TYPE_SHORT_CODE: dict[PiiType, str] = {
    PiiType.PERSON_NAME: "N",
    PiiType.DATE_OF_BIRTH: "D",
    PiiType.NATIONAL_ID_OR_PASSPORT: "I",
    PiiType.RESIDENTIAL_ADDRESS: "R",
    PiiType.PHONE: "P",
    PiiType.EMAIL: "E",
    PiiType.BANK_ACCOUNT: "B",
    PiiType.LEGAL_ENTITY: "O",
}


# ==============================================================================
# 2. REGEX (TDD §10.2)
# Quy ước: mỗi pattern có nhóm có tên `v` = phần giá trị cần mask; anchor nằm ngoài `v`.
# Cờ (?i) chỉ bọc anchor bằng (?i:...). Không dùng (?i) toàn pattern vì sẽ làm [A-Z] khớp chữ
# thường và biến cả câu ("có quyền được nghỉ...") thành "tên".
# Khoảng trắng giữa anchor và giá trị dùng [ \t], không dùng \s, để không vượt qua dòng.
# ==============================================================================

_UP = (
    "A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ"
)  # chữ hoa tiếng Việt, dạng dựng sẵn (NFC)
_LO = "a-zàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ"

# Một từ trong tên người: Viết-hoa-đầu ("Nguyễn", "A") hoặc TOÀN CHỮ HOA ("NGUYỄN").
_NAME_TOKEN = rf"(?:[{_UP}]{{2,}}|[{_UP}][{_LO}]*)\b"
_HONORIFIC = r"(?i:ông/bà|ông|bà|anh|chị)"
_SEP = r"[ \t]*[:：][ \t]*"  # dấu hai chấm bắt buộc


def _name(min_tokens: int, max_tokens: int = 7) -> str:
    return rf"{_NAME_TOKEN}(?:[ \t]+{_NAME_TOKEN}){{{min_tokens - 1},{max_tokens - 1}}}"


# Từ nối đánh dấu hết tên pháp nhân. Không gồm "và" vì "Thương mại và Dịch vụ ABC" là tên.
_ORG_STOP = (
    r"(?:có|do|được|là|sau|địa|mã|trụ|đại|đã|sẽ|thuộc|gọi|cùng|ký|thỏa|với|"
    r"và[ \t]+(?:người|ông|bà))"
)
_ORG_FORM = (
    r"(?:[ \t]+(?i:cổ[ \t]+phần|tnhh(?:[ \t]+một[ \t]+thành[ \t]+viên|[ \t]+mtv)?|"
    r"trách[ \t]+nhiệm[ \t]+hữu[ \t]+hạn(?:[ \t]+một[ \t]+thành[ \t]+viên)?|mtv|hợp[ \t]+danh|"
    r"tư[ \t]+nhân|liên[ \t]+doanh))*"
)

# Phần "high precision" quét trước. is_high_precision=True khi resolve overlap.
_PATTERNS_HIGH: list[tuple[PiiType, re.Pattern[str]]] = [
    (
        PiiType.EMAIL,
        re.compile(
            r"(?<![\w.%+-])(?P<v>[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+"
            r"(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})(?![\w-])"
        ),
    ),
    (
        # 10 số di động VN hoặc +84; chấp nhận dấu cách, dấu chấm, gạch nối giữa các số
        # (0912 345 678, 0912.345.678, 091-234-5678, +84 912 345 678).
        PiiType.PHONE,
        re.compile(r"(?<![\d.])(?P<v>(?:\+?84|0)[ .-]?[35789](?:[ .-]?\d){8})(?!\d)"),
    ),
    (
        # CCCD 12 số, không cần anchor (đầu 0 + mã tỉnh 001..096 + 1 số thế kỷ/giới 0..3).
        PiiType.NATIONAL_ID_OR_PASSPORT,
        re.compile(r"(?<!\d)(?P<v>0(?:0[1-9]|[1-8]\d|9[0-6])[0-3]\d{8})(?!\d)"),
    ),
    (
        # CMND 9 số / CCCD 12 số / hộ chiếu (1 chữ + 7-8 số) có anchor.
        PiiType.NATIONAL_ID_OR_PASSPORT,
        re.compile(
            r"(?i:cmnd|cmt|cccd|căn[ \t]+cước(?:[ \t]+công[ \t]+dân)?|"
            r"chứng[ \t]+minh(?:[ \t]+nhân[ \t]+dân|[ \t]+thư)?|hộ[ \t]+chiếu|passport|"
            r"số[ \t]+định[ \t]+danh(?:[ \t]+cá[ \t]+nhân)?)"
            r"(?:[ \t]*(?i:số|no\.?))?[ \t]*[:：]?[ \t]*(?P<v>\d{12}|\d{9}|[A-Z]\d{7,8})(?!\d)"
        ),
    ),
    (
        PiiType.BANK_ACCOUNT,
        re.compile(
            r"(?i:stk|số[ \t]+tài[ \t]+khoản|số[ \t]+tk|tài[ \t]+khoản(?:[ \t]+ngân[ \t]+hàng)?)"
            r"(?:[ \t]*\([^)\n]{0,20}\))?[ \t]*[:：]?[ \t]*(?P<v>\d(?:[ .-]?\d){7,18})(?!\d)"
        ),
    ),
    (
        # Ngày sinh: BẮT BUỘC anchor, để không mask ngày hiệu lực, ngày ký (TDD §10.2 preserve).
        PiiType.DATE_OF_BIRTH,
        re.compile(
            r"(?i:ngày[ \t]+tháng[ \t]+năm[ \t]+sinh|ngày[ \t]+sinh|sinh[ \t]+ngày|"
            r"sinh[ \t]+năm|d\.?o\.?b)"
            r"[ \t]*[:：]?[ \t]*(?P<v>"
            r"\d{1,2}[/\-.]\d{1,2}[/\-.](?:19|20)\d{2}"
            r"|\d{1,2}[ \t]+tháng[ \t]+\d{1,2}[ \t]+năm[ \t]+(?:19|20)\d{2}"
            r"|(?:19|20)\d{2})(?!\d)"
        ),
    ),
    (
        PiiType.RESIDENTIAL_ADDRESS,
        re.compile(
            r"(?i:địa[ \t]+chỉ(?:[ \t]+(?:thường[ \t]+trú|cư[ \t]+trú|hiện[ \t]+tại|"
            r"liên[ \t]+(?:lạc|hệ)|nơi[ \t]+ở))?|"
            r"nơi[ \t]+(?:thường[ \t]+trú|cư[ \t]+trú|ở)|hộ[ \t]+khẩu[ \t]+thường[ \t]+trú|"
            r"chỗ[ \t]+ở(?:[ \t]+hiện[ \t]+nay)?)"
            + _SEP
            + r"(?P<v>[^\r\n]+)"
        ),
    ),
]

# Heuristic entity quét sau. Chỉ mask giá trị, không mask từ vai trò.
_PATTERNS_HEURISTIC: list[tuple[PiiType, re.Pattern[str]]] = [
    (  # Trường khai báo rõ ràng: cho phép tên 1 từ.
        PiiType.PERSON_NAME,
        re.compile(
            r"(?i:họ[ \t]+(?:và[ \t]+)?tên(?:[ \t]+người[ \t]+lao[ \t]+động)?)"
            + _SEP
            + rf"(?:{_HONORIFIC}[ \t]+)?(?P<v>{_name(1)})"
        ),
    ),
    (  # Anchor vai trò + ':' : cần >= 2 từ để không bắt "Người lao động: Có quyền ...".
        PiiType.PERSON_NAME,
        re.compile(
            r"(?i:đại[ \t]+diện(?:[ \t]+(?:bởi|là|theo[ \t]+pháp[ \t]+luật))?|"
            r"người[ \t]+lao[ \t]+động|nlđ)"
            + _SEP
            + rf"(?:{_HONORIFIC}[ \t]+)?(?P<v>{_name(2)})"
        ),
    ),
    (  # Danh xưng + tên: "Ông Nguyễn Văn An", "Bà Trần Thị B".
        PiiType.PERSON_NAME,
        re.compile(rf"(?<![{_UP}{_LO}]){_HONORIFIC}[ \t]*[:：]?[ \t]+(?P<v>{_name(2)})"),
    ),
    (  # Công ty/Tập đoàn + tên riêng; giá trị phải bắt đầu bằng chữ hoa hoặc số,
        # nên "Công ty có quyền" không khớp.
        PiiType.LEGAL_ENTITY,
        re.compile(
            r"(?<![\w])(?i:tổng[ \t]+công[ \t]+ty|công[ \t]+ty|tập[ \t]+đoàn)"
            + _ORG_FORM
            + rf"[ \t]+(?P<v>[{_UP}0-9][^\r\n,;:()]{{0,79}}?)"
            + rf"(?=[ \t]*(?:[,;:()\r\n.]|$)|[ \t]+{_ORG_STOP}\b)"
        ),
    ),
    (  # Mã số thuế (định danh pháp nhân).
        PiiType.LEGAL_ENTITY,
        re.compile(r"(?i:mst|mã[ \t]+số[ \t]+thuế)[ \t]*[:：]?[ \t]*(?P<v>\d{10}(?:-\d{3})?)(?!\d)"),
    ),
]

# Địa chỉ chỉ nhận khi giá trị có dấu hiệu địa chỉ (chặn "nơi ở: do công ty bố trí").
_ADDRESS_HINT = re.compile(
    r"(?i)\b(?:xã|phường|thị[ \t]+trấn|quận|huyện|thị[ \t]+xã|tỉnh|thành[ \t]+phố|tp\.?|"
    r"đường|phố|ngõ|ngách|hẻm|thôn|xóm|ấp|khu[ \t]+phố|tổ)\b"
)

# Cắt đuôi tên khi regex lỡ ăn sang nhãn trường kế tiếp ("... Văn An Chức vụ").
_NAME_STOP_TOKENS = frozenset(
    {"chức", "sinh", "địa", "số", "điện", "email", "quốc", "cmnd", "cccd", "mst", "ngày",
     "năm", "vụ"}
)

# Preserve-list (TDD §10.2): giá trị đúng bằng các cụm này không bị mask.
PRESERVE_LIST: frozenset[str] = frozenset(
    {
        "người lao động", "nld", "nlđ", "người sử dụng lao động", "nsdld", "nsdlđ",
        "giám đốc", "tổng giám đốc", "trưởng phòng", "kế toán trưởng", "nhân viên",
        "lương", "phụ cấp", "bảo hiểm", "giờ làm", "công ty", "doanh nghiệp",
    }
)  # fmt: skip


# ==============================================================================
# 3. DETECTOR
# ==============================================================================


def _require_nfc(text: str) -> None:
    """canonical_text phải đã NFC. Không tự chuẩn hóa: đổi độ dài sẽ phá INV-02/INV-03."""
    if unicodedata.normalize("NFC", text) != text:
        raise ValueError("canonical_text phải ở dạng NFC trước khi mask")


def _is_preserved(value: str) -> bool:
    return value.strip().lower() in PRESERVE_LIST


def _trim_name(value: str) -> str:
    tokens = value.split()
    for i, tok in enumerate(tokens):
        if i >= 1 and tok.lower() in _NAME_STOP_TOKENS:
            return " ".join(tokens[:i])
    return value


def _resolve_overlaps(candidates: list[tuple[PiiSpan, bool]]) -> list[PiiSpan]:
    """Triệt overlap (TDD §10.2): high-precision trước, rồi span dài hơn, rồi start nhỏ hơn.

    Trả list đã sort theo start, không chồng lấn.
    """
    ranked = sorted(
        candidates,
        key=lambda c: (not c[1], -(c[0].end - c[0].start), c[0].start),
    )
    accepted: list[PiiSpan] = []
    for span, _ in ranked:
        if all(span.end <= a.start or span.start >= a.end for a in accepted):
            accepted.append(span)
    accepted.sort(key=lambda s: s.start)
    return accepted


def detect(canonical_text: str) -> list[PiiSpan]:
    """Phát hiện PII trên canonical_text (đã NFC): high-precision, heuristic, rồi resolve."""
    _require_nfc(canonical_text)
    found: list[tuple[PiiSpan, bool]] = []

    for rules, high in ((_PATTERNS_HIGH, True), (_PATTERNS_HEURISTIC, False)):
        for pii_type, pattern in rules:
            for m in pattern.finditer(canonical_text):
                start, end = m.span("v")
                value = canonical_text[start:end]
                if pii_type is PiiType.PERSON_NAME:
                    value = _trim_name(value)
                value = value.rstrip()  # địa chỉ cuối dòng có thể còn khoảng trắng
                if not value or _is_preserved(value):
                    continue
                if pii_type is PiiType.RESIDENTIAL_ADDRESS and not _ADDRESS_HINT.search(value):
                    continue
                found.append((PiiSpan(pii_type, start, start + len(value)), high))

    return _resolve_overlaps(found)


# ==============================================================================
# 4. MASKER VÀ BOUNDARY GUARD
# ==============================================================================


def mask_value(text: str, pii_type: PiiType) -> str:
    """Placeholder cùng độ dài với `text` (TDD §10.1): tag + '_', hoặc mã 1 chữ nếu quá ngắn."""
    n = len(text)
    tag = TYPE_TAG[pii_type]
    if n >= len(tag):
        return tag + "_" * (n - len(tag))
    return TYPE_SHORT_CODE[pii_type] * n


def mask(canonical_text: str) -> MaskResult:
    """Che PII trên toàn bộ canonical_text. len(masked_text) == len(canonical_text) (INV-02)."""
    spans = detect(canonical_text)
    pieces: list[str] = []
    cursor = 0
    for span in spans:
        pieces.append(canonical_text[cursor : span.start])
        pieces.append(mask_value(canonical_text[span.start : span.end], span.type))
        cursor = span.end
    pieces.append(canonical_text[cursor:])
    masked = "".join(pieces)
    if len(masked) != len(canonical_text):  # không dùng assert: -O sẽ bỏ qua
        raise RuntimeError("Vi phạm INV-02: độ dài masked_text khác canonical_text")
    return MaskResult(masked_text=masked, pii_spans=spans)


def boundary_guard(pos: int, pii_spans: list[PiiSpan]) -> bool:
    """TDD §10.3: False nếu start < pos < end của span nào đó (biên rơi vào trong placeholder)."""
    return not any(span.start < pos < span.end for span in pii_spans)


def adjust_boundary(pos: int, pii_spans: list[PiiSpan]) -> int:
    """Dời biên ra đầu/cuối span nếu rơi vào trong placeholder (hòa thì về đầu)."""
    for span in pii_spans:
        if span.start < pos < span.end:
            return span.start if pos - span.start <= span.end - pos else span.end
    return pos
