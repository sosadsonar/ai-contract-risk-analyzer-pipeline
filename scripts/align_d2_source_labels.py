"""Source-aligned D2 annotation suggestions; never transfer human approval."""

import argparse
import csv
import hashlib
import json
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


def checked_geometry(raw, gold):
    if hashlib.sha256(raw).hexdigest() != gold["source_sha256"]:
        raise ValueError("source/geometry hash mismatch")
    text = raw.decode("utf-8")
    if unicodedata.normalize("NFC", text) != text:
        raise ValueError("canonical source is not NFC")
    seen, previous_end = set(), 0
    for s in gold["segments"]:
        start, end, ref = s["start_char"], s["end_char"], s["gold_clause_ref"]
        if (ref in seen or s["offset_unit"] != "unicode_code_point" or isinstance(start, bool) or isinstance(end, bool)
                or not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(text)
                or start < previous_end):
            raise ValueError("invalid, overlapping or duplicate source geometry")
        seen.add(ref)
        previous_end = end
    return text


def classification_text_anchors(source, rows, labels):
    if unicodedata.normalize("NFC", source) != source:
        raise ValueError("source must already be NFC before locating code-point spans")
    chars, positions = [], []
    for index, char in enumerate(source):
        if char.isspace():
            if chars and chars[-1] != " ":
                chars.append(" ")
                positions.append(index)
        else:
            chars.append(char)
            positions.append(index)
    normalized = "".join(chars).rstrip()
    anchors, reasons = [], Counter()
    for row in rows:
        if row.get("offset_quality") != "EXACT":
            reasons["CONTEXT_OR_NON_EXACT_EXCLUDED"] += 1
            continue
        ref = row["clause_id"]
        query = " ".join(unicodedata.normalize("NFC", row["clause_text"]).split())
        start = normalized.find(query) if query else -1
        if start < 0 or ref not in labels:
            reasons["NO_EXACT_TEXT_OR_LABEL_BINDING"] += 1
            continue
        if normalized.find(query, start+1) >= 0:
            reasons["NON_UNIQUE_SOURCE_TEXT"] += 1
            continue
        end = start+len(query)
        anchors.append({"ref": ref, "start": positions[start], "end": positions[end-1]+1, "labels": labels[ref]})
        reasons["UNIQUE_CLASSIFICATION_TEXT_ANCHOR"] += 1
    return anchors, dict(reasons)


def align_span(before, after, start, end, segments, blocks):
    unit = after[start:end]
    left, right = start + len(unit)-len(unit.lstrip()), end-(len(unit)-len(unit.rstrip()))
    result = {"status": "NEW_OR_CHANGED_SOURCE", "suggested_labels": [], "overlapping_d1_refs": []}
    if left >= right:
        return {**result, "status": "EMPTY_UNIT"}
    for block in blocks:
        if block.b <= left and right <= block.b + block.size:
            a, b = block.a + left-block.b, block.a + right-block.b
            text = before[a:b]
            assert text == after[left:right]
            result.update(source_start_char=a, source_end_char=b,
                          aligned_text_sha256=hashlib.sha256(text.encode()).hexdigest())
            if before.count(text) != 1:
                return {**result, "status": "AMBIGUOUS_REPEATED_SOURCE"}
            overlapping = [s for s in segments if max(a, s["start"]) < min(b, s["end"])]
            containing = [s for s in overlapping if s["start"] <= a and b <= s["end"]]
            result["overlapping_d1_refs"] = [{"ref": s["ref"], "labels": s["labels"]} for s in overlapping]
            result["context_label_candidates_not_transferred"] = sorted({label for s in overlapping for label in s["labels"]})
            if len(containing) == 1:
                s = containing[0]
                status = ("UNCHANGED_EXACT_LABELED_UNIT_REQUIRES_REVIEW" if (a, b) == (s["start"], s["end"])
                          else "UNCHANGED_CONTAINED_UNIT_REQUIRES_REVIEW")
                return {**result, "status": status, "suggested_labels": s["labels"]}
            return {**result, "status": "UNCHANGED_MIXED_OR_UNLABELED_UNIT_REQUIRES_REVIEW"}
    return result


def prepare(data_root: Path, output: Path, *, unit_source="geometry"):
    if output.exists():
        raise FileExistsError(output)
    root = data_root/"data/intake/restricted"
    if unit_source not in ("geometry", "classification_exact_text"):
        raise ValueError("invalid source unit method")
    rows, bindings, anchor_counts = [], {}, Counter()
    with (data_root/"data/processed/clauses_v06.csv").open(encoding="utf-8-sig", newline="") as stream:
        classification_rows = list(csv.DictReader(stream))
    for i in range(1, 5):
        doc = f"HDLD{i:03}"
        a_raw = (root/f"D1_m1_runtime_predictions_v01/{doc}.canonical_nfc.txt").read_bytes()
        b_raw = (root/f"D2_candidate_v02/{doc}.d2_candidate.txt").read_bytes()
        a_gold_path = root/f"D1_m1_gold_v01/{doc}.gold_segmentation.json"
        b_gold_path = root/f"D2_segmentation_gold_v02/{doc}.gold_segmentation.json"
        labels_path = root/f"D1_clause_label_gold_v01/{doc}.gold_clause_labels.json"
        a_gold, b_gold, labels = [json.loads(p.read_text(encoding="utf-8")) for p in (a_gold_path, b_gold_path, labels_path)]
        a_sha, b_sha = hashlib.sha256(a_raw).hexdigest(), hashlib.sha256(b_raw).hexdigest()
        a_text, b_text = checked_geometry(a_raw, a_gold), checked_geometry(b_raw, b_gold)
        by_ref = {r["clause_id"]: r["labels"] for r in labels["items"]}
        segments = [{"ref": s["gold_clause_ref"], "start": s["start_char"], "end": s["end_char"],
                     "labels": by_ref[s["gold_clause_ref"]]} for s in a_gold["segments"] if s["gold_clause_ref"] in by_ref]
        if unit_source == "classification_exact_text":
            segments, reasons = classification_text_anchors(
                a_text, [r for r in classification_rows if r["contract_id"] == doc], by_ref,
            )
            anchor_counts.update(reasons)
        blocks = SequenceMatcher(None, a_text, b_text, autojunk=False).get_matching_blocks()
        for s in b_gold["segments"]:
            start, end = s["start_char"], s["end_char"]
            if s["offset_unit"] != "unicode_code_point" or not 0 <= start < end <= len(b_text):
                raise ValueError("invalid D2 source span")
            rows.append({"document_id": doc, "d2_gold_clause_ref": s["gold_clause_ref"],
                         "d2_source_sha256": b_sha, "d1_source_sha256": a_sha,
                         "start_char": start, "end_char": end,
                         "span_sha256": hashlib.sha256(b_text[start:end].encode()).hexdigest(),
                         **align_span(a_text, b_text, start, end, segments, blocks),
                         "human_decision": "", "owner_approver": "", "reviewed_on": ""})
        bindings[doc] = {"d1": a_sha, "d2": b_sha,
                         "d1_geometry_sha256": hashlib.sha256(a_gold_path.read_bytes()).hexdigest(),
                         "d2_geometry_sha256": hashlib.sha256(b_gold_path.read_bytes()).hexdigest(),
                         "d1_labels_sha256": hashlib.sha256(labels_path.read_bytes()).hexdigest()}
    if len(rows) != 250:
        raise ValueError("D2 inventory is not the frozen250 units")
    output.mkdir(parents=True, exist_ok=False)
    (output/"source_alignment_suggestions.json").write_text(json.dumps(rows, indent=2)+"\n", encoding="utf-8")
    summary = {"status": "AI_REVIEW_ASSISTANCE_NOT_GOLD", "units": len(rows),
               "unit_source": unit_source, "classification_anchor_counts": dict(anchor_counts),
               "source_aligned_suggestions": sum(bool(r["suggested_labels"]) for r in rows),
               "partial_source_context_hints_not_transferred": sum(
                   not r["suggested_labels"] and bool(r.get("context_label_candidates_not_transferred")) for r in rows),
               "categories": dict(Counter(r["status"] for r in rows)), "source_bindings": bindings,
               "human_decisions_written": 0, "held_out_used": False,
               "limitations": ["Contained spans can change semantic unit; do not inherit Gold automatically.",
                               "Repeated text and mixed/unlabeled units require manual resolution.",
                               "New/changed source units are never assigned old labels by this method."]}
    (output/"summary.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--unit-source", choices=("geometry", "classification_exact_text"), default="geometry")
    args = parser.parse_args()
    print(json.dumps(prepare(args.data_root, args.output, unit_source=args.unit_source)))
