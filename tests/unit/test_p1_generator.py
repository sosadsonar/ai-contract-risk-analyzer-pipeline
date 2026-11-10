"""Q4 (N3, F2): bộ sinh P1 - ranh giới import, tái lập, offset, cỡ mẫu, NFD, biến đổi thật, email ASCII."""

import ast
import hashlib
import json
import tempfile
import unicodedata
from pathlib import Path

from app.document.canonicalizer import canonicalize
from app.privacy.masker import mask

from ai_pipeline.eval.p1 import build_p1
from ai_pipeline.eval.p1.generator import _base_docs, doc_sha256, generate, sample_to_doc

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "ai_pipeline" / "eval" / "p1" / "generator.py"
POOLS = ROOT / "ai_pipeline" / "eval" / "p1" / "pools.py"
D1 = build_p1.D1_RAW
GOLDEN_SEED17_SMALL_SHA = "56f360ef4aa66914f9eda21fb5fae30f673fcf6fdd9fa025ea229ca00a445168"


def _texts():
    return build_p1.load_d1(D1)


def test_generator_and_pools_do_not_import_privacy_package():
    for path in (GEN, POOLS):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            for name in names:
                assert not name.startswith("app.privacy"), (path.name, name)


def test_same_seed_gives_identical_documents_and_other_seed_differs():
    texts = _texts()
    a = [sample_to_doc(s) for s in generate(texts, 17, 2, 2, 2)]
    b = [sample_to_doc(s) for s in generate(texts, 17, 2, 2, 2)]
    c = [sample_to_doc(s) for s in generate(texts, 18, 2, 2, 2)]
    assert [doc_sha256(d) for d in a] == [doc_sha256(d) for d in b]
    assert [doc_sha256(d) for d in a] != [doc_sha256(d) for d in c]


def test_golden_sha_of_small_dev_seed_is_fixed():
    docs = [sample_to_doc(s) for s in generate(_texts(), 17, 2, 2, 2)]
    blob = hashlib.sha256("".join(doc_sha256(d) for d in docs).encode("utf-8")).hexdigest()
    assert blob == GOLDEN_SEED17_SMALL_SHA


def test_offsets_point_at_inserted_value_and_text_is_nfc():
    for s in generate(_texts(), 17, 3, 3, 3):
        assert unicodedata.normalize("NFC", s.canonical_text) == s.canonical_text
        for g in s.pii_spans + s.preserve_spans:
            assert s.canonical_text[g["start_char"] : g["end_char"]] == g["text"]


def test_no_tabs_or_trailing_spaces_in_canonical_text():
    for s in generate(_texts(), 17, 3, 3, 3):
        assert "\t" not in s.canonical_text
        assert all(not line.endswith(" ") for line in s.canonical_text.split("\n"))


def test_nfd_input_canonicalizes_back_to_the_gold_text():
    samples = [s for s in generate(_texts(), 17, 6, 6, 6) if s.raw_nfd is not None]
    assert samples and all(s.mutation == "nfd_input" for s in samples)
    for s in samples:
        assert canonicalize([s.raw_nfd]) == s.canonical_text


def test_mutation_is_recorded_only_when_it_really_applied():
    for s in generate(_texts(), 17, 4, 4, 4):
        doc = sample_to_doc(s)
        assert doc["mutation_applied"] == (s.mutation != "clean")
        if s.mutation == "newline_in_value":
            assert s.kind in ("NATIONAL_ID_OR_PASSPORT", "PHONE", "BANK_ACCOUNT", "TAX_ID")
            assert len(s.pii_spans) == 2
            left, right = s.pii_spans
            assert left["end_char"] + 1 == right["start_char"]
            assert s.canonical_text[left["end_char"]] == "\n"
        if s.mutation == "digit_groups":
            assert len(s.pii_spans) == 1 and s.pii_spans[0]["text"].replace(" ", "").isdigit()


def test_newline_gold_never_contains_the_newline_character():
    for s in generate(_texts(), 17, 6, 6, 6):
        for g in s.pii_spans:
            assert "\n" not in g["text"]


def test_emails_are_ascii_only():
    for s in generate(_texts(), 17, 20, 1, 1):
        for g in s.pii_spans:
            if g["pii_type"] == "EMAIL":
                assert g["text"].isascii(), g["text"]


def test_default_sample_sizes_meet_brd_73_minimums():
    counts = {}
    for s in generate(_texts(), 17, 100, 50, 100):
        counts[s.kind] = counts.get(s.kind, 0) + 1
    for kind in ("NATIONAL_ID_OR_PASSPORT", "PHONE", "EMAIL", "BANK_ACCOUNT", "TAX_ID"):
        assert counts[kind] >= 100, kind
    for kind in ("PERSON_NAME", "DATE_OF_BIRTH", "RESIDENTIAL_ADDRESS", "LEGAL_ENTITY", "ID_ISSUE",
                 "BUSINESS_ADDRESS", "SIGNATURE"):
        assert counts[kind] >= 50, kind
    assert counts["PRESERVE"] >= 100


def test_masker_runs_on_every_clean_sample_without_error():
    for s in generate(_texts(), 17, 2, 2, 2):
        if s.mutation == "clean":
            mask(s.canonical_text)


def test_base_documents_have_no_pii_before_insertion():
    for name, text in _base_docs(_texts()).items():
        assert mask(text).pii_spans == [], name


def test_build_writes_manifest_with_requested_counts():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "p1"
        m = build_p1.build(out, _texts(), 17, 1, 1, 1)
        assert m["documents"] == 5 + 7 + 1
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["seed"] == 17 and len(manifest["entries"]) == manifest["documents"]
        assert not str(out).startswith(str(ROOT / "build"))


def test_runner_reports_two_lanes_and_misses_are_synthetic_only():
    from ai_pipeline.eval import eval_p1
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "p1"
        build_p1.build(out, _texts(), 17, 2, 2, 2)
        r = eval_p1.run(out / "docs", _texts())
        assert set(r["lanes"]) == {"realistic", "stress"}
        assert r["preserve"]["total"] == 2
        for lane in r["lanes"].values():
            for m in lane["misses"]:
                assert m["mutation"] in ("clean", "upper", "nfd_input", "newline_in_value", "digit_groups")
