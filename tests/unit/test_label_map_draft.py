"""Nháp label_map (N3, X-17/X-24): cấu trúc, tham chiếu và trạng thái DRAFT. Không nối vào corpus loader."""

import hashlib
import json
import re
from pathlib import Path

import yaml
from app.clause.taxonomy import CLAUSE_LABELS

ROOT = Path(__file__).resolve().parents[2]
DRAFT = ROOT / "data" / "label_map.yaml"
CORPUS = ROOT / "data" / "legal_corpus"
_ID = re.compile(r"^[A-Z][A-Z0-9_]*:art[0-9]+$")
EXPECTED_ARTICLES = frozenset({
    5, 8, 14, 17, 20, 21, 24, 25, 26, 27, 29, 33, 35, 36, 40, 41, 46, 47, 48, 49, 61, 62,
    94, 95, 96, 97, 98, 101, 104, 105, 107, 109, 110, 111, 112, 113, 114, 115,
    118, 119, 120, 121, 129, 137, 138,
})


def _load():
    return yaml.safe_load(DRAFT.read_text(encoding="utf-8"))


def test_keys_are_the_clause_labels():
    assert set(_load()) <= set(CLAUSE_LABELS)


def test_ids_are_article_level_and_only_blld2019():
    ids = {cid for weights in _load().values() for cid in weights}
    assert ids and all(_ID.match(cid) for cid in ids)
    assert {cid.split(":")[0] for cid in ids} == {"BLLD2019"}


def test_weights_are_in_unit_interval():
    for weights in _load().values():
        for w in weights.values():
            assert isinstance(w, float) and 0 < w <= 1


def test_articles_match_frozen_table():
    ids = {cid for weights in _load().values() for cid in weights}
    assert {int(cid.split("art")[1]) for cid in ids} == set(EXPECTED_ARTICLES)


def test_draft_is_marked_and_pending_items_are_listed():
    text = DRAFT.read_text(encoding="utf-8")
    assert text.startswith("# DRAFT")
    assert text.count("PENDING") >= 2


def test_draft_is_not_loadable_until_provisions_are_expanded():
    """Guard: ID cấp Điều chưa có trong provisions nên validate_corpus sẽ từ chối; chỉ nạp sau X-24."""
    known = {json.loads(line)["citation_id"] for line in (CORPUS / "provisions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()}
    ids = {cid for weights in _load().values() for cid in weights}
    assert not ids <= known


def test_new_files_do_not_hardcode_the_legacy_risk_label_name():
    assert "POST_EMPLOYMENT_RESTRICTION" not in DRAFT.read_text(encoding="utf-8")
