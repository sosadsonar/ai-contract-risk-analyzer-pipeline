"""PR #30 note: anchor "TK ngân hàng:" bị sót ở P1 realistic (50/65) → pii_draft_0.5.

Chỉ là test hồi quy trên chuỗi viết tay. Số recall phải đo lại trên P1 bằng seed KHÁC 17 và trên T1 gold
(OI-12 §5.3); không báo lại số trên seed 17 sau khi đã sửa detector theo chính seed đó."""

import pytest
from app.privacy.detector import detect
from app.privacy.masker import PII_MASKING_VERSION
from app.privacy.pii_types import PiiType


def _bank(text):
    return [text[s.start:s.end] for s in detect(text) if s.type == PiiType.BANK_ACCOUNT]


@pytest.mark.parametrize("text,value", [
    ("TK ngân hàng: 0123456789012", "0123456789012"),
    ("Số TK: 0123 456 789", "0123 456 789"),
    ("tk ngân hàng 9704 1234 5678", "9704 1234 5678"),
    ("Số tài khoản: 0011002233", "0011002233"),
])
def test_bank_account_short_anchor(text, value):
    assert _bank(text) == [value]


def test_tk_inside_word_is_not_anchor():
    assert _bank("Mã TKB ngân hàng 20261111") == []


def test_version_bumped():
    assert PII_MASKING_VERSION == "pii_draft_0.5"
