"""Mở rộng label_map nháp cấp Điều (`data/label_map.yaml`, N3) thành ID cấp Khoản có trong corpus (X-24, PR #30).

Validator corpus yêu cầu mọi ID trong label_map tồn tại trong provisions. Nháp của N3 dùng ID cấp Điều
(`BLLD2019:art25`); corpus mức Khoản có `BLLD2019:art25:cl1`, `:cl2`... Công cụ này thay mỗi ID Điều bằng mọi
Khoản con (cùng trọng số); Điều không chia khoản giữ nguyên ID Điều. ID chưa có trong corpus được liệt kê ở
stderr và BỎ khỏi đầu ra (không bịa ID). Không tự sửa corpus thật; N2 review rồi ghi file + băm lại checksum.

Dùng: python scripts/expand_label_map.py data/label_map.yaml data/legal_corpus/provisions.jsonl > label_map.yaml
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

import yaml


def expand(draft: dict[str, dict[str, float]], provisions: list[dict]) -> tuple[dict, list[str]]:
    ids = {p["citation_id"] for p in provisions}
    # Điều → các nút con gần nhất có trong corpus: Khoản (độ sâu 3); nếu corpus chỉ có Điểm (độ sâu 4) thì dùng Điểm.
    by_depth: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    for p in provisions:
        path = p["parent_path"]
        if len(path) >= 3:
            by_depth[":".join(path[:2])][len(path)].append(p["citation_id"])
    children = {art: depths[min(depths)] for art, depths in by_depth.items()}
    out: dict[str, dict[str, float]] = {}
    missing: list[str] = []
    for label, weights in draft.items():
        target: dict[str, float] = {}
        for cid, weight in (weights or {}).items():
            expanded = sorted(children.get(cid, [])) or ([cid] if cid in ids else [])
            if not expanded:
                missing.append(f"{label}: {cid}")
            for x in expanded:
                target[x] = max(target.get(x, 0.0), float(weight))
        if target:
            out[label] = target
    return out, missing


def main() -> None:
    draft_path, provisions_path = sys.argv[1], sys.argv[2]
    with open(draft_path, encoding="utf-8") as fh:
        draft = yaml.safe_load(fh) or {}
    with open(provisions_path, encoding="utf-8") as fh:
        provisions = [json.loads(line) for line in fh if line.strip()]
    out, missing = expand(draft, provisions)
    for item in missing:
        print(f"PENDING (không có trong corpus): {item}", file=sys.stderr)
    sys.stdout.write(yaml.safe_dump(out, allow_unicode=True, sort_keys=False))


if __name__ == "__main__":
    main()
