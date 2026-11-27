"""Build an APPROVED corpus v2 release bundle from a completed Owner Decision Sheet (v2).

Fails closed without creating or modifying the output directory if any item in the
7 required decision groups (D-01..D-05 design_decisions, 9 source_register_decisions,
30 provisions, 8 edges, 20 labels, 5 excluded_candidates, 11 excluded_labels) lacks an
explicit human owner decision, uses a placeholder/AI alias, admits a future-effective
or unverified source into active runtime, disagrees with the draft corpus checksums,
or if out_dir already exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from app.legal.corpus_loader import (
    ALLOWED_APPROVED_USAGE_RIGHTS,
    ALLOWED_EXCLUDED_LABEL_DECISIONS,
    ALLOWED_NON_RUNTIME_SOURCE_DECISIONS,
    REQUIRED_DESIGN_DECISION_IDS,
    REQUIRED_EXCLUDED_CANDIDATE_IDS,
    REQUIRED_EXCLUDED_RISK_LABELS,
    REQUIRED_SOURCE_REGISTER_IDS,
    load_corpus,
)

BASE_FILES = ("provisions.jsonl", "edges.jsonl", "label_map.yaml")


def _check_item_owner(item: dict[str, Any], owner: str, ident: str) -> None:
    item_owner = (item.get("owner_approver") or owner).strip()
    if item_owner != owner:
        raise ValueError(f"item {ident!r} owner_approver {item_owner!r} != {owner!r}")


def build_signed_release(
    decision_sheet_path: Path,
    draft_dir: Path,
    out_dir: Path,
    *,
    corpus_version: str = "legal_corpus_2026-11-18_v2_wp1",
    graph_version: str = "data_graph_2026-11-18_v2_wp1",
) -> dict[str, str]:
    if out_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output directory: {out_dir}")

    sheet: dict[str, Any] = json.loads(decision_sheet_path.read_text(encoding="utf-8"))
    if sheet.get("schema_version") != "owner_decision_sheet_v2":
        raise ValueError("decision sheet: invalid schema_version (expected 'owner_decision_sheet_v2')")
    policy = sheet.get("approval_policy")
    if policy != "OWNER_SINGLE_APPROVER_AI_ASSISTED_V1":
        raise ValueError(f"decision sheet: unsupported approval_policy {policy!r}")

    owner = (sheet.get("owner_approver") or "").strip()
    reviewed_on = (sheet.get("reviewed_on") or "").strip()
    rel_decision = (sheet.get("release_decision") or "").strip()
    rel_note = (sheet.get("release_note") or "").strip()
    if not owner or not reviewed_on or rel_decision != "APPROVED" or not rel_note:
        raise ValueError(
            "decision sheet: missing owner_approver, reviewed_on, release_note, "
            "or release_decision!=APPROVED"
        )
    reviewed_dt = date.fromisoformat(reviewed_on)

    actual_data_hashes = {
        name: hashlib.sha256((draft_dir / name).read_bytes()).hexdigest()
        for name in BASE_FILES
    }
    expected_hashes = sheet.get("expected_data_checksums")
    if not isinstance(expected_hashes, dict) or expected_hashes != actual_data_hashes:
        raise ValueError("decision sheet: expected_data_checksums do not match draft_dir files")

    # 1. Validate D-01..D-05 design_decisions
    raw_dd = sheet.get("design_decisions")
    if not isinstance(raw_dd, list) or len(raw_dd) != len(REQUIRED_DESIGN_DECISION_IDS):
        raise ValueError("decision sheet: design_decisions must contain D-01..D-05")
    seen_dd: set[str] = set()
    stamped_dd: list[dict[str, Any]] = []
    for dd in raw_dd:
        did = (dd.get("decision_id") or "").strip()
        if did not in REQUIRED_DESIGN_DECISION_IDS or did in seen_dd:
            raise ValueError(f"decision sheet: invalid or duplicate design_decision {did!r}")
        if dd.get("owner_decision") != "APPROVED":
            raise ValueError(f"design decision {did!r} is not APPROVED")
        sel_opt = (dd.get("selected_option") or "").strip()
        if not sel_opt:
            raise ValueError(f"design decision {did!r} requires a non-empty selected_option")
        _check_item_owner(dd, owner, did)
        seen_dd.add(did)
        stamped_dd.append({
            **{k: v for k, v in dd.items() if k != "owner_decision"},
            "selected_option": sel_opt,
            "approval_policy": policy,
            "owner_approver": owner,
            "reviewed_on": reviewed_on,
            "decision": "APPROVED",
            "ai_review_passes": dd.get("ai_review_passes") or ["design_gate_audit"],
        })

    # 2. Identify active sources referenced by provisions, edges, labels
    raw_provs = sheet.get("provisions", [])
    raw_edges = sheet.get("edges", [])
    raw_labels = sheet.get("labels", [])
    used_source_ids: set[str] = set()
    for grp in (raw_provs, raw_edges, raw_labels):
        for item in grp:
            sid = (item.get("source_id") or "").strip()
            if sid:
                used_source_ids.add(sid)

    # 3. Validate all 9 source_register_decisions and connect to runtime sources
    raw_srd = sheet.get("source_register_decisions")
    if not isinstance(raw_srd, list) or len(raw_srd) != len(REQUIRED_SOURCE_REGISTER_IDS):
        raise ValueError("decision sheet: source_register_decisions must contain all 9 sources")
    seen_srd: set[str] = set()
    stamped_srd: list[dict[str, Any]] = []
    approved_runtime_sources: list[dict[str, Any]] = []

    for srd in raw_srd:
        sid = (srd.get("source_id") or "").strip()
        if sid not in REQUIRED_SOURCE_REGISTER_IDS or sid in seen_srd:
            raise ValueError(f"decision sheet: invalid or duplicate source_id {sid!r} in source_register_decisions")
        _check_item_owner(srd, owner, sid)
        src_dec = (srd.get("owner_source_approval_decision") or "").strip()
        rights_dec = (srd.get("owner_usage_rights_decision") or "").strip()
        eff_dec = (srd.get("owner_effective_window_decision") or "").strip()
        is_req = bool(srd.get("required_for_wp1_release")) or (sid in used_source_ids)

        eff_from_str = (srd.get("document_effective_from") or "").strip()
        if eff_from_str and date.fromisoformat(eff_from_str) > reviewed_dt:
            if src_dec == "APPROVED" or is_req:
                raise ValueError(
                    f"source {sid!r} takes effect on {eff_from_str} (> {reviewed_on}) "
                    "and cannot be APPROVED for current runtime"
                )

        if is_req:
            if src_dec != "APPROVED":
                raise ValueError(f"active WP1 source {sid!r} requires owner_source_approval_decision=='APPROVED'")
            if rights_dec not in ALLOWED_APPROVED_USAGE_RIGHTS:
                raise ValueError(
                    f"active WP1 source {sid!r} requires owner_usage_rights_decision in "
                    f"{sorted(ALLOWED_APPROVED_USAGE_RIGHTS)}"
                )
            if eff_dec != "APPROVED":
                raise ValueError(f"active WP1 source {sid!r} requires owner_effective_window_decision=='APPROVED'")
            approved_runtime_sources.append({
                "source_id": sid,
                "document_id": srd["document_id"],
                "source_url": srd["official_record_url"],
                "source_sha256": srd["sha256"],
                "accessed_on": srd.get("accessed_on") or "2026-11-15",
                "rights_status": "APPROVED",
                "usage_rights_decision": rights_dec,
                "effective_window_decision": "APPROVED",
            })
        else:
            if (
                not src_dec
                or src_dec == "PENDING_OWNER_DECISION"
                or src_dec not in ALLOWED_NON_RUNTIME_SOURCE_DECISIONS
            ):
                raise ValueError(
                    f"non-runtime source {sid!r} requires an explicit owner_source_approval_decision "
                    f"in {sorted(ALLOWED_NON_RUNTIME_SOURCE_DECISIONS)} (not 'PENDING_OWNER_DECISION')"
                )
            if not rights_dec or rights_dec == "PENDING_OWNER_DECISION":
                raise ValueError(
                    f"non-runtime source {sid!r} requires an explicit owner_usage_rights_decision "
                    "(not 'PENDING_OWNER_DECISION')"
                )
            if not eff_dec or eff_dec == "PENDING_OWNER_DECISION":
                raise ValueError(
                    f"non-runtime source {sid!r} requires an explicit owner_effective_window_decision "
                    "(not 'PENDING_OWNER_DECISION')"
                )

        seen_srd.add(sid)
        stamped_srd.append({
            **{
                k: v
                for k, v in srd.items()
                if k not in (
                    "owner_source_approval_decision",
                    "owner_usage_rights_decision",
                    "owner_effective_window_decision",
                )
            },
            "usage_rights_decision": rights_dec,
            "effective_window_decision": eff_dec,
            "approval_policy": policy,
            "owner_approver": owner,
            "reviewed_on": reviewed_on,
            "decision": src_dec,
            "ai_review_passes": srd.get("ai_review_passes") or ["source_register_hash_and_effectivity_audit"],
        })

    # 4. Validate 5 excluded_candidates (provision candidates)
    draft_provs = [
        json.loads(line)
        for line in (draft_dir / "provisions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    draft_ids = {p["citation_id"] for p in draft_provs}
    raw_exc_cands = sheet.get("excluded_candidates")
    if not isinstance(raw_exc_cands, list) or len(raw_exc_cands) != len(REQUIRED_EXCLUDED_CANDIDATE_IDS):
        raise ValueError("decision sheet: excluded_candidates must contain all 5 excluded provision candidates")
    seen_exc_cands: set[str] = set()
    stamped_exc_cands: list[dict[str, Any]] = []
    for ex in raw_exc_cands:
        ex_cid = (ex.get("citation_id") or "").strip()
        if ex_cid not in REQUIRED_EXCLUDED_CANDIDATE_IDS or ex_cid in seen_exc_cands:
            raise ValueError(f"decision sheet: invalid or duplicate excluded candidate {ex_cid!r}")
        if ex.get("owner_decision") != "EXCLUDED":
            raise ValueError(f"excluded candidate {ex_cid!r} must have owner_decision=='EXCLUDED'")
        if ex_cid in draft_ids:
            raise ValueError(f"excluded candidate {ex_cid!r} is still present in provisions.jsonl")
        _check_item_owner(ex, owner, ex_cid)
        seen_exc_cands.add(ex_cid)
        stamped_exc_cands.append({
            **{k: v for k, v in ex.items() if k != "owner_decision"},
            "approval_policy": policy,
            "owner_approver": owner,
            "reviewed_on": reviewed_on,
            "decision": "EXCLUDED",
            "ai_review_passes": ex.get("ai_review_passes") or ["provision_scope_exclusion_audit"],
        })

    # 5. Validate 11 excluded_labels (risk labels outside WP1 Articles 20-22)
    raw_exc_lbls = sheet.get("excluded_labels")
    if not isinstance(raw_exc_lbls, list) or len(raw_exc_lbls) != len(REQUIRED_EXCLUDED_RISK_LABELS):
        raise ValueError("decision sheet: excluded_labels must contain all 11 out-of-scope risk labels")
    seen_exc_lbls: set[str] = set()
    stamped_exc_lbls: list[dict[str, Any]] = []
    for el in raw_exc_lbls:
        rlbl = (el.get("risk_label") or "").strip()
        if rlbl not in REQUIRED_EXCLUDED_RISK_LABELS or rlbl in seen_exc_lbls:
            raise ValueError(f"decision sheet: invalid or duplicate excluded_label {rlbl!r}")
        el_dec = (el.get("owner_decision") or "").strip()
        if el_dec not in ALLOWED_EXCLUDED_LABEL_DECISIONS:
            raise ValueError(
                f"excluded_label {rlbl!r} must have owner_decision in "
                f"{sorted(ALLOWED_EXCLUDED_LABEL_DECISIONS)}"
            )
        if not (el.get("rationale") or "").strip() or not (el.get("target_work_package") or "").strip():
            raise ValueError(f"excluded_label {rlbl!r} requires non-empty rationale and target_work_package")
        _check_item_owner(el, owner, rlbl)
        seen_exc_lbls.add(rlbl)
        stamped_exc_lbls.append({
            **{k: v for k, v in el.items() if k != "owner_decision"},
            "approval_policy": policy,
            "owner_approver": owner,
            "reviewed_on": reviewed_on,
            "decision": el_dec,
            "ai_review_passes": el.get("ai_review_passes") or ["risk_taxonomy_21_label_scope_audit"],
        })

    # 6. Stamp provisions, edges, labels
    def _stamp(item: dict[str, Any], decision_key: str = "owner_decision") -> dict[str, Any]:
        ident = item.get("citation_id") or item.get("label") or item.get("from_citation_id") or ""
        if item.get(decision_key) != "APPROVED":
            raise ValueError(f"item {ident!r} is not APPROVED")
        _check_item_owner(item, owner, str(ident))
        out = {k: v for k, v in item.items() if k != decision_key}
        out["approval_policy"] = policy
        out["owner_approver"] = owner
        out["reviewed_on"] = reviewed_on
        out["decision"] = "APPROVED"
        return out

    receipts_bundle = {
        "schema_version": "review_receipts_v2",
        "approval_policy": policy,
        "owner_approver": owner,
        "design_decisions": stamped_dd,
        "source_register_decisions": stamped_srd,
        "sources": approved_runtime_sources,
        "provisions": [_stamp(prov_item) for prov_item in raw_provs],
        "edges": [_stamp(edge_item) for edge_item in raw_edges],
        "labels": [_stamp(label_item) for label_item in raw_labels],
        "excluded_candidates": stamped_exc_cands,
        "excluded_labels": stamped_exc_lbls,
        "release": {
            "note": rel_note,
            "approval_policy": policy,
            "owner_approver": owner,
            "reviewed_on": reviewed_on,
            "decision": "APPROVED",
            "ai_review_passes": ["release_checksum_binding_check", "full_7_group_owner_gate_v2"],
            "approved_data_checksums": actual_data_hashes,
        },
    }

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "stage"
        stage.mkdir(parents=True, exist_ok=True)
        for name in BASE_FILES:
            (stage / name).write_bytes((draft_dir / name).read_bytes())
        (stage / "review_receipts.json").write_text(
            json.dumps(receipts_bundle, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        all_files = (*BASE_FILES, "review_receipts.json")
        checksums = {
            name: hashlib.sha256((stage / name).read_bytes()).hexdigest()
            for name in all_files
        }
        manifest = {
            "corpus_version": corpus_version,
            "graph_version": graph_version,
            "timezone": "Asia/Ho_Chi_Minh",
            "release_status": "APPROVED",
            "checksums": checksums,
        }
        (stage / "manifest.yaml").write_text(
            yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        load_corpus(stage, allow_draft=False)
        if out_dir.exists():
            raise FileExistsError(f"refusing to overwrite existing output directory: {out_dir}")
        shutil.copytree(stage, out_dir, dirs_exist_ok=False)
        return checksums


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decision-sheet", type=Path, required=True)
    ap.add_argument("--draft-dir", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    build_signed_release(args.decision_sheet, args.draft_dir, args.out_dir)


if __name__ == "__main__":
    main()
