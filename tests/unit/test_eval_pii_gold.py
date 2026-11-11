"""G2 (N3, F1): CLI đo gold D1/T1. Dữ liệu tổng hợp lấy từ fixture case_001; không đọc restricted/ thật."""

import hashlib
import json
import tempfile
import unicodedata
from pathlib import Path

from app.document.canonicalizer import canonicalize

from ai_pipeline.eval.eval_pii_gold import main

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "privacy" / "case_001.json"


def _case():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _gold(case, *, extra=None, status=None, sha=None):
    obj = {
        "pii_spans": [{"pii_type": s["type"], "start_char": s["start"], "end_char": s["end"]} for s in case["pii_spans"]],
        "preserve_spans": [{"start_char": s["start"], "end_char": s["end"]} for s in case["preserve_spans"]],
    }
    if extra:
        obj["pii_spans"].extend(extra)
    if status is not None:
        obj["status"] = status
    if sha is not None:
        obj["source_sha256"] = sha
    return obj


def _put(root: Path, sub: str, doc: str, text_bytes: bytes, gold: dict):
    text_dir, gold_dir = root / sub / "text", root / sub / "gold"
    text_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)
    (text_dir / f"{doc}.txt").write_bytes(text_bytes)
    (gold_dir / f"{doc}.gold_privacy.json").write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")
    return text_dir, gold_dir


def _run_t1(root: Path, docs: str, extra_args=()):
    args = ["--data-root", str(root), "--sets", "t1", "--t1-docs", docs,
            "--t1-text-dir", str(root / "t1" / "text"), "--t1-gold-dir", str(root / "t1" / "gold"),
            "--out-json", str(root / "t1" / "out.json"), "--out-md", str(root / "t1" / "out.md"), *extra_args]
    return main(args)


def _out(root: Path):
    return json.loads((root / "t1" / "out.json").read_text(encoding="utf-8"))


def test_t1_clean_run_passes_with_recall_one_and_ci_when_two_clusters():
    case = _case()
    text = case["canonical_text"]
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for doc in ("HDLD005", "HDLD006"):
            _put(root, "t1", doc, text.encode("utf-8"), _gold(case))
        assert _run_t1(root, "HDLD005,HDLD006") == 0
        g = _out(root)["sets"]["T1"]["groups"]["high_sensitivity"]
        assert g["recall"] == 1.0 and g["status"] == "PASS"
        assert g["ci95"]["clusters"] == 2 and g["ci95"]["low"] is not None


def test_single_cluster_gives_no_interval():
    case = _case()
    text = case["canonical_text"]
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _put(root, "t1", "HDLD005", text.encode("utf-8"), _gold(case))
        assert _run_t1(root, "HDLD005") == 0
        assert _out(root)["sets"]["T1"]["groups"]["high_sensitivity"]["ci95"]["low"] is None


def test_missing_t1_gold_for_listed_doc_fails_closed():
    case = _case()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _put(root, "t1", "HDLD005", case["canonical_text"].encode("utf-8"), _gold(case))
        assert _run_t1(root, "HDLD005,HDLD006") == 2


def test_t1_sha_mismatch_and_non_adjudicated_status_fail_closed():
    case = _case()
    raw = case["canonical_text"].encode("utf-8")
    for kwargs in ({"sha": "0" * 64}, {"status": "DRAFT"}):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _put(root, "t1", "HDLD005", raw, _gold(case, **kwargs))
            assert _run_t1(root, "HDLD005") == 2


def test_t1_crlf_text_gives_same_offsets_as_lf():
    case = _case()
    text = case["canonical_text"]
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _put(root, "t1", "HDLD005", text.replace("\n", "\r\n").encode("utf-8"), _gold(case))
        assert _run_t1(root, "HDLD005") == 0
        assert _out(root)["sets"]["T1"]["groups"]["high_sensitivity"]["recall"] == 1.0


def test_d1_nfd_text_is_canonicalized_and_sha_is_checked_on_canonical():
    case = _case()
    canon = canonicalize([case["canonical_text"]])
    nfd = unicodedata.normalize("NFD", canon)
    assert nfd != canon
    canon_sha = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    raw_sha = hashlib.sha256(nfd.encode("utf-8")).hexdigest()
    for sha, expect in ((canon_sha, 0), (raw_sha, 2)):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            text_dir, gold_dir = None, None
            for i in range(1, 5):
                text_dir, gold_dir = _put(root, "d1", f"HDLD00{i}", nfd.encode("utf-8"),
                                          _gold(case, sha=sha) if i == 1 else {"pii_spans": [], "preserve_spans": []})
            code = main(["--data-root", str(root), "--sets", "d1", "--d1-text-dir", str(text_dir),
                         "--d1-gold-dir", str(gold_dir), "--out-json", str(root / "d1.json")])
            assert code == expect, (sha == canon_sha, code)
            if expect == 0:
                basis = json.loads((root / "d1.json").read_text(encoding="utf-8"))["sets"]["D1"]["hash_basis"]
                assert basis["HDLD001"] == "canonical"


def test_d1_without_pii_gold_is_not_estimable_never_one_hundred():
    case = _case()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for i in range(1, 5):
            text_dir, gold_dir = _put(root, "d1", f"HDLD00{i}", case["canonical_text"].encode("utf-8"),
                                      {"pii_spans": [], "preserve_spans": []})
        assert main(["--data-root", str(root), "--sets", "d1", "--d1-text-dir", str(text_dir),
                     "--d1-gold-dir", str(gold_dir), "--out-json", str(root / "d1.json")]) == 0
        g = json.loads((root / "d1.json").read_text(encoding="utf-8"))["sets"]["D1"]["groups"]["high_sensitivity"]
        assert g["recall"] is None and g["status"] == "NOT_ESTIMABLE"


def test_public_outputs_contain_no_contract_text():
    case = _case()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _put(root, "t1", "HDLD005", case["canonical_text"].encode("utf-8"), _gold(case))
        assert _run_t1(root, "HDLD005") == 0
        blob = (root / "t1" / "out.json").read_text(encoding="utf-8") + (root / "t1" / "out.md").read_text(encoding="utf-8")
        for secret in ("Sao Mai", "0312345678", "Trần Văn Bình", "18 ngõ 5"):
            assert secret not in blob


def test_missed_span_goes_only_to_restricted_file_with_offsets():
    case = _case()
    text = case["canonical_text"]
    hidden = text.rindex("Hà Nội")  # lần cuối: "làm việc tại Hà Nội", không thuộc span nào được che
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        extra = [{"pii_type": "PERSON_NAME", "start_char": hidden, "end_char": hidden + len("Hà Nội")}]
        _put(root, "t1", "HDLD005", text.encode("utf-8"), _gold(case, extra=extra))
        restricted = root / "restricted" / "missed.json"
        assert _run_t1(root, "HDLD005", extra_args=["--restricted-out", str(restricted)]) == 0
        missed = json.loads(restricted.read_text(encoding="utf-8"))
        assert {"doc_id": "HDLD005", "pii_type": "PERSON_NAME", "start_char": hidden,
                "end_char": hidden + len("Hà Nội")} in missed
        public = (root / "t1" / "out.json").read_text(encoding="utf-8")
        assert "Hà Nội" not in public and str(hidden) not in public


def test_restricted_output_inside_reports_is_refused():
    case = _case()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _put(root, "t1", "HDLD005", case["canonical_text"].encode("utf-8"), _gold(case))
        bad = Path(__file__).resolve().parents[2] / "reports" / "should_not_write.json"
        assert _run_t1(root, "HDLD005", extra_args=["--restricted-out", str(bad)]) == 2
        assert not bad.exists()
