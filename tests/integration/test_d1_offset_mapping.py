"""Hồi quy: ánh xạ offset gold (raw_text) → canonical_text trên D1 (HDLD001–004), W4 N1.

Dataset v06 tính offset trên file raw_text (không chuẩn NFC, còn khoảng trắng cuối dòng) còn pipeline
chạy trên canonical_text. Test kiểm 174 span EXACT: nội dung sau ánh xạ phải khớp nội dung raw (so sau
khi gộp khoảng trắng và ép NFC — hai việc canonicalize cố ý làm), và span giữ thứ tự/không rỗng.
Cần submodule dữ liệu; thiếu thì SKIP (không pass ngầm).
"""

import csv
import unicodedata

import pytest
from app.document.canonicalizer import canonicalize

from ai_pipeline.evaluation.d1_clause_run import D1_CONTRACTS, DATA_ROOT, offset_mapper

CSV_PATH = DATA_ROOT / "processed" / "clauses_v06.csv"

pytestmark = pytest.mark.skipif(not CSV_PATH.exists(), reason="thiếu submodule ai_pipeline/data")


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", " ".join(s.split()))


def test_d1_exact_spans_keep_content_after_mapping():
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    total = 0
    for cid in D1_CONTRACTS:
        raw = (DATA_ROOT / "processed" / "raw_text" / f"{cid}.txt").read_text(encoding="utf-8")
        canon = canonicalize([raw])
        mp = offset_mapper(raw, canon)
        for r in (r for r in rows if r["contract_id"] == cid and r["offset_quality"] == "EXACT"):
            total += 1
            rs, re_ = int(r["start_offset"]), int(r["end_offset"])
            cs, ce = mp(rs), mp(re_)
            assert 0 <= cs < ce <= len(canon), (cid, r["clause_id"])
            assert _norm(raw[rs:re_]) == _norm(canon[cs:ce]), (cid, r["clause_id"])
    assert total == 174  # BRD 0.6 §8.2: D1 = HDLD001–004


def test_mapper_is_monotonic_on_every_d1_contract():
    for cid in D1_CONTRACTS:
        raw = (DATA_ROOT / "processed" / "raw_text" / f"{cid}.txt").read_text(encoding="utf-8")
        mp = offset_mapper(raw, canonicalize([raw]))
        vals = [mp(i) for i in range(0, len(raw) + 1, 7)]
        assert vals == sorted(vals)
