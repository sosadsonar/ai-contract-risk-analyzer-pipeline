"""Read a complete, source-pinned single-Owner D2 Gold export for Dev oracle only."""

import csv
import hashlib
import json
from datetime import date
from pathlib import Path

from app.clause.taxonomy import validate_labels
from app.legal.corpus_loader import _valid_human_id

from scripts.align_d2_source_labels import checked_geometry


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_d2_gold(restricted: Path, gold_dir: Path, review_packet: Path):
    """Check all250 units, not merely the30 injection spans used by M8."""
    manifest_path = gold_dir / "manifest.json"
    manifest = _json(manifest_path)
    policy = "OWNER_SINGLE_APPROVER_AI_ASSISTED_V1"
    docs = {f"HDLD{i:03}" for i in range(1, 5)}
    if (manifest.get("schema_version") != "d2_clause_label_gold_manifest_v2"
            or manifest.get("status") != "GOLD_ADJUDICATED"
            or manifest.get("taxonomy_version") != "clause_taxonomy_v03"
            or manifest.get("approval_governance_mode") != policy
            or sorted(manifest.get("documents", [])) != sorted(docs)
            or manifest.get("items") != 250 or not manifest.get("dataset_version")):
        raise ValueError("D2 Gold manifest is incomplete or not adjudicated")
    if _sha(review_packet) != manifest.get("packet_sha256"):
        raise ValueError("D2 Owner review packet checksum mismatch")
    with review_packet.open(encoding="utf-8-sig", newline="") as stream:
        packet = list(csv.DictReader(stream))
    reviewed, owners = {}, set()
    for row in packet:
        key = row["document_id"], row["d2_gold_clause_ref"]
        owner = row["reviewer_n1"].strip()
        try:
            reviewed_on = date.fromisoformat(row["reviewed_on"])
        except (TypeError, ValueError) as exc:
            raise ValueError("D2 Owner review date is invalid") from exc
        if (key in reviewed or key[0] not in docs or row["decision"] != "APPROVED"
                or not _valid_human_id(owner) or row["reviewer_n2"].strip()
                or reviewed_on.isoformat() != row["reviewed_on"] or reviewed_on > date.today()
                or row["taxonomy_version"] != "clause_taxonomy_v03"):
            raise ValueError("D2 Owner review is incomplete, duplicated or invalid")
        owners.add(owner)
        reviewed[key] = row
    if len(reviewed) != 250 or len(owners) != 1:
        raise ValueError("D2 Gold requires all250 units and one actual Owner")
    result = {}
    hashes = {"manifest.json": _sha(manifest_path), "owner_review.csv": _sha(review_packet)}
    for doc in sorted(docs):
        source = restricted / f"D2_candidate_v02/{doc}.d2_candidate.txt"
        geometry = restricted / f"D2_segmentation_gold_v02/{doc}.gold_segmentation.json"
        file = gold_dir / f"{doc}.gold_clause_labels.json"
        if (_sha(source) != manifest.get("d2_sources_sha256", {}).get(doc)
                or _sha(geometry) != manifest.get("d2_segmentation_sha256", {}).get(doc)
                or _sha(file) != manifest.get("gold_files_sha256", {}).get(file.name)):
            raise ValueError("D2 Gold/source/geometry checksum mismatch")
        geom = _json(geometry)
        text = checked_geometry(source.read_bytes(), geom)
        if geom.get("status") != "ADJUDICATED_D2_GOLD_V02":
            raise ValueError("D2 geometry is not the adjudicated v02 source")
        payload = _json(file)
        if (payload.get("status") != "GOLD_ADJUDICATED" or payload.get("schema_version") != "clause_labels_v1"
                or payload.get("taxonomy_version") != "clause_taxonomy_v03"
                or payload.get("approval_governance_mode") != policy):
            raise ValueError("D2 clause Gold status or taxonomy mismatch")
        labels = {}
        for item in payload["items"]:
            ref = item["clause_id"]
            if ref in labels:
                raise ValueError("duplicate D2 clause Gold ref")
            labels[ref] = validate_labels(item["labels"])
        if set(labels) != {s["gold_clause_ref"] for s in geom["segments"]}:
            raise ValueError("D2 Gold does not cover exact segmentation refs")
        for span in geom["segments"]:
            ref = span["gold_clause_ref"]
            row = reviewed.get((doc, ref), {})
            start, end = span["start_char"], span["end_char"]
            reviewed_labels = [label.strip() for label in row.get("adjudicated_labels", "").split(";")]
            if (reviewed_labels != labels[ref]
                    or row.get("start_char") != str(start) or row.get("end_char") != str(end)
                    or row.get("d2_source_sha256") != _sha(source)
                    or row.get("span_sha256") != hashlib.sha256(text[start:end].encode()).hexdigest()):
                raise ValueError("D2 reviewed labels or source span binding changed")
        hashes[file.name] = _sha(file)
        result[doc] = labels
    return result, {"dataset_version": manifest["dataset_version"], "input_sha256": hashes}
