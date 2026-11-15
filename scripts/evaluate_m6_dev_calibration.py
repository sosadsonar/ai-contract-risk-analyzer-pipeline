"""Rule cross-check of 40 D2 Dev outputs; never M6 human acceptance."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

from app.domain.errors import AiOutputInvalid
from app.legal.corpus_loader import load_corpus
from app.privacy.masker import mask
from app.session.pipeline_runner import sanitize_advice_sentences

from scripts.score_m6_review_packet import FIELDS, score

_DOCUMENT = re.compile(
    r"giấy\s+tờ|căn\s+cước|cccd|cmnd|văn\s+bằng|bằng\s+(?:tốt\s+nghiệp|đại\s+học|cấp)"
    r"|chứng\s+chỉ|hồ\s+sơ|hộ\s+chiếu"
)
_ORIGINAL = re.compile(
    r"bản\s+gốc|bản\s+chính|giấy\s+tờ\s+gốc|hồ\s+sơ\s+gốc|văn\s+bằng\s+gốc"
    r"|chứng\s+chỉ\s+gốc|bằng\s+tốt\s+nghiệp"
)
_RETENTION = re.compile(r"giữ|nộp|giao|lưu|thu|quản\s+lý|trả\s+lại|nhận\s+lại")
_SECURITY = re.compile(
    r"đặt\s+cọc|ký\s+quỹ|bảo\s+đảm|thế\s+chân|thế\s+chấp|cầm\s+cố"
    r"|phong\s+tỏa|khấu\s+trừ|trích\s+lương|tạm\s+giữ\s+lương"
)
_DEBT = re.compile(r"nợ|vay|tạm\s+ứng")
_WORK = re.compile(r"làm\s+việc|thực\s+hiện\s+hợp\s+đồng|nghỉ\s+việc|chấm\s+dứt|phục\s+vụ\s+công\s+ty")
_NEGATED = re.compile(
    r"không\s+(?:được\s+)?(?:giữ|thu\s+giữ|yêu\s+cầu\s+đặt\s+cọc|phải\s+đặt\s+cọc)"
)
_CITATION_TYPES = {
    "BLLD2019:art17:cl1": "document",
    "BLLD2019:art17:cl2": "security",
    "BLLD2019:art17:cl3": "debt",
}


def judge_candidate(row: dict, valid_citations: set[str]) -> str:
    """Independent lexical cross-check of evidence, citation type and explanation."""
    text = row["masked_clause_text"].casefold()
    document = bool(_DOCUMENT.search(text) and _ORIGINAL.search(text)
                    and _RETENTION.search(text) and not _NEGATED.search(text))
    security = bool(_SECURITY.search(text) and not _NEGATED.search(text))
    debt = bool(_DEBT.search(text) and _WORK.search(text))
    label = row["risk_label"]
    risk_present = ((document or security) if label == "DEPOSIT_DOCUMENT_HELD"
                    else debt if label == "EMPLOYEE_OBLIGATIONS_DISCIPLINE" else False)
    if not risk_present:
        return "SAI"
    citation = row["citation_candidate"]
    kind = _CITATION_TYPES.get(citation)
    citation_correct = (citation in valid_citations and
                        ((kind == "document" and document) or
                         (kind == "security" and security) or
                         (kind == "debt" and debt)))
    explanation = row["explanation_candidate"]
    try:
        _, changed = sanitize_advice_sentences(explanation)
    except AiOutputInvalid:
        changed = True
    semantic_hint = (_DOCUMENT.search(explanation.casefold()) or
                     re.search(r"giữ|bảo\s+đảm", explanation.casefold())) if kind != "debt" else (
                         _DEBT.search(explanation.casefold()) and _WORK.search(explanation.casefold()))
    explanation_ok = len(explanation.strip()) >= 10 and not changed and bool(semantic_hint)
    return "DUNG" if citation_correct and explanation_ok else "DUNG_MOT_PHAN"


def calibrate_rows(packet: list[dict], draft: list[dict],
                   valid_citations: set[str]) -> dict:
    """Score synthetic copies of one approved reviewer; never claim two humans."""
    if len(packet) != 40 or len(draft) != 40:
        raise ValueError("Dev calibration requires exactly 40 rows in both files")
    packet_ids = [row["output_id"] for row in packet]
    draft_by_id = {row["output_id"]: row for row in draft}
    if (len(set(packet_ids)) != 40 or len(draft_by_id) != 40
            or set(packet_ids) != set(draft_by_id)):
        raise ValueError("packet and draft output IDs do not match")
    generated = []
    for row in packet:
        human = draft_by_id[row["output_id"]]
        if human["human_a"] != "DUNG" or any(
            human.get(field) for field in ("human_b", "human_adjudicated", "judge")
        ):
            raise ValueError("single-reviewer Dev draft must have only approved human_a")
        generated.append({"output_id": row["output_id"], "human_a": "DUNG",
                          "human_b": "DUNG", "human_adjudicated": "DUNG",
                          "judge": judge_candidate(row, valid_citations),
                          "document_id": row["document_id"],
                          "candidate_status": "SYNTHETIC_SINGLE_REVIEWER_DEV"})
    with tempfile.TemporaryDirectory(prefix="m6_dev_calibration_") as directory:
        path = Path(directory) / "ratings_synthetic.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=[*FIELDS, "document_id", "candidate_status"])
            writer.writeheader()
            writer.writerows(generated)
        result = score(path)
    return {
        **result,
        "mode": "SINGLE_REVIEWER_APPROVED_DEV_CALIBRATION",
        "judge_type": "DETERMINISTIC_LEXICAL_ARTICLE17_CROSSCHECK",
        "human_b_is_synthetic_copy": True,
        "adjudication_is_human_a_copy": True,
        "m6_acceptance_met": False,
        "judge_rating_counts": dict(Counter(row["judge"] for row in generated)),
        "limitations": [
            "The automated judge is a distinct lexical cross-check, not a human or independent LLM judge.",
            "human_b and adjudication are synthetic copies of human_a; kappa is not independent human agreement.",
            "The threshold flag applies to Dev calibration only; M6 acceptance requires independent real ratings.",
        ],
    }


def evaluate(data_root: Path, corpus_root: Path, *, as_of: date) -> dict:
    restricted = data_root / "data" / "intake" / "restricted"
    folder = restricted / "M6_D2_dev_candidate_review_v01"
    packet_path = folder / "D2_40_risk_candidates_for_review.csv"
    draft_path = folder / "D2_40_ratings_ducanh_draft.csv"
    with packet_path.open(encoding="utf-8-sig", newline="") as stream:
        packet = list(csv.DictReader(stream))
    with draft_path.open(encoding="utf-8-sig", newline="") as stream:
        draft = list(csv.DictReader(stream))
    corpus = load_corpus(corpus_root)
    if corpus.release_status != "APPROVED":
        raise ValueError("legal corpus must be approved")
    valid = {p.citation_id for p in corpus.provisions
             if p.document_id == "BLLD2019" and p.article == "17"
             and p.citation_id in _CITATION_TYPES and p.effective_from <= as_of
             and (p.effective_to is None or as_of <= p.effective_to)}
    source_cache = {}
    for row in packet:
        doc = row["document_id"]
        if doc not in {"HDLD001", "HDLD002", "HDLD003", "HDLD004"}:
            raise ValueError("packet contains a document outside D2 Dev")
        if doc not in source_cache:
            source_path = restricted / "D2_candidate_v02" / f"{doc}.d2_candidate.txt"
            source_cache[doc] = (source_path.read_text(encoding="utf-8"),
                                 hashlib.sha256(source_path.read_bytes()).hexdigest())
        source, digest = source_cache[doc]
        start, end = int(row["start_char"]), int(row["end_char"])
        if (row["source_sha256"] != digest or not 0 <= start < end <= len(source)
                or mask(source).masked_text[start:end] != row["masked_clause_text"]):
            raise ValueError("D2 Dev packet source provenance or span mismatch")
    return {**calibrate_rows(packet, draft, valid),
            "as_of": as_of.isoformat(), "corpus_version": corpus.corpus_version,
            "packet_sha256": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
            "draft_sha256": hashlib.sha256(draft_path.read_bytes()).hexdigest(),
            "source_provenance_checks": len(packet)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--corpus-root", type=Path, default=Path("data/legal_corpus"))
    parser.add_argument("--as-of", type=date.fromisoformat, default=date(2026, 11, 12))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.data_root, args.corpus_root, as_of=args.as_of)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": result["mode"], "n": result["n"],
                      "judge_human_agreement": result["judge_human_agreement"],
                      "acceptance_scope_verified": result["acceptance_scope_verified"]}))


if __name__ == "__main__":
    main()
