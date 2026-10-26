"""C-01 (a): segment() trên 6 hợp đồng thật của data repo (submodule `ai_pipeline/data`).

Chỉ kiểm bất biến (INV-02/03, ≤150 clause, độ dài giữ nguyên sau che PII), KHÔNG chấm F1/M1 —
dataset v06 không phải gold segmentation (DATA_PLAN §4). Bỏ qua nếu chưa kéo submodule.
"""

import unicodedata
from pathlib import Path

import pytest
from app.clause.segmenter import MAX_CLAUSES, segment
from app.privacy.masker import mask

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "ai_pipeline" / "data" / "data" / "processed" / "raw_text"
FILES = sorted(RAW_DIR.glob("HDLD00[1-6].txt")) if RAW_DIR.exists() else []

pytestmark = pytest.mark.skipif(
    not FILES, reason="submodule ai_pipeline/data chưa được kéo (git submodule update --init)"
)


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_invariants_hold_on_real_contract(path):
    text = unicodedata.normalize("NFC", path.read_text(encoding="utf-8"))
    masked = mask(text)
    assert len(masked.masked_text) == len(text)  # INV-01

    result = segment(text, masked.masked_text, masked.pii_spans)
    clauses = result.clauses
    assert 0 < len(clauses) <= MAX_CLAUSES

    prev_end = 0
    for c in clauses:
        assert text[c.start_char : c.end_char] == c.original_text  # INV-02
        assert c.start_char >= prev_end and c.end_char > c.start_char  # INV-03
        for span in masked.pii_spans:  # không ranh giới trong placeholder
            assert not (span.start < c.start_char < span.end)
            assert not (span.start < c.end_char < span.end)
        prev_end = c.end_char

    # Không mất chữ: mọi ký tự khác khoảng trắng thuộc đúng một clause.
    covered = sum(1 for c in clauses for ch in c.original_text if not ch.isspace())
    assert covered == sum(1 for ch in text if not ch.isspace())
