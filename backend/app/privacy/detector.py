"""Phát hiện PII trên canonical_text: regex có anchor (high precision) rồi heuristic, và
resolve overlap (TDD §10.2). Bản đầu của C-09 (a); C-09 (b) sửa MST bị gán PHONE.

Giới hạn đã biết (cần đo trên D1, SRS OI-12):
- Tên người chỉ bắt được khi có anchor (Họ và tên:, Ông/Bà, Đại diện:, Người lao động:).
  Tên đứng một mình trong câu không bị bắt.
- Số điện thoại: di động 10 số, bàn 02x (11 số kể cả 0), hoặc +84; số quốc tế khác chưa hỗ trợ.
- Tên pháp nhân dừng ở dấu , ; : ( ) hoặc từ nối (có, do, được, là...), nên "Co., Ltd" sau dấu
  phẩy còn sót.
- Địa chỉ cần anchor có dấu ':' và có từ hành chính/đường phố trong giá trị.
- TAX_ID (a): MST 10 hoặc 13 số, bắt buộc có anchor; số 10 chữ số không anchor vẫn có thể là PHONE.
- ID_ISSUE (b): chỉ khi có nhãn "cấp ngày", "nơi cấp:", "cấp tại:" hoặc dòng "Tại:" ngay sau dòng "Cấp ngày".
- Địa chỉ (c): anchor chung "địa chỉ" được phân loại theo tiêu đề Bên A/Bên B gần nhất trong 400 ký tự; không thấy tiêu đề thì RESIDENTIAL_ADDRESS.
- SIGNATURE (d): chỉ tên in dưới khối ký trong 20% cuối văn bản; không bắt chữ ký tay.
- LEGAL_ENTITY (e): chỉ che tên riêng, không che loại hình (TNHH, Cổ phần...); tên không được là từ loại hình.
- Tỉnh/thành đứng riêng, không có số hay từ chỉ chi tiết, không bị che (f).
- Cờ high chỉ quyết định thứ tự giải trùng (_resolve_overlaps), không quyết định nhóm đo.
"""

from __future__ import annotations

import re
import unicodedata

from app.privacy.pii_types import PiiSpan, PiiType

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
        # Mã số thuế (định danh pháp nhân) có anchor. Phải đứng TRƯỚC PHONE: MST 10 số như
        # 0312345678 trùng dạng số di động; cả hai cùng high-precision nên khi hai span trùng
        # nhau _resolve_overlaps giữ ứng viên đứng trước trong danh sách này.
        PiiType.TAX_ID,
        re.compile(r"(?i:mst|mã[ \t]+số[ \t]+thuế)[ \t]*[:：]?[ \t]*(?P<v>\d{10}(?:-?\d{3})?)(?!\d)"),
    ),
    (
        PiiType.EMAIL,
        re.compile(
            r"(?<![\w.%+-])(?P<v>[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+"
            r"(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})(?![\w-])"
        ),
    ),
    (
        # Di động VN 10 số (đầu 03/05/07/08/09) hoặc +84; bàn có mã vùng 02x (024, 028, 0203...) là
        # 0 + 10 số. Chấp nhận dấu cách, chấm, gạch nối giữa các số (0912 345 678, 091-234-5678,
        # +84 912 345 678, 024 3825 1234, 024.38251234). MST/CCCD không khớp vì khác số chữ số.
        PiiType.PHONE,
        re.compile(
            r"(?<![\d.])(?P<v>(?:\+?84|0)[ .-]?(?:[35789](?:[ .-]?\d){8}|2\d(?:[ .-]?\d){8})"
            r"|\(0?2\d\)[ .-]?\d(?:[ .-]?\d){7})(?!\d)"  # (024) 3825 1234
        ),
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
            r"(?i:stk|số[ \t]+tài[ \t]+khoản|số[ \t]+tk|(?:tài[ \t]+khoản|\btk)(?:[ \t]+ngân[ \t]+hàng)?)"
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
            + r"[ \t]+(?!(?i:tnhh|mtv|cổ[ \t]+phần|trách[ \t]+nhiệm|hợp[ \t]+danh|tư[ \t]+nhân|liên[ \t]+doanh)(?!\w))"
            + rf"(?P<v>[{_UP}0-9][^\r\n,;:()]{{0,79}}?)"
            + rf"(?=[ \t]*(?:[,;:()\r\n.]|$)|[ \t]+{_ORG_STOP}\b)"
        ),
    ),
]

# Địa chỉ chỉ nhận khi giá trị có dấu hiệu địa chỉ (chặn "nơi ở: do công ty bố trí").
_ADDRESS_HINT = re.compile(
    r"(?i)\b(?:xã|phường|thị[ \t]+trấn|quận|huyện|thị[ \t]+xã|tỉnh|thành[ \t]+phố|tp\.?|"
    r"đường|phố|ngõ|ngách|hẻm|thôn|xóm|ấp|khu[ \t]+phố|tổ)\b"
)

# Cắt đuôi tên khi regex lỡ ăn sang nhãn trường kế tiếp ("... Văn An Chức vụ").
# Nhiều từ nhãn cũng là tên người thật (Quốc, Năm, Điện, Sinh, Số...), nên chỉ cắt khi từ đó là phần
# đầu của một nhãn: giá trị là tập từ theo sau được phép (None = luôn cắt, vì không là tên người).
_NAME_STOP_FOLLOWERS: dict[str, frozenset[str] | None] = {
    "chức": frozenset({"vụ", "danh"}),
    "quốc": frozenset({"tịch"}),
    "sinh": frozenset({"ngày", "năm"}),
    "ngày": frozenset({"sinh", "tháng", "cấp"}),
    "năm": frozenset({"sinh"}),
    "số": frozenset({"cmnd", "cccd", "điện", "hộ", "căn", "chứng", "tài", "tk", "định"}),
    "điện": frozenset({"thoại"}),
    "địa": frozenset({"chỉ"}),
    "email": None,
    "cmnd": None,
    "cccd": None,
    "mst": None,
}
_NEXT_WORD = re.compile(r"[ \t]+([^\W\d_]+)")

# Preserve-list (TDD §10.2): giá trị đúng bằng các cụm này không bị mask.
PRESERVE_LIST: frozenset[str] = frozenset(
    {
        "người lao động", "nld", "nlđ", "người sử dụng lao động", "nsdld", "nsdlđ",
        "giám đốc", "tổng giám đốc", "trưởng phòng", "kế toán trưởng", "nhân viên",
        "lương", "phụ cấp", "bảo hiểm", "giờ làm", "công ty", "doanh nghiệp",
        "phó giám đốc", "phó tổng giám đốc", "chủ tịch", "chủ tịch hội đồng quản trị",
        "giám đốc nhân sự", "người đại diện theo pháp luật", "chủ hộ",
    }
)  # fmt: skip


# ==============================================================================
# 3. DETECTOR
# ==============================================================================


def _require_nfc(text: str) -> None:
    """canonical_text phải đã NFC. Không tự chuẩn hóa: đổi độ dài sẽ phá INV-01/INV-03."""
    if unicodedata.normalize("NFC", text) != text:
        raise ValueError("canonical_text phải ở dạng NFC trước khi mask")


def _is_preserved(value: str) -> bool:
    return value.strip().lower() in PRESERVE_LIST


_LABEL_COLON_OR_DIGIT = re.compile(r"[ \t]*(?:[:：]|\d)")


def _trim_name(value: str, following: str = "") -> str:
    """Cắt từ `value` tại từ đầu của nhãn trường kế tiếp. `following` = văn bản ngay sau `value`."""
    tokens = value.split()
    for i, tok in enumerate(tokens):
        key = tok.lower()
        if i < 1 or key not in _NAME_STOP_FOLLOWERS:
            continue
        followers = _NAME_STOP_FOLLOWERS[key]
        if followers is None:
            return " ".join(tokens[:i])
        if i + 1 < len(tokens):
            nxt, rest = tokens[i + 1].lower(), None
        else:
            m = _NEXT_WORD.match(following)
            nxt, rest = (m.group(1).lower(), following[m.end() :]) if m else ("", "")
        if nxt not in followers:
            continue
        # "Năm" vừa là tên (Nguyễn Văn Năm) vừa mở đầu nhãn "Năm sinh:": chỉ coi là nhãn khi sau
        # "sinh" có dấu ':' hoặc chữ số; "Năm sinh ngày ..." thì "Năm" là tên.
        if key == "năm" and rest is not None and not _LABEL_COLON_OR_DIGIT.match(rest):
            continue
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


# ==============================================================================
# 3b. PATTERN CHO ID_ISSUE, ĐỊA CHỈ, CHỮ KÝ (P3 b, c, d, f)
# ==============================================================================

_DATE_VN = r"(?:\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4}|\d{1,2}[ \t]+tháng[ \t]+\d{1,2}[ \t]+năm[ \t]+\d{4})"

# ID_ISSUE: chỉ che khi có nhãn. "nơi cấp" và "cấp tại" bắt buộc dấu ':' để không bắt câu thường
# ("được cấp tại Hà Nội" không phải nhãn giấy tờ).
_ISSUE_DATE = re.compile(r"(?i:cấp[ \t]+ngày|ngày[ \t]+cấp)[ \t]*[:：]?[ \t]*(?P<v>" + _DATE_VN + r")(?!\d)")
_ISSUE_PLACE = re.compile(r"(?i:nơi[ \t]+cấp|cấp[ \t]+tại)[ \t]*[:：][ \t]*(?P<v>[^\r\n;]+)")
_ISSUE_NEXT_LINE = re.compile(r"(?im)^[ \t]*cấp[ \t]+ngày[^\r\n]*\r?\n[ \t]*tại[ \t]*[:：][ \t]*(?P<v>[^\r\n;]+)")
_ISSUE_SAME_LINE = re.compile(
    r"(?i:cấp[ \t]+ngày|ngày[ \t]+cấp)[ \t]*[:：]?[ \t]*" + _DATE_VN + r"[ \t]+(?i:tại)[ \t]*[:：]?[ \t]*(?P<v>[^\r\n;]+)"
)


def _issue_candidates(text: str) -> list[tuple[PiiSpan, bool]]:
    """Giá trị ngày/nơi cấp đứng sau nhãn. Bỏ giá trị không có chữ hoặc số (biểu mẫu trống "……")."""
    out: list[tuple[PiiSpan, bool]] = []
    for pattern in (_ISSUE_DATE, _ISSUE_PLACE, _ISSUE_NEXT_LINE, _ISSUE_SAME_LINE):
        for m in pattern.finditer(text):
            start, end = m.span("v")
            value = text[start:end].rstrip()
            if any(ch.isalnum() for ch in value):
                out.append((PiiSpan(PiiType.ID_ISSUE, start, start + len(value)), True))
    return out


# Anchor địa chỉ. Nhóm `anchor` dùng để phân loại BUSINESS/RESIDENTIAL (P3 c).
_ADDRESS_ANCHOR = re.compile(
    r"(?P<anchor>(?i:địa[ \t]+chỉ(?:[ \t]+(?:trụ[ \t]+sở(?:[ \t]+chính)?|công[ \t]+ty|doanh[ \t]+nghiệp|"
    r"thường[ \t]+trú|tạm[ \t]+trú|cư[ \t]+trú|hiện[ \t]+tại|liên[ \t]+(?:lạc|hệ)|nơi[ \t]+ở))?|"
    r"nơi[ \t]+(?:thường[ \t]+trú|tạm[ \t]+trú|cư[ \t]+trú|ở)|"
    r"hộ[ \t]+khẩu(?:[ \t]+thường[ \t]+trú)?|chỗ[ \t]+ở(?:[ \t]+hiện[ \t]+nay)?))"
    + _SEP
    + r"(?P<v>[^\r\n]+)"
)
_PROVINCE_PREFIX = re.compile(r"(?i)^(?:tỉnh|thành[ \t]+phố|tp\.?)[ \t]*")
_ADDRESS_DETAIL = re.compile(r"(?i)(?<!\w)(?:đường|phố|phường|xã|quận|huyện|thôn|ngõ|số|tòa)(?!\w)")
_BUSINESS_HEADER = re.compile(r"(?i)(?<!\w)(?:bên[ \t]+a|người[ \t]+sử[ \t]+dụng[ \t]+lao[ \t]+động|nsdlđ)(?!\w)")
_RESIDENT_HEADER = re.compile(r"(?i)(?<!\w)(?:bên[ \t]+b|người[ \t]+lao[ \t]+động|nlđ)(?!\w)")


def _has_address_detail(value: str) -> bool:
    """Tỉnh/thành đứng riêng (không số, không từ chỉ chi tiết) thì không che (P3 f)."""
    rest = _PROVINCE_PREFIX.sub("", value.strip(), count=1)
    return any(ch.isdigit() for ch in rest) or _ADDRESS_DETAIL.search(rest) is not None


def _address_type(anchor: str, text: str, pos: int) -> PiiType:
    if any(k in anchor for k in ("trụ sở", "công ty", "doanh nghiệp")):
        return PiiType.BUSINESS_ADDRESS
    if anchor in ("địa chỉ", "địa chỉ liên hệ", "địa chỉ liên lạc"):
        best: tuple[int, PiiType] | None = None
        window = text[max(0, pos - 400) : pos]
        for pattern, kind in ((_BUSINESS_HEADER, PiiType.BUSINESS_ADDRESS), (_RESIDENT_HEADER, PiiType.RESIDENTIAL_ADDRESS)):
            for h in pattern.finditer(window):
                if best is None or h.start() > best[0]:
                    best = (h.start(), kind)
        return best[1] if best else PiiType.RESIDENTIAL_ADDRESS
    return PiiType.RESIDENTIAL_ADDRESS


def _address_candidates(text: str) -> list[tuple[PiiSpan, bool]]:
    out: list[tuple[PiiSpan, bool]] = []
    for m in _ADDRESS_ANCHOR.finditer(text):
        start, end = m.span("v")
        value = text[start:end].rstrip()
        if not value or _is_preserved(value) or not _ADDRESS_HINT.search(value):
            continue
        if not _has_address_detail(value):
            continue
        anchor = " ".join(m.group("anchor").lower().split())
        kind = _address_type(anchor, text, m.start("anchor"))
        out.append((PiiSpan(kind, start, start + len(value)), True))
    return out


# SIGNATURE: tên in dưới khối ký ở 20% cuối văn bản. Không bắt chữ ký tay (PDF thường không có).
_SIG_LABEL = re.compile(
    r"(?i:\(ký,[ \t]*ghi[ \t]+rõ[ \t]+họ[ \t]+tên\)|\(ký[ \t]+và[ \t]+ghi[ \t]+rõ[ \t]+họ[ \t]+tên\)|"
    r"\(ký[ \t]+tên\)|ký[ \t]+tên[ \t]*[:：])"
)
_NAME_FULL = re.compile(rf"{_NAME_TOKEN}(?:[ \t]+{_NAME_TOKEN}){{1,4}}")
_SIG_SEGMENT = re.compile(r"\S+(?:[ \t]\S+)*")  # cụm cách nhau bằng đúng một khoảng trắng
_SIG_TITLE_WORDS = frozenset({"người", "lao", "động", "sử", "dụng", "giám", "đốc", "đại", "diện", "bên", "ký"})


# Chức danh bị anchor "Đại diện:"/"Họ và tên:" nhặt nhầm (P5): cặp đầu ("Phó", "Kế") + từ kế tiếp.
_TITLE_FIRST = frozenset({"phó", "tổng", "giám", "chủ", "kế", "trưởng"})
_TITLE_SECOND = frozenset({"giám", "đốc", "tịch", "toán", "hộ", "phòng", "trưởng", "nhân", "viên"})


def _is_job_title(value: str, following: str) -> bool:
    """`following` = văn bản ngay sau giá trị: _trim_name có thể cắt còn một từ ("Kế" của "Kế toán")."""
    tokens = value.lower().split()
    if not tokens or tokens[0] not in _TITLE_FIRST:
        return False
    if len(tokens) >= 2:
        return tokens[1] in _TITLE_SECOND
    m = _NEXT_WORD.match(following)
    return m is not None and m.group(1).lower() in _TITLE_SECOND


def _signature_spans(text: str) -> list[tuple[int, int]]:
    """Phần còn lại của dòng nhãn và tối đa 4 dòng không rỗng sau nhãn; mỗi cụm 2-5 từ là một tên."""
    spans: list[tuple[int, int]] = []
    limit = int(len(text) * 0.8)
    for m in _SIG_LABEL.finditer(text):
        if m.start() < limit:
            continue
        pos, used, label_line = m.end(), 0, True
        while pos <= len(text):
            nl = text.find("\n", pos)
            line_end = len(text) if nl == -1 else nl
            line = text[pos:line_end]
            if not label_line and line.strip():
                used += 1  # tối đa 4 dòng không rỗng SAU dòng nhãn; phần còn lại của dòng nhãn không tính
                if used > 4:
                    break
            label_line = False
            if line.strip():
                for seg in _SIG_SEGMENT.finditer(line):
                    s = seg.group(0)
                    if (
                        _NAME_FULL.fullmatch(s)
                        and not (set(w.lower() for w in s.split()) & _SIG_TITLE_WORDS)
                        and not _is_preserved(s)
                    ):
                        spans.append((pos + seg.start(), pos + seg.end()))
            if nl == -1:
                break
            pos = nl + 1
    return spans


def detect(canonical_text: str) -> list[PiiSpan]:
    """Phát hiện PII trên canonical_text (đã NFC): high-precision, heuristic, rồi resolve."""
    _require_nfc(canonical_text)
    found: list[tuple[PiiSpan, bool]] = []

    for rules, high in ((_PATTERNS_HIGH, True), (_PATTERNS_HEURISTIC, False)):
        if high:
            found.extend(_issue_candidates(canonical_text))
            found.extend(_address_candidates(canonical_text))
        else:
            # SIGNATURE đứng TRƯỚC heuristic: khi trùng span với PERSON_NAME, thứ tự danh sách thắng.
            found.extend((PiiSpan(PiiType.SIGNATURE, s, e), False) for s, e in _signature_spans(canonical_text))
        for pii_type, pattern in rules:
            for m in pattern.finditer(canonical_text):
                start, end = m.span("v")
                value = canonical_text[start:end]
                if pii_type is PiiType.PERSON_NAME:
                    value = _trim_name(value, canonical_text[end : end + 40])
                value = value.rstrip()  # địa chỉ cuối dòng có thể còn khoảng trắng
                if not value or _is_preserved(value):
                    continue
                if pii_type is PiiType.PERSON_NAME and _is_job_title(value, canonical_text[end : end + 40]):
                    continue
                found.append((PiiSpan(pii_type, start, start + len(value)), high))

    return _resolve_overlaps(found)
