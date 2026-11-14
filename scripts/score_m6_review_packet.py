"""Score a real 40-output human/judge packet after independent ratings exist."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

LABELS = {"DUNG", "DUNG_MOT_PHAN", "SAI"}
FIELDS = ("output_id", "human_a", "human_b", "human_adjudicated", "judge")


def _kappa(left: list[str], right: list[str]) -> float | None:
    n = len(left)
    observed = sum(a == b for a, b in zip(left, right)) / n
    counts_a, counts_b = Counter(left), Counter(right)
    expected = sum(counts_a[label] * counts_b[label] for label in LABELS) / (n * n)
    return (observed - expected) / (1 - expected) if expected < 1 else None


def score(path: Path) -> dict:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not set(FIELDS).issubset(reader.fieldnames or ()):
            raise ValueError(f"columns must include {FIELDS}")
        rows = list(reader)
    if (
        len(rows) != 40
        or len({row["output_id"] for row in rows}) != 40
        or any(not row["output_id"].strip() for row in rows)
    ):
        raise ValueError("require 40 unique real output IDs")
    for row in rows:
        if any(row[key] not in LABELS for key in FIELDS[1:]):
            raise ValueError(f"missing or invalid rating for {row['output_id']}")
    human_a = [row["human_a"] for row in rows]
    human_b = [row["human_b"] for row in rows]
    adjudicated = [row["human_adjudicated"] for row in rows]
    judge = [row["judge"] for row in rows]
    judge_agreement = sum(a == b for a, b in zip(adjudicated, judge)) / 40
    dev_scope = any(
        row.get("candidate_status") or row.get("document_id", "") in {"HDLD001", "HDLD002", "HDLD003", "HDLD004"}
        for row in rows
    )
    return {
        "status": (
            "D2_DEV_REVIEW_AGREEMENT_NOT_M6_ACCEPTANCE" if dev_scope else "M6_40_OUTPUT_RATINGS_SCORED_SCOPE_UNVERIFIED"
        ),
        "n": 40,
        "acceptance_scope_verified": False,
        "judge_human_agreement": judge_agreement,
        "judge_human_kappa": _kappa(adjudicated, judge),
        "m6_threshold_met": judge_agreement >= 0.80,
        "human_a_b_agreement": sum(a == b for a, b in zip(human_a, human_b)) / 40,
        "human_a_b_kappa": _kappa(human_a, human_b),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ratings", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = score(args.ratings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
