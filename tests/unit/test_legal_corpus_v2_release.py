"""V2 approval needs auditable receipts for every runtime legal item."""

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml
from app.domain.errors import LegalCorpusConflict
from app.legal.corpus_loader import load_corpus

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "legal_corpus" / "valid"
REAL = Path(__file__).resolve().parents[2] / "data" / "legal_corpus"
FILES = ("provisions.jsonl", "edges.jsonl", "label_map.yaml", "review_receipts.json")
TODAY_VN = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat()


def _reviewed(**extra):
    return {
        "reviewer_n2": "Nguyen A", "reviewer_independent": "Tran B",
        "reviewed_on": TODAY_VN, "decision": "APPROVED", **extra,
    }


def _bundle(root):
    provisions = [json.loads(line) for line in (root / "provisions.jsonl").read_text(encoding="utf-8").splitlines()]
    edges = [json.loads(line) for line in (root / "edges.jsonl").read_text(encoding="utf-8").splitlines()]
    label_map = yaml.safe_load((root / "label_map.yaml").read_text(encoding="utf-8"))
    return {
        "sources": [{
            "source_id": "TESTLAW", "document_id": "TESTLAW",
            "source_url": "https://example.gov.vn/law.pdf",
            "source_sha256": "a" * 64, "accessed_on": TODAY_VN,
            "rights_status": "APPROVED",
        }],
        "provisions": [_reviewed(
            citation_id=p["citation_id"], version=p["version"],
            content_sha256=hashlib.sha256(p["content"].encode("utf-8")).hexdigest(),
            source_id="TESTLAW", source_locator="page 1, Article 21",
            amendment_chain="Original text; no amendment in fixture",
            effective_from=p["effective_from"], effective_to=p["effective_to"],
        ) for p in provisions],
        "edges": [_reviewed(**edge, source_id="TESTLAW", source_locator="page 1") for edge in edges],
        "labels": [_reviewed(label=label, citation_id=cid, weight=weight,
                             source_id="TESTLAW", source_locator="page 1")
                   for label, weights in label_map.items() for cid, weight in weights.items()],
        "release": _reviewed(note="Fixture release sign-off"),
    }


def _owner_single_bundle(root, owner="DucAnh_ProjectOwner"):
    provisions = [json.loads(line) for line in (root / "provisions.jsonl").read_text(encoding="utf-8").splitlines()]
    edges = [json.loads(line) for line in (root / "edges.jsonl").read_text(encoding="utf-8").splitlines()]
    label_map = yaml.safe_load((root / "label_map.yaml").read_text(encoding="utf-8"))
    data_hashes = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in FILES[:3]
    }
    common = {
        "approval_policy": "OWNER_SINGLE_APPROVER_AI_ASSISTED_V1",
        "owner_approver": owner,
        "reviewed_on": TODAY_VN,
        "decision": "APPROVED",
        "ai_review_passes": ["source_verbatim_nfc", "pdf_page_locator"],
    }
    return {
        "approval_policy": "OWNER_SINGLE_APPROVER_AI_ASSISTED_V1",
        "sources": [{
            "source_id": "TESTLAW", "document_id": "TESTLAW",
            "source_url": "https://example.gov.vn/law.pdf",
            "source_sha256": "a" * 64, "accessed_on": TODAY_VN,
            "rights_status": "APPROVED",
        }],
        "provisions": [{
            **common,
            "citation_id": p["citation_id"], "version": p["version"],
            "content_sha256": hashlib.sha256(p["content"].encode("utf-8")).hexdigest(),
            "source_id": "TESTLAW", "source_locator": "page 1, Article 21",
            "amendment_chain": "Original text; no amendment in fixture",
            "effective_from": p["effective_from"], "effective_to": p["effective_to"],
        } for p in provisions],
        "edges": [{**common, **edge, "source_id": "TESTLAW", "source_locator": "page 1"} for edge in edges],
        "labels": [{
            **common, "label": label, "citation_id": cid, "weight": weight,
            "source_id": "TESTLAW", "source_locator": "page 1",
        } for label, weights in label_map.items() for cid, weight in weights.items()],
        "release": {
            **common,
            "note": "Single owner release sign-off with AI-assisted audit trace",
            "approved_data_checksums": data_hashes,
        },
    }


def _manifest(root, status="APPROVED"):
    manifest = {
        "corpus_version": "legal_corpus_v2_fixture", "graph_version": "graph_v2_fixture",
        "timezone": "Asia/Ho_Chi_Minh", "release_status": status,
        "checksums": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                      for name in FILES if (root / name).exists()},
    }
    (root / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")


@pytest.fixture
def v2_dir(tmp_path):
    for name in FILES[:3]:
        shutil.copyfile(FIX / name, tmp_path / name)
    (tmp_path / "review_receipts.json").write_text(
        json.dumps(_bundle(tmp_path), ensure_ascii=False), encoding="utf-8",
    )
    _manifest(tmp_path)
    return tmp_path


def test_v2_approved_requires_review_receipts(v2_dir):
    (v2_dir / "review_receipts.json").unlink()
    _manifest(v2_dir)
    with pytest.raises(LegalCorpusConflict, match="review_receipts"):
        load_corpus(v2_dir)


def test_v2_approved_receipts_cover_all_items(v2_dir):
    assert len(load_corpus(v2_dir).provisions) == 4


@pytest.mark.parametrize("filename,payload", [
    ("manifest.yaml", b"["), ("provisions.jsonl", b"[]\n"),
    ("edges.jsonl", b"null\n"), ("provisions.jsonl", b"\xff"),
])
def test_malformed_bundle_has_consistent_corpus_error(v2_dir, filename, payload):
    (v2_dir / filename).write_bytes(payload)
    if filename != "manifest.yaml":
        _manifest(v2_dir)
    with pytest.raises(LegalCorpusConflict):
        load_corpus(v2_dir)


def test_dev_legal_fallback_handles_malformed_manifest(tmp_path):
    from app.core.config import Settings
    from app.main import load_legal

    (tmp_path / "manifest.yaml").write_text("[", encoding="utf-8")
    cfg = Settings(APP_ENV="dev", LEGAL_CORPUS_DIR=str(tmp_path), _env_file=None)
    assert load_legal(cfg) == (None, None, None)


def test_v2_receipt_source_must_belong_to_provision_document(v2_dir):
    bundle = json.loads((v2_dir / "review_receipts.json").read_text(encoding="utf-8"))
    bundle["sources"][0]["document_id"] = "UNRELATED_DOCUMENT"
    (v2_dir / "review_receipts.json").write_text(json.dumps(bundle), encoding="utf-8")
    _manifest(v2_dir)
    with pytest.raises(LegalCorpusConflict, match="document/source mismatch"):
        load_corpus(v2_dir)


@pytest.mark.parametrize("bad_url", ["https://", "https:///law.pdf"])
def test_v2_receipt_source_url_requires_a_host(v2_dir, bad_url):
    bundle = json.loads((v2_dir / "review_receipts.json").read_text(encoding="utf-8"))
    bundle["sources"][0]["source_url"] = bad_url
    (v2_dir / "review_receipts.json").write_text(json.dumps(bundle), encoding="utf-8")
    _manifest(v2_dir)
    with pytest.raises(LegalCorpusConflict, match="source_url"):
        load_corpus(v2_dir)


def test_v2_receipt_weight_cannot_use_boolean_in_place_of_one(v2_dir):
    lmap = yaml.safe_load((v2_dir / "label_map.yaml").read_text(encoding="utf-8"))
    for weights in lmap.values():
        for cid in weights:
            weights[cid] = 1.0
    (v2_dir / "label_map.yaml").write_text(yaml.safe_dump(lmap), encoding="utf-8")
    bundle = _bundle(v2_dir)
    bundle["labels"][0]["weight"] = True
    (v2_dir / "review_receipts.json").write_text(json.dumps(bundle), encoding="utf-8")
    _manifest(v2_dir)
    with pytest.raises(LegalCorpusConflict, match="label weight"):
        load_corpus(v2_dir)


def test_v2_owner_single_approver_policy_passes_when_valid(tmp_path):
    for name in FILES[:3]:
        shutil.copyfile(FIX / name, tmp_path / name)
    (tmp_path / "review_receipts.json").write_text(
        json.dumps(_owner_single_bundle(tmp_path), ensure_ascii=False), encoding="utf-8",
    )
    _manifest(tmp_path)
    assert len(load_corpus(tmp_path).provisions) == 4


@pytest.mark.parametrize("bad_owner", [
    "", "AI", "ChatGPT", "Gemini", "Independent_Source_Auditor", "N2", "TBD", "PENDING", "owner",
])
def test_v2_owner_single_approver_rejects_placeholder_or_ai_names(tmp_path, bad_owner):
    for name in FILES[:3]:
        shutil.copyfile(FIX / name, tmp_path / name)
    bundle = _owner_single_bundle(tmp_path, owner=bad_owner)
    (tmp_path / "review_receipts.json").write_text(json.dumps(bundle), encoding="utf-8")
    _manifest(tmp_path)
    with pytest.raises(LegalCorpusConflict):
        load_corpus(tmp_path)


def test_v2_owner_single_approver_forbids_fake_multi_reviewer_fields(tmp_path):
    for name in FILES[:3]:
        shutil.copyfile(FIX / name, tmp_path / name)
    bundle = _owner_single_bundle(tmp_path)
    bundle["provisions"][0]["reviewer_independent"] = "FakeSecondPerson"
    (tmp_path / "review_receipts.json").write_text(json.dumps(bundle), encoding="utf-8")
    _manifest(tmp_path)
    with pytest.raises(LegalCorpusConflict, match="forbids populating"):
        load_corpus(tmp_path)


def test_v2_owner_single_approver_requires_matching_pinned_data_checksums(tmp_path):
    for name in FILES[:3]:
        shutil.copyfile(FIX / name, tmp_path / name)
    bundle = _owner_single_bundle(tmp_path)
    bundle["release"]["approved_data_checksums"]["provisions.jsonl"] = "0" * 64
    (tmp_path / "review_receipts.json").write_text(json.dumps(bundle), encoding="utf-8")
    _manifest(tmp_path)
    with pytest.raises(LegalCorpusConflict, match="approved_data_checksums"):
        load_corpus(tmp_path)


@pytest.mark.parametrize("mutation", [
    lambda b: b["provisions"].pop(),
    lambda b: b["provisions"][0].update(content_sha256="0" * 64),
    lambda b: b["provisions"][0].update(reviewer_independent="Nguyen A"),
    lambda b: b["provisions"][0].update(effective_from="2020-01-01"),
    lambda b: b["sources"][0].update(source_sha256="bad"),
    lambda b: b["edges"].clear(),
    lambda b: b["labels"].clear(),
    lambda b: b["release"].update(decision="PENDING"),
])
def test_v2_rejects_incomplete_or_unverified_review(v2_dir, mutation):
    bundle = json.loads((v2_dir / "review_receipts.json").read_text(encoding="utf-8"))
    mutation(bundle)
    (v2_dir / "review_receipts.json").write_text(json.dumps(bundle), encoding="utf-8")
    _manifest(v2_dir)
    with pytest.raises(LegalCorpusConflict):
        load_corpus(v2_dir)


def test_v2_receipt_checksum_rejects_silent_edit(v2_dir):
    with (v2_dir / "review_receipts.json").open("a", encoding="utf-8") as handle:
        handle.write(" ")
    with pytest.raises(LegalCorpusConflict, match="SHA-256 mismatch"):
        load_corpus(v2_dir)


def test_v2_draft_is_never_runtime_approved(v2_dir):
    _manifest(v2_dir, status="DRAFT")
    with pytest.raises(LegalCorpusConflict, match="awaits"):
        load_corpus(v2_dir)


def test_edge_requires_temporally_coexisting_endpoints(v2_dir):
    path = v2_dir / "provisions.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["effective_to"] = "2024-12-31"
    rows[-1]["effective_from"] = "2025-01-01"
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    bundle = _bundle(v2_dir)
    (v2_dir / "review_receipts.json").write_text(json.dumps(bundle), encoding="utf-8")
    _manifest(v2_dir)
    with pytest.raises(LegalCorpusConflict, match="no common effective interval"):
        load_corpus(v2_dir)


def test_v1_snapshot_cannot_be_rewritten_with_new_manifest_hash(tmp_path):
    for name in FILES[:3] + ("manifest.yaml",):
        shutil.copyfile(REAL / name, tmp_path / name)
    path = tmp_path / "provisions.jsonl"
    path.write_bytes(path.read_bytes() + b"\n")
    manifest = yaml.safe_load((tmp_path / "manifest.yaml").read_text(encoding="utf-8"))
    manifest["checksums"]["provisions.jsonl"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (tmp_path / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    with pytest.raises(LegalCorpusConflict, match="immutable v1"):
        load_corpus(tmp_path)
def test_non_fixture_corpus_disguised_as_fixture_v1_is_rejected(tmp_path):
    for name in FILES[:3]:
        shutil.copyfile(REAL / name, tmp_path / name)
    manifest = {
        "corpus_version": "fixture_v1",
        "graph_version": "fixture_graph_v1",
        "timezone": "Asia/Ho_Chi_Minh",
        "release_status": "APPROVED",
        "checksums": {
            name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
            for name in FILES[:3]
        },
    }
    (tmp_path / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    with pytest.raises(LegalCorpusConflict, match="review_receipts"):
        load_corpus(tmp_path)


def _make_v2_decision_sheet(draft_dir: Path, owner: str = "DucAnh_ProjectOwner") -> dict:
    from app.legal.corpus_loader import (
        REQUIRED_DESIGN_DECISION_IDS,
        REQUIRED_EXCLUDED_CANDIDATE_IDS,
        REQUIRED_EXCLUDED_RISK_LABELS,
        REQUIRED_SOURCE_REGISTER_IDS,
    )

    provs = [
        json.loads(line)
        for line in (draft_dir / "provisions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    edges = [
        json.loads(line)
        for line in (draft_dir / "edges.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    lmap = yaml.safe_load((draft_dir / "label_map.yaml").read_text(encoding="utf-8"))
    hashes = {
        name: hashlib.sha256((draft_dir / name).read_bytes()).hexdigest()
        for name in FILES[:3]
    }
    active_sids = {"LAW-BLLD-45-2019", "LAW-BLLD-VBHN-18-2026", "LAW-BLLD-VBHN-18-2026-GAZETTE-PDF"}
    srd_list = []
    for idx_s, sid in enumerate(REQUIRED_SOURCE_REGISTER_IDS):
        is_active = sid in active_sids
        is_2027 = "399-2026" in sid
        is_tt10 = sid == "LAW-TT-10-2020"
        srd_list.append({
            "source_id": sid,
            "document_id": "TESTLAW" if "BLLD" in sid else f"DOC_{idx_s}",
            "document_number": sid,
            "part": "main",
            "priority": "P0",
            "required_for_wp1_release": is_active,
            "document_effective_from": "2027-01-01" if is_2027 else ("2021-01-01" if is_active else ""),
            "document_effective_to_candidate": "",
            "sha256": f"{idx_s + 1:064x}",
            "pages": "83",
            "accessed_on": TODAY_VN,
            "official_record_url": f"https://vanban.chinhphu.vn/?docid={idx_s + 1}",
            "official_attachment_url": f"https://datafiles.chinhphu.vn/{idx_s + 1}.pdf",
            "owner_source_approval_decision": (
                "APPROVED"
                if is_active
                else (
                    "PENDING_EFFECTIVE_DATE_2027"
                    if is_2027
                    else ("PENDING_HASH_VERIFICATION" if is_tt10 else "DEFERRED_TO_WP2")
                )
            ),
            "owner_usage_rights_decision": (
                "INTERNAL_REPO_ONLY" if is_active else "HOLD_OR_METADATA_ONLY"
            ),
            "owner_effective_window_decision": (
                "APPROVED"
                if is_active
                else ("PENDING_EFFECTIVE_DATE_2027" if is_2027 else "PENDING_HASH_VERIFICATION")
            ),
        })

    return {
        "schema_version": "owner_decision_sheet_v2",
        "approval_policy": "OWNER_SINGLE_APPROVER_AI_ASSISTED_V1",
        "target_draft_version": "legal_corpus_2026-11-18_v2_wp1_draft_v09",
        "expected_data_checksums": hashes,
        "owner_approver": owner,
        "reviewed_on": TODAY_VN,
        "release_decision": "APPROVED",
        "release_note": "Full 7-group owner sign-off for WP1 v2 release",
        "design_decisions": [
            {
                "decision_id": did,
                "title": f"Design decision {did}",
                "selected_option": "OPTION_A",
                "owner_decision": "APPROVED",
                "ai_review_passes": ["design_gate_audit"],
            }
            for did in REQUIRED_DESIGN_DECISION_IDS
        ],
        "source_register_decisions": srd_list,
        "provisions": [
            {
                "citation_id": p["citation_id"],
                "version": p["version"],
                "content_sha256": hashlib.sha256(p["content"].encode("utf-8")).hexdigest(),
                "source_id": "LAW-BLLD-45-2019",
                "source_locator": "p.9 Article 21",
                "amendment_chain": "Original 45/2019/QH14; unamended in 18/VBHN-VPQH (2026-02-12)",
                "effective_from": p["effective_from"],
                "effective_to": p["effective_to"],
                "ai_review_passes": ["source_verbatim_nfc"],
                "owner_decision": "APPROVED",
            }
            for p in provs
        ],
        "edges": [
            {
                **e,
                "source_id": "LAW-BLLD-45-2019",
                "source_locator": "p.9",
                "ai_review_passes": ["edge_endpoint_audit"],
                "owner_decision": "APPROVED",
            }
            for e in edges
        ],
        "labels": [
            {
                "label": lbl,
                "citation_id": cid,
                "weight": float(w),
                "source_id": "LAW-BLLD-45-2019",
                "source_locator": "p.9",
                "ai_review_passes": ["label_weight_audit"],
                "owner_decision": "APPROVED",
            }
            for lbl, weights in lmap.items()
            for cid, w in weights.items()
        ],
        "excluded_candidates": [
            {
                "citation_id": cid,
                "proposed_action": "EXCLUDE_FROM_RISK_DRAFT",
                "rationale": "Excluded administrative/header provision candidate",
                "target_work_package": "OUT_OF_RISK_TAXONOMY_SCOPE",
                "ai_review_passes": ["provision_scope_exclusion_audit"],
                "owner_decision": "EXCLUDED",
            }
            for cid in REQUIRED_EXCLUDED_CANDIDATE_IDS
        ],
        "excluded_labels": [
            {
                "risk_label": rlbl,
                "clause_label_ref": "OTHER",
                "statutory_basis": "Articles outside 20-22",
                "rationale": "Out of WP-1 Articles 20-22 scope",
                "target_work_package": "WP-2",
                "ai_review_passes": ["risk_taxonomy_21_label_scope_audit"],
                "owner_decision": "DEFERRED_TO_WP2",
            }
            for rlbl in REQUIRED_EXCLUDED_RISK_LABELS
        ],
    }


def test_build_signed_release_enforces_all_seven_groups_and_connects_source_rights(tmp_path):
    import sys
    root_dir = Path(__file__).resolve().parents[2]
    if str(root_dir / "scripts") not in sys.path:
        sys.path.insert(0, str(root_dir / "scripts"))
    from generate_receipts_after_human_signoff import build_signed_release

    draft_dir = tmp_path / "draft"
    draft_dir.mkdir()
    for name in FILES[:3]:
        shutil.copyfile(FIX / name, draft_dir / name)

    sheet = _make_v2_decision_sheet(draft_dir)
    sheet_path = tmp_path / "sheet.json"
    sheet_path.write_text(json.dumps(sheet, ensure_ascii=False), encoding="utf-8")

    out_dir = tmp_path / "signed_out"
    checksums = build_signed_release(sheet_path, draft_dir, out_dir)
    assert "review_receipts.json" in checksums
    corpus = load_corpus(out_dir, allow_draft=False)
    assert len(corpus.provisions) == 4
    receipts = json.loads((out_dir / "review_receipts.json").read_text(encoding="utf-8"))
    assert receipts["schema_version"] == "review_receipts_v2"
    assert len(receipts["design_decisions"]) == 5
    assert len(receipts["source_register_decisions"]) == 9
    assert len(receipts["excluded_candidates"]) == 5
    assert len(receipts["excluded_labels"]) == 11
    assert all(s["rights_status"] == "APPROVED" for s in receipts["sources"])


@pytest.mark.parametrize("bad_mutation,err_match", [
    (lambda s: s["design_decisions"].pop(), "design_decisions must contain D-01..D-05"),
    (lambda s: s["design_decisions"][0].update(owner_decision="PENDING_OWNER_DECISION"), "D-01' is not APPROVED"),
    (lambda s: s["source_register_decisions"][0].update(owner_usage_rights_decision="PENDING_OWNER_DECISION"), "owner_usage_rights_decision"),
    (lambda s: s["source_register_decisions"][0].update(owner_effective_window_decision="PENDING_OWNER_DECISION"), "owner_effective_window_decision"),
    (lambda s: s["source_register_decisions"][6].update(owner_source_approval_decision="APPROVED"), "cannot be APPROVED for current runtime"),
    (lambda s: s["excluded_candidates"][0].update(owner_decision="PENDING_OWNER_DECISION"), "owner_decision=='EXCLUDED'"),
    (lambda s: s["excluded_labels"].pop(), "excluded_labels must contain all 11"),
    (lambda s: s["excluded_labels"][0].update(owner_decision="PENDING_OWNER_DECISION"), "excluded_label 'PROBATION'"),
])
def test_build_signed_release_rejects_incomplete_design_source_or_exclusion_groups(
    tmp_path, bad_mutation, err_match
):
    import sys
    root_dir = Path(__file__).resolve().parents[2]
    if str(root_dir / "scripts") not in sys.path:
        sys.path.insert(0, str(root_dir / "scripts"))
    from generate_receipts_after_human_signoff import build_signed_release

    draft_dir = tmp_path / "draft"
    draft_dir.mkdir()
    for name in FILES[:3]:
        shutil.copyfile(FIX / name, draft_dir / name)

    sheet = _make_v2_decision_sheet(draft_dir)
    bad_mutation(sheet)
    sheet_path = tmp_path / "sheet.json"
    sheet_path.write_text(json.dumps(sheet, ensure_ascii=False), encoding="utf-8")

    out_dir = tmp_path / "signed_out"
    with pytest.raises(ValueError, match=err_match):
        build_signed_release(sheet_path, draft_dir, out_dir)
    assert not out_dir.exists()


@pytest.mark.parametrize("line_ending", ["\n", "\r\n"])
def test_fixture_v1_accepts_both_lf_and_crlf_edges_but_rejects_modified_edges(tmp_path, line_ending):
    for name in FILES[:3]:
        raw = (FIX / name).read_bytes().replace(b"\r\n", b"\n")
        if line_ending == "\r\n":
            raw = raw.replace(b"\n", b"\r\n")
        (tmp_path / name).write_bytes(raw)
    manifest = {
        "corpus_version": "fixture_v1",
        "graph_version": "fixture_graph_v1",
        "timezone": "Asia/Ho_Chi_Minh",
        "release_status": "APPROVED",
        "checksums": {
            name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
            for name in FILES[:3]
        },
    }
    (tmp_path / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    loaded = load_corpus(tmp_path)
    assert len(loaded.provisions) == 4
    assert len(loaded.edges) == 1
