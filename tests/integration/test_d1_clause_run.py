"""W4: pipeline D1 cục bộ tới Clause Classification với provider giả (cần submodule dữ liệu)."""

import asyncio
from pathlib import Path

import pytest
from app.core.config import Settings

from ai_pipeline.evaluation.d1_clause_run import (
    DATA_ROOT,
    OtherProvider,
    load_d1,
    offset_mapper,
    run_all,
)

pytestmark = pytest.mark.skipif(
    not (DATA_ROOT / "processed" / "clauses_v06.csv").exists(), reason="thiếu submodule ai_pipeline/data"
)
CFG = Settings(GEMINI_MODEL_ID="smoke", _env_file=None)


def test_offset_mapper_handles_deletions_and_nfc():
    raw = "abc  \nđ\u0063\u0302d"  # có khoảng trắng cuối dòng và ký tự tổ hợp
    import unicodedata

    canon = unicodedata.normalize("NFC", "abc\nđĉd")
    mp = offset_mapper(raw, canon)
    assert mp(0) == 0 and mp(len(raw)) == len(canon)
    assert all(0 <= mp(i) <= len(canon) for i in range(len(raw) + 1))


def test_d1_gold_spans_map_inside_canonical_and_are_ordered():
    d1 = load_d1()
    assert sorted(d1) == ["HDLD001", "HDLD002", "HDLD003", "HDLD004"]  # BRD 0.6 §8.2
    for canon, gold in d1.values():
        assert gold and all(0 <= g.start < g.end <= len(canon) for g in gold)


def test_t1_contract_is_refused():
    with pytest.raises(ValueError, match="T1"):
        load_d1(contracts=("HDLD001", "HDLD005"))


def test_smoke_run_covers_all_d1_contracts_and_graph_inv():
    rep = asyncio.run(run_all(OtherProvider(), CFG, Path(DATA_ROOT), measured=False))
    assert rep["mode"] == "SMOKE_NOT_A_MEASUREMENT" and rep["m7_preliminary"] is None
    pc = rep["per_contract"]
    assert len(pc) == 4
    for c in pc:
        assert c["graph_next"] == c["clauses"] - 1 and c["segmentation_warnings"] == 0
    assert rep["cost"]["calls"] == sum(-(-c["clauses"] // 20) for c in pc)  # ceil(clauses/20) mỗi hợp đồng
    assert rep["version_pins"]["taxonomy_version"] == "clause_taxonomy_v03"


def test_measured_flag_produces_m7_block_with_pins():
    rep = asyncio.run(run_all(OtherProvider(), CFG, Path(DATA_ROOT), measured=True))
    assert rep["mode"] == "MEASUREMENT_PRELIMINARY_D1" and rep["m7_preliminary"]["gold_total"] == 174
