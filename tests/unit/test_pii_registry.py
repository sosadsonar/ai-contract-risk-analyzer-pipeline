"""M2 (N3): mỗi PiiType có đúng một tag và một mã ngắn, không trùng nhau."""

from app.privacy.pii_types import TYPE_SHORT_CODE, TYPE_TAG, PiiType


def test_every_type_has_unique_tag_and_short_code():
    assert set(TYPE_TAG) == set(PiiType)
    assert set(TYPE_SHORT_CODE) == set(PiiType)
    assert len(set(TYPE_TAG.values())) == len(PiiType)
    assert len(set(TYPE_SHORT_CODE.values())) == len(PiiType)
    assert all(len(v) == 1 for v in TYPE_SHORT_CODE.values())
