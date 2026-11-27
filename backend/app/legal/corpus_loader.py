"""Read the closed legal corpus from data files without network access (C-12a & v2 gates)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import yaml

from app.domain.errors import LegalCorpusConflict

_BASE_FILES = ("provisions.jsonl", "edges.jsonl", "label_map.yaml")
_RECEIPT_FILE = "review_receipts.json"
_V1_VERSION = "legal_corpus_2026-11-14_v02"
_V1_CHECKSUMS = {
    "provisions.jsonl": "f8a3b6b5bd34d0352da1dad05e156b246cd78e470386c5634732073151dfb44b",
    "edges.jsonl": "bce0f9dcf457f130493816ff3e3281268abaf2c1b760696cb49452fe91f9e098",
    "label_map.yaml": "e9b652af68e25ea55f2d7bf32599256aea9a2d1cf4afda416ef880f2a4dc89ad",
}
_FIXTURE_V1_VERSION = "fixture_v1"
_FIXTURE_V1_GRAPH = "fixture_graph_v1"
_FIXTURE_V1_EDGES_SHA256_SET = frozenset({
    "2b59c37e604c0fe30ce596c7d7a24074da6c9f39d0ec4a1b910fba17023587c1",  # LF checkout
    "252e224a7e235d1ec2c9e4835040336293e75ea76cc95154d293512878b18ca4",  # CRLF checkout
})
_FIXTURE_V1_EDGES_EXPECTED = (
    ("TESTLAW:art22", "TESTLAW:art21", "REFERS_TO", "MANUAL"),
)
_FIXTURE_V1_DOC_NAME = "Luật giả lập (chỉ fixture kiểm thử)"
_FIXTURE_V1_CONTENTS = {
    "TESTLAW:art21": "Điều 21. Văn bản giả lập cho kiểm thử.",
    "TESTLAW:art21:cl1": "1. Quy định giả lập về nội dung hợp đồng.",
    "TESTLAW:art21:cl1:ptc": "c) Công việc giả lập và địa điểm làm việc.",
    "TESTLAW:art22": "Điều 22. Phụ lục giả lập.",
}
_PROVISION_KEYS = {
    "citation_id", "document_id", "document_name", "version", "article", "clause",
    "point", "parent_path", "content", "effective_from", "effective_to",
}
_EDGE_KEYS = {"from_citation_id", "to_citation_id", "edge_type", "origin"}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_REVIEWER_TOKENS = {
    "", "ai", "assistant", "chatgpt", "gemini", "codex", "claude", "llm", "bot",
    "independent_source_auditor", "independent_reviewer", "reviewer_n2", "reviewer_n3",
    "n1", "n2", "n3", "n4", "n5", "owner", "tbd", "pending", "unknown", "none", "null",
}

REQUIRED_DESIGN_DECISION_IDS = ("D-01", "D-02", "D-03", "D-04", "D-05")
REQUIRED_SOURCE_REGISTER_IDS = (
    "LAW-BLLD-45-2019",
    "LAW-BLLD-VBHN-18-2026",
    "LAW-BLLD-VBHN-18-2026-GAZETTE-PDF",
    "LAW-BLLD-VBHN-18-2026-GAZETTE-DOCX",
    "LAW-ND-145-2020",
    "LAW-ND-293-2025",
    "LAW-ND-399-2026-MAIN",
    "LAW-ND-399-2026-ANNEX",
    "LAW-TT-10-2020",
)
REQUIRED_EXCLUDED_CANDIDATE_IDS = (
    "BLLD2019:art21:cl1:pta",
    "BLLD2019:art21:cl1:ptb",
    "BLLD2019:art21:cl3",
    "BLLD2019:art21:cl4",
    "BLLD2019:art21:cl5",
)
REQUIRED_EXCLUDED_RISK_LABELS = (
    "PROBATION",
    "PAYMENT_TIMING_METHOD",
    "REST_AND_LEAVE",
    "PENALTY_DEDUCTION_DAMAGES",
    "DISCIPLINE_OBLIGATION",
    "DEPOSIT_DOCUMENT_HELD",
    "DISCRIMINATION_PROTECTED_GROUPS",
    "TERMINATION_GROUNDS_NOTICE",
    "TERMINATION_SETTLEMENT",
    "WAIVER_RIGHTS_DISPUTE",
    "PERSONAL_DATA_PRIVACY",
)
ALLOWED_APPROVED_USAGE_RIGHTS = {
    "APPROVED",
    "INTERNAL_REPO_ONLY",
    "APPROVED_INTERNAL_REPO_ONLY",
    "PUBLIC_REDISTRIBUTION_CLEARED",
}
ALLOWED_NON_RUNTIME_SOURCE_DECISIONS = {
    "APPROVED",
    "DEFERRED_TO_WP2",
    "DEFERRED_TO_WP3",
    "PENDING",
    "PENDING_EFFECTIVE_DATE_2027",
    "HOLD_PENDING_EFFECTIVE_DATE_2027",
    "PENDING_HASH_VERIFICATION",
    "HOLD_PENDING_HASH_VERIFICATION",
    "PENDING_EVIDENCE",
    "HOLD_OR_METADATA_ONLY",
}
ALLOWED_EXCLUDED_LABEL_DECISIONS = {
    "EXCLUDED",
    "DEFERRED_TO_WP2",
    "DEFERRED_TO_WP3",
    "COMPLETE_IN_V1_NO_ART20_22_EXPANSION",
}


@dataclass(frozen=True)
class LegalProvision:
    citation_id: str
    document_id: str
    document_name: str
    version: str
    article: str
    clause: str | None
    point: str | None
    parent_path: tuple[str, ...]
    content: str
    effective_from: date
    effective_to: date | None


@dataclass(frozen=True)
class LegalEdge:
    from_citation_id: str
    to_citation_id: str
    edge_type: str
    origin: str


@dataclass(frozen=True)
class LegalCorpus:
    corpus_version: str
    graph_version: str
    timezone: str
    release_status: str
    provisions: tuple[LegalProvision, ...]
    edges: tuple[LegalEdge, ...]
    label_map: dict[str, dict[str, float]]


def _fail(message: str) -> None:
    raise LegalCorpusConflict(message)


def _no_duplicate_json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            _fail(f"duplicate JSON key: {key}")
        out[key] = value
    return out


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(
    loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            _fail(f"duplicate key in YAML: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def _parse_date(value: Any, field: str) -> date:
    if not isinstance(value, str) or len(value) != 10:
        _fail(f"invalid {field}: {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise LegalCorpusConflict(f"invalid {field}: {value!r}") from exc


def _valid_human_id(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    cleaned = value.strip()
    if len(cleaned) < 3 or cleaned.casefold() in _FORBIDDEN_REVIEWER_TOKENS:
        return False
    bad_parts = {"ai", "bot", "llm", "auditor", "placeholder"}
    return not any(tok in bad_parts for tok in cleaned.casefold().split("_"))


def _is_bounded_testlaw_fixture(
    manifest: dict[str, Any],
    corpus: LegalCorpus,
    checksums: dict[str, str],
) -> bool:
    """True only for the synthetic 4-node TESTLAW unit-test fixture (`fixture_v1`)."""
    if (
        manifest.get("corpus_version") != _FIXTURE_V1_VERSION
        or manifest.get("graph_version") != _FIXTURE_V1_GRAPH
        or _RECEIPT_FILE in checksums
        or checksums.get("edges.jsonl") not in _FIXTURE_V1_EDGES_SHA256_SET
    ):
        return False
    actual_edges = tuple(
        (e.from_citation_id, e.to_citation_id, e.edge_type, e.origin) for e in corpus.edges
    )
    if actual_edges != _FIXTURE_V1_EDGES_EXPECTED:
        return False
    if not (4 <= len(corpus.provisions) <= 5):
        return False
    if not all(
        p.document_id == "TESTLAW"
        and p.document_name == _FIXTURE_V1_DOC_NAME
        and _FIXTURE_V1_CONTENTS.get(p.citation_id) == p.content
        for p in corpus.provisions
    ):
        return False
    return all(
        cid in _FIXTURE_V1_CONTENTS
        for weights in corpus.label_map.values()
        for cid in weights
    )


def _check_signoff_fields(
    record: dict[str, Any],
    policy: str,
    today_vn: date,
    owners_seen: set[str],
    *,
    allowed_decisions: set[str] | None = None,
) -> None:
    valid_decisions = allowed_decisions or {"APPROVED"}
    if record.get("decision") not in valid_decisions:
        _fail(f"review_receipts: decision must be in {sorted(valid_decisions)}")
    reviewed_on = _parse_date(record.get("reviewed_on"), "reviewed_on")
    if reviewed_on > today_vn:
        _fail("review_receipts: reviewed_on cannot be in the future")
    if policy == "OWNER_SINGLE_APPROVER_AI_ASSISTED_V1":
        if record.get("approval_policy") != "OWNER_SINGLE_APPROVER_AI_ASSISTED_V1":
            _fail("review_receipts: item approval_policy mismatch")
        owner = record.get("owner_approver")
        if not _valid_human_id(owner):
            _fail(f"review_receipts: invalid or placeholder owner_approver {owner!r}")
        owners_seen.add(owner.strip())
        for forbidden_key in ("reviewer_n2", "reviewer_n3", "reviewer_independent"):
            if record.get(forbidden_key) not in (None, ""):
                _fail(f"review_receipts: single-approver policy forbids populating {forbidden_key}")
        ai_passes = record.get("ai_review_passes")
        if (
            not isinstance(ai_passes, list)
            or not ai_passes
            or not all(isinstance(x, str) and x.strip() for x in ai_passes)
        ):
            _fail("review_receipts: single-approver policy requires non-empty ai_review_passes")
    elif policy == "TWO_HUMAN_REVIEWERS_V1":
        r_n2 = record.get("reviewer_n2")
        r_ind = record.get("reviewer_independent")
        if not (_valid_human_id(r_n2) and _valid_human_id(r_ind)) or r_n2.strip() == r_ind.strip():
            _fail("review_receipts: require two distinct valid human reviewers")
    else:
        _fail(f"review_receipts: unsupported approval_policy {policy!r}")


def _validate_v2_governance_extensions(
    bundle: dict[str, Any],
    policy: str,
    today_vn: date,
    owners_seen: set[str],
    used_source_ids: set[str],
    provisions: tuple[LegalProvision, ...],
    label_map: dict[str, dict[str, float]],
) -> None:
    is_v2_schema = bundle.get("schema_version") == "review_receipts_v2"

    if is_v2_schema or "design_decisions" in bundle:
        dd_list = bundle.get("design_decisions")
        if not isinstance(dd_list, list) or len(dd_list) != len(REQUIRED_DESIGN_DECISION_IDS):
            _fail("review_receipts: design_decisions must contain D-01..D-05")
        seen_dd: set[str] = set()
        for dd in dd_list:
            if not isinstance(dd, dict):
                _fail("review_receipts: invalid design_decision entry")
            _check_signoff_fields(dd, policy, today_vn, owners_seen)
            did = dd.get("decision_id", "")
            if did not in REQUIRED_DESIGN_DECISION_IDS or did in seen_dd:
                _fail(f"review_receipts: invalid or duplicate design_decision {did!r}")
            if not (isinstance(dd.get("selected_option"), str) and dd["selected_option"].strip()):
                _fail(f"review_receipts: design_decision {did!r} missing selected_option")
            seen_dd.add(did)

    if is_v2_schema or "source_register_decisions" in bundle:
        srd_list = bundle.get("source_register_decisions")
        if not isinstance(srd_list, list) or len(srd_list) != len(REQUIRED_SOURCE_REGISTER_IDS):
            _fail("review_receipts: source_register_decisions must cover all 9 sources")
        srd_by_id: dict[str, dict[str, Any]] = {}
        for srd in srd_list:
            if not isinstance(srd, dict):
                _fail("review_receipts: invalid source_register_decisions entry")
            sid = srd.get("source_id", "")
            if sid not in REQUIRED_SOURCE_REGISTER_IDS or sid in srd_by_id:
                _fail(f"review_receipts: invalid or duplicate source_register source_id {sid!r}")
            _check_signoff_fields(
                srd,
                policy,
                today_vn,
                owners_seen,
                allowed_decisions=ALLOWED_NON_RUNTIME_SOURCE_DECISIONS,
            )
            eff_from_raw = (srd.get("document_effective_from") or "").strip()
            if eff_from_raw:
                eff_from_dt = _parse_date(eff_from_raw, "document_effective_from")
                if eff_from_dt > today_vn and srd.get("decision") == "APPROVED":
                    _fail(f"review_receipts: future-effective source {sid!r} cannot be APPROVED for current runtime")
            srd_by_id[sid] = srd

        for active_sid in used_source_ids:
            srd = srd_by_id.get(active_sid)
            if srd is None:
                _fail(f"review_receipts: active source {active_sid!r} missing from source_register_decisions")
            if srd.get("decision") != "APPROVED":
                _fail(f"review_receipts: active source {active_sid!r} decision must be APPROVED")
            if srd.get("usage_rights_decision") not in ALLOWED_APPROVED_USAGE_RIGHTS:
                _fail(f"review_receipts: active source {active_sid!r} lacks approved usage_rights_decision")
            if srd.get("effective_window_decision") != "APPROVED":
                _fail(f"review_receipts: active source {active_sid!r} lacks approved effective_window_decision")

    prov_ids = {p.citation_id for p in provisions}
    mapped_ids = {cid for weights in label_map.values() for cid in weights}

    if is_v2_schema or "excluded_candidates" in bundle:
        exc_cands = bundle.get("excluded_candidates")
        if not isinstance(exc_cands, list) or len(exc_cands) != len(REQUIRED_EXCLUDED_CANDIDATE_IDS):
            _fail("review_receipts: excluded_candidates must contain the 5 excluded provision candidates")
        seen_exc_cands: set[str] = set()
        for ec in exc_cands:
            if not isinstance(ec, dict):
                _fail("review_receipts: invalid excluded_candidate entry")
            _check_signoff_fields(ec, policy, today_vn, owners_seen, allowed_decisions={"EXCLUDED"})
            cid = ec.get("citation_id", "")
            if cid not in REQUIRED_EXCLUDED_CANDIDATE_IDS or cid in seen_exc_cands:
                _fail(f"review_receipts: invalid or duplicate excluded_candidate {cid!r}")
            if cid in prov_ids or cid in mapped_ids:
                _fail(f"review_receipts: excluded_candidate {cid!r} must not appear in corpus provisions or label_map")
            if not (isinstance(ec.get("rationale"), str) and ec["rationale"].strip()):
                _fail(f"review_receipts: excluded_candidate {cid!r} missing rationale")
            seen_exc_cands.add(cid)

    if is_v2_schema or "excluded_labels" in bundle:
        exc_lbls = bundle.get("excluded_labels")
        if not isinstance(exc_lbls, list) or len(exc_lbls) != len(REQUIRED_EXCLUDED_RISK_LABELS):
            _fail("review_receipts: excluded_labels must contain all 11 out-of-scope risk labels")
        seen_exc_lbls: set[str] = set()
        for el in exc_lbls:
            if not isinstance(el, dict):
                _fail("review_receipts: invalid excluded_label entry")
            _check_signoff_fields(
                el,
                policy,
                today_vn,
                owners_seen,
                allowed_decisions=ALLOWED_EXCLUDED_LABEL_DECISIONS,
            )
            rlbl = el.get("risk_label", "")
            if rlbl not in REQUIRED_EXCLUDED_RISK_LABELS or rlbl in seen_exc_lbls:
                _fail(f"review_receipts: invalid or duplicate excluded_label {rlbl!r}")
            if not (isinstance(el.get("rationale"), str) and el["rationale"].strip()):
                _fail(f"review_receipts: excluded_label {rlbl!r} missing rationale")
            if not (isinstance(el.get("target_work_package"), str) and el["target_work_package"].strip()):
                _fail(f"review_receipts: excluded_label {rlbl!r} missing target_work_package")
            seen_exc_lbls.add(rlbl)


def _validate_v2_receipts(
    folder: Path,
    provisions: tuple[LegalProvision, ...],
    edges: tuple[LegalEdge, ...],
    label_map: dict[str, dict[str, float]],
    checksums: dict[str, str],
) -> None:
    receipt_path = folder / _RECEIPT_FILE
    if _RECEIPT_FILE not in checksums or not receipt_path.exists():
        _fail("v2 APPROVED corpus requires review_receipts.json and its checksum")
    raw = receipt_path.read_text(encoding="utf-8")
    bundle = json.loads(raw, object_pairs_hook=_no_duplicate_json_pairs)
    if not isinstance(bundle, dict):
        _fail("review_receipts: root must be an object")

    policy = bundle.get("approval_policy", "TWO_HUMAN_REVIEWERS_V1")
    today_vn = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    owners_seen: set[str] = set()
    if policy == "OWNER_SINGLE_APPROVER_AI_ASSISTED_V1" and "owner_approver" in bundle:
        top_owner = bundle.get("owner_approver")
        if not _valid_human_id(top_owner):
            _fail(f"review_receipts: invalid top-level owner_approver {top_owner!r}")
        owners_seen.add(top_owner.strip())

    sources = bundle.get("sources")
    if not isinstance(sources, list) or not sources:
        _fail("review_receipts: sources must be a non-empty list")
    source_ids: set[str] = set()
    source_documents: dict[str, str] = {}
    for src in sources:
        if not isinstance(src, dict):
            _fail("review_receipts: invalid source entry")
        sid = src.get("source_id")
        doc_id = src.get("document_id")
        s_url = src.get("source_url")
        s_sha = src.get("source_sha256")
        if not (isinstance(sid, str) and sid.strip() and sid not in source_ids):
            _fail("review_receipts: missing or duplicate source_id")
        if not (isinstance(doc_id, str) and doc_id.strip()):
            _fail("review_receipts: missing document_id in source")
        try:
            parsed_url = urlparse(s_url) if isinstance(s_url, str) else None
            valid_url = parsed_url is not None and parsed_url.scheme == "https" and bool(parsed_url.netloc and parsed_url.hostname)
        except ValueError:
            valid_url = False
        if not valid_url:
            _fail("review_receipts: source_url must use HTTPS and have a host")
        if not (isinstance(s_sha, str) and _HEX64.fullmatch(s_sha)):
            _fail("review_receipts: invalid source_sha256")
        if _parse_date(src.get("accessed_on"), "accessed_on") > today_vn:
            _fail("review_receipts: accessed_on in the future")
        if src.get("rights_status") != "APPROVED":
            _fail("review_receipts: source rights_status must be APPROVED")
        source_ids.add(sid)
        source_documents[sid] = doc_id

    used_source_ids: set[str] = set(source_ids)

    prov_receipts = bundle.get("provisions")
    if not isinstance(prov_receipts, list) or len(prov_receipts) != len(provisions):
        _fail("review_receipts: provisions count mismatch")
    by_prov_key: dict[tuple[str, str], dict[str, Any]] = {}
    for pr in prov_receipts:
        if not isinstance(pr, dict):
            _fail("review_receipts: invalid provision receipt")
        _check_signoff_fields(pr, policy, today_vn, owners_seen)
        key = (pr.get("citation_id", ""), pr.get("version", ""))
        if key in by_prov_key:
            _fail(f"review_receipts: duplicate provision receipt {key}")
        if pr.get("source_id") not in source_ids:
            _fail("review_receipts: unknown source_id in provision receipt")
        used_source_ids.add(pr["source_id"])
        if not (isinstance(pr.get("source_locator"), str) and pr["source_locator"].strip()):
            _fail("review_receipts: missing source_locator")
        if not (isinstance(pr.get("amendment_chain"), str) and pr["amendment_chain"].strip()):
            _fail("review_receipts: missing amendment_chain")
        by_prov_key[key] = pr

    for p in provisions:
        pr = by_prov_key.get((p.citation_id, p.version))
        if pr is None:
            _fail(f"review_receipts: missing receipt for {p.citation_id} ({p.version})")
        if source_documents[pr["source_id"]] != p.document_id:
            _fail(f"review_receipts: provision document/source mismatch for {p.citation_id}")
        expected_sha = hashlib.sha256(p.content.encode("utf-8")).hexdigest()
        if pr.get("content_sha256") != expected_sha:
            _fail(f"review_receipts: content_sha256 mismatch for {p.citation_id}")
        if _parse_date(pr.get("effective_from"), "effective_from") != p.effective_from:
            _fail(f"review_receipts: effective_from mismatch for {p.citation_id}")
        rec_to = pr.get("effective_to")
        expected_to = p.effective_to.isoformat() if p.effective_to else None
        if rec_to != expected_to:
            _fail(f"review_receipts: effective_to mismatch for {p.citation_id}")

    edge_receipts = bundle.get("edges")
    if not isinstance(edge_receipts, list) or len(edge_receipts) != len(edges):
        _fail("review_receipts: edges count mismatch")
    seen_edges: set[tuple[str, str, str, str]] = set()
    for er in edge_receipts:
        if not isinstance(er, dict):
            _fail("review_receipts: invalid edge receipt")
        _check_signoff_fields(er, policy, today_vn, owners_seen)
        if er.get("source_id") not in source_ids or not (
            isinstance(er.get("source_locator"), str) and er["source_locator"].strip()
        ):
            _fail("review_receipts: edge missing source_id/source_locator")
        used_source_ids.add(er["source_id"])
        ekey = (
            er.get("from_citation_id", ""),
            er.get("to_citation_id", ""),
            er.get("edge_type", ""),
            er.get("origin", ""),
        )
        seen_edges.add(ekey)
    for e in edges:
        if (e.from_citation_id, e.to_citation_id, e.edge_type, e.origin) not in seen_edges:
            _fail(f"review_receipts: missing edge receipt for {e.from_citation_id} -> {e.to_citation_id}")

    expected_labels = [
        (lbl, cid, float(w))
        for lbl, weights in label_map.items()
        for cid, w in weights.items()
    ]
    label_receipts = bundle.get("labels")
    if not isinstance(label_receipts, list) or len(label_receipts) != len(expected_labels):
        _fail("review_receipts: labels count mismatch")
    seen_labels: dict[tuple[str, str], float] = {}
    for lr in label_receipts:
        if not isinstance(lr, dict):
            _fail("review_receipts: invalid label receipt")
        _check_signoff_fields(lr, policy, today_vn, owners_seen)
        if lr.get("source_id") not in source_ids or not (
            isinstance(lr.get("source_locator"), str) and lr["source_locator"].strip()
        ):
            _fail("review_receipts: label missing source_id/source_locator")
        used_source_ids.add(lr["source_id"])
        lkey = (lr.get("label", ""), lr.get("citation_id", ""))
        if lkey in seen_labels:
            _fail(f"review_receipts: duplicate label receipt {lkey}")
        weight = lr.get("weight")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            _fail(f"review_receipts: label weight must be numeric for {lkey}")
        seen_labels[lkey] = float(weight)
    for lbl, cid, w in expected_labels:
        if seen_labels.get((lbl, cid)) != w:
            _fail(f"review_receipts: label weight mismatch for {lbl}/{cid}")

    _validate_v2_governance_extensions(
        bundle, policy, today_vn, owners_seen, used_source_ids, provisions, label_map
    )

    rel = bundle.get("release")
    if not isinstance(rel, dict) or not (isinstance(rel.get("note"), str) and rel["note"].strip()):
        _fail("review_receipts: missing release note")
    _check_signoff_fields(rel, policy, today_vn, owners_seen)
    if policy == "OWNER_SINGLE_APPROVER_AI_ASSISTED_V1":
        if len(owners_seen) != 1:
            _fail("review_receipts: single-approver policy requires the exact same owner_approver across all items and release")
        pinned = rel.get("approved_data_checksums")
        if not isinstance(pinned, dict) or any(pinned.get(k) != checksums.get(k) for k in _BASE_FILES):
            _fail("review_receipts: release approved_data_checksums must match manifest data file hashes")


def load_corpus(folder: Path, *, allow_draft: bool = False) -> LegalCorpus:
    """Expose one typed corpus error for decoding, filesystem and metadata failures."""
    try:
        return _load_corpus(folder, allow_draft=allow_draft)
    except (OSError, KeyError, TypeError, ValueError, AttributeError, yaml.YAMLError) as exc:
        raise LegalCorpusConflict(f"corpus read/metadata error: {type(exc).__name__}") from exc


def _load_corpus(folder: Path, *, allow_draft: bool = False) -> LegalCorpus:
    """Load and verify checksums, records, and release gates."""
    manifest_path = folder / "manifest.yaml"
    if not manifest_path.exists():
        _fail("manifest.yaml not found")
    manifest = yaml.load(manifest_path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    if not isinstance(manifest, dict):
        _fail("manifest.yaml must be a mapping")

    status = manifest.get("release_status")
    if status not in ("DRAFT", "APPROVED"):
        _fail("manifest.yaml: invalid release_status")
    if status != "APPROVED" and not allow_draft:
        _fail("corpus awaits Data/Legal reviewer sign-off")

    checksums = manifest.get("checksums")
    if not isinstance(checksums, dict):
        _fail("manifest.yaml: missing checksums")

    version_str = manifest.get("corpus_version", "")
    is_immutable_v1 = version_str == _V1_VERSION
    if is_immutable_v1 and set(checksums.keys()) != set(_V1_CHECKSUMS.keys()):
        _fail("cannot rewrite immutable v1 snapshot (manifest keys)")

    required_files = list(_BASE_FILES)
    if _RECEIPT_FILE in checksums:
        required_files.append(_RECEIPT_FILE)

    for name in required_files:
        file_path = folder / name
        if not file_path.exists() or name not in checksums:
            _fail(f"missing {name} or its checksum in manifest.yaml")
        actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual != checksums[name]:
            _fail(f"SHA-256 mismatch for {name}")
        if is_immutable_v1 and actual != _V1_CHECKSUMS[name]:
            _fail(f"cannot rewrite immutable v1 snapshot ({name})")

    provisions_list: list[LegalProvision] = []
    for line in (folder / "provisions.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw_p = json.loads(line, object_pairs_hook=_no_duplicate_json_pairs)
        if set(raw_p.keys()) != _PROVISION_KEYS:
            _fail(f"invalid provision keys in {raw_p.get('citation_id')!r}")
        parent_path = raw_p["parent_path"]
        if not isinstance(parent_path, list) or not all(isinstance(x, str) for x in parent_path):
            _fail("parent_path must be an array of strings")
        eff_from = _parse_date(raw_p["effective_from"], "effective_from")
        eff_to = (
            _parse_date(raw_p["effective_to"], "effective_to")
            if raw_p["effective_to"] is not None
            else None
        )
        provisions_list.append(LegalProvision(
            citation_id=raw_p["citation_id"],
            document_id=raw_p["document_id"],
            document_name=raw_p["document_name"],
            version=raw_p["version"],
            article=raw_p["article"],
            clause=raw_p["clause"],
            point=raw_p["point"],
            parent_path=tuple(parent_path),
            content=raw_p["content"],
            effective_from=eff_from,
            effective_to=eff_to,
        ))

    edges_list: list[LegalEdge] = []
    for line in (folder / "edges.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw_e = json.loads(line, object_pairs_hook=_no_duplicate_json_pairs)
        if set(raw_e.keys()) != _EDGE_KEYS:
            _fail("invalid edge keys")
        edges_list.append(LegalEdge(
            from_citation_id=raw_e["from_citation_id"],
            to_citation_id=raw_e["to_citation_id"],
            edge_type=raw_e["edge_type"],
            origin=raw_e["origin"],
        ))

    label_map = yaml.load(
        (folder / "label_map.yaml").read_text(encoding="utf-8"), Loader=_UniqueKeyLoader
    )
    corpus = LegalCorpus(
        corpus_version=version_str,
        graph_version=manifest.get("graph_version", ""),
        timezone=manifest.get("timezone", ""),
        release_status=status,
        provisions=tuple(provisions_list),
        edges=tuple(edges_list),
        label_map=label_map,
    )
    from app.legal.corpus_validator import validate_corpus
    validate_corpus(corpus)

    if status == "APPROVED" and not is_immutable_v1:
        if not _is_bounded_testlaw_fixture(manifest, corpus, checksums):
            _validate_v2_receipts(
                folder, corpus.provisions, corpus.edges, corpus.label_map, checksums
            )

    return corpus
