"""P1 trên D1 thật (HDLD001-004), W4 N3 X-18. Cần submodule dữ liệu; thiếu thì SKIP (như các test integration khác).

Job `test` của CI không kéo submodule nên skip; job `data` kéo submodule và chạy file này.
"""

import unicodedata

import pytest
from app.privacy.masker import mask

from ai_pipeline.eval.p1 import build_p1
from ai_pipeline.eval.p1.generator import _base_docs, generate

D1 = build_p1.D1_RAW
pytestmark = pytest.mark.skipif(
    not all((D1 / f"{doc}.txt").exists() for doc in build_p1.D1_DOCS),
    reason="thiếu submodule ai_pipeline/data",
)


def test_real_d1_base_documents_have_no_pii_before_insertion():
    for name, text in _base_docs(build_p1.load_d1(D1)).items():
        assert mask(text).pii_spans == [], name


def test_real_d1_generation_keeps_invariants_at_default_sizes():
    """generate() tự kiểm canonical, offset và NFD khi sinh; chạy cỡ mặc định để bắt lỗi trên D1 thật."""
    samples = generate(build_p1.load_d1(D1), 17, 100, 50, 100)
    assert len(samples) == 5 * 100 + 7 * 50 + 100
    for s in samples:
        assert unicodedata.normalize("NFC", s.canonical_text) == s.canonical_text
        for g in s.pii_spans + s.preserve_spans:
            assert s.canonical_text[g["start_char"] : g["end_char"]] == g["text"]
