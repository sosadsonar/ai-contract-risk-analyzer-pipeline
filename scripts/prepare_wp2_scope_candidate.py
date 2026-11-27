"""Fixed synthetic controls for broad WP2 mappings; every output remains DRAFT."""

import argparse
import copy
import hashlib
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import yaml
from app.legal.baseline_retriever import BaselineRetriever
from app.legal.corpus_loader import load_corpus
from app.legal.data_graph import DataGraph, get_candidates

DELEGATED = {f"BLLD2019:art{art}:cl{cl}" for art, cl in
             [(46, 4), (47, 4), (96, 3), (98, 4), (107, 5), (112, 3), (113, 7)]}
EMPLOYER = "EMPLOYER_RIGHTS_OBLIGATIONS"
EMPLOYEE = "EMPLOYEE_OBLIGATIONS_DISCIPLINE"
# Predeclared source-based controls: no real D1/D2/T1/T2 examples or tuning.
CONTROLS = (
    (EMPLOYER, "BLLD2019:art29:cl1", "Công ty tạm thời chuyển người lao động làm công việc khác khi xảy ra thiên tai, "
     "không quá 60 ngày làm việc cộng dồn trong năm."),
    (EMPLOYER, "BLLD2019:art29:cl2", "Khi tạm chuyển công việc khác, công ty báo trước ít nhất 03 ngày làm việc, "
     "thông báo thời hạn và bố trí việc phù hợp sức khỏe, giới tính."),
    (EMPLOYER, "BLLD2019:art29:cl3", "Lương công việc mới khi tạm điều chuyển bằng ít nhất 85 phần trăm lương cũ, "
     "giữ nguyên lương cũ trong 30 ngày làm việc."),
    (EMPLOYER, "BLLD2019:art29:cl4", "Người lao động không đồng ý tạm làm việc khác quá 60 ngày và phải ngừng việc; "
     "công ty trả tiền lương ngừng việc."),
    (EMPLOYER, "BLLD2019:art33:cl1", "Bên yêu cầu sửa đổi nội dung hợp đồng thông báo trước ít nhất 03 ngày làm việc "
     "về nội dung cần sửa đổi, bổ sung."),
    (EMPLOYER, "BLLD2019:art33:cl2", "Hai bên thỏa thuận sửa đổi hợp đồng bằng ký phụ lục hoặc giao kết hợp đồng lao động mới."),
    (EMPLOYER, "BLLD2019:art33:cl3", "Hai bên không thỏa thuận được việc sửa đổi nên tiếp tục thực hiện hợp đồng lao động đã giao kết."),
    (EMPLOYEE, "BLLD2019:art127:cl1", "Công ty áp dụng kỷ luật bằng hành vi xúc phạm danh dự, nhân phẩm và xâm phạm sức khỏe của người lao động."),
    (EMPLOYEE, "BLLD2019:art127:cl2", "Người lao động bị phạt tiền và cắt lương thay cho xử lý kỷ luật lao động."),
    (EMPLOYEE, "BLLD2019:art127:cl3", "Công ty xử lý kỷ luật một hành vi không được quy định trong nội quy, hợp đồng hoặc pháp luật lao động."),
)
NEGATIVES = {
    EMPLOYER: (
        "Công ty trả lương đầy đủ đúng kỳ và thực hiện nghĩa vụ đóng bảo hiểm xã hội theo thỏa thuận.",
        "Công ty cung cấp máy tính và chỗ làm việc để người lao động thực hiện nhiệm vụ.",
    ),
    EMPLOYEE: (
        "Người lao động bảo mật thông tin khách hàng trong khi thực hiện công việc.",
        "Người lao động báo cáo tiến độ công việc cho quản lý vào cuối mỗi tuần.",
    ),
}


def revised_mappings(original):
    result = copy.deepcopy(original)
    for mappings in result.values():
        for cid in DELEGATED:
            mappings.pop(cid, None)
    cid = "BLLD2019:art26"
    weight = result["CONTRACT_TERM"].pop(cid)
    if cid in result.get("COMPENSATION_BENEFITS", {}):
        raise ValueError("art26 already has a compensation link; refusing silent overwrite")
    result.setdefault("COMPENSATION_BENEFITS", {})[cid] = weight
    return result


def scope_exposure(before, after):
    """Flag new top5 hits or promotion into top3 on an unrelated negative query."""
    old = before if before is not None else 10**9
    return after is not None and ((after <= 5 < old) or (after <= 3 and after < old))


def recommended_review_rows(rows):
    broad_pairs = {(label, cid) for label, cid, _ in CONTROLS}
    return [copy.deepcopy(row) for row in rows if row["citation_id"] not in DELEGATED
            and (row["label"], row["citation_id"]) not in broad_pairs]


def run(base_dir: Path, wp2_dir: Path, output: Path):
    if output.exists():
        raise FileExistsError(output)
    base = load_corpus(base_dir, allow_draft=True)
    wp2 = load_corpus(wp2_dir, allow_draft=True)
    wp_ids = {p.citation_id for p in wp2.provisions}
    if not DELEGATED <= wp_ids or len(wp2.provisions) != 125:
        raise ValueError("WP2 input differs from the audited125-node candidate")
    old_mapping = wp2.label_map
    amended = revised_mappings(old_mapping)
    if sum(map(len, amended.values())) != 93:
        raise ValueError("expected93 WP2 mapping pairs before scope controls")
    eligible = tuple(p for p in wp2.provisions if p.citation_id not in DELEGATED)
    combined_map = copy.deepcopy(base.label_map)
    for label, mapping in amended.items():
        combined_map.setdefault(label, {}).update(mapping)
    combined = replace(base, release_status="DRAFT", corpus_version="wp2_synthetic_scope_only_v1",
                       provisions=base.provisions+eligible, label_map=combined_map)
    cfg = type("Cfg", (), {"RETRIEVAL_FINAL_K": 8, "DATA_GRAPH_ENABLED": True,
                          "GRAPH_MAX_NEIGHBORS_PER_SEED": 4, "GRAPH_MAX_CHILDREN_PER_SEED": 2})()
    as_of = date(2026, 11, 12)

    def ranks(corpus, query, label, target):
        retriever = BaselineRetriever(corpus, final_k=8, seed_k=3, allow_draft=True)
        graph = DataGraph(corpus, allow_draft=True)
        off = retriever.retrieve(query, [label], as_of=as_of).baseline_pool
        on, _ = get_candidates(retriever, graph, query, [label], as_of, cfg)
        result = {}
        for name, rows in [("off", off), ("on", on)]:
            ids = [r.citation_id for r in rows]
            result[name+"_rank"] = ids.index(target)+1 if target in ids else None
            result[name+"_top8"] = ids
        return result

    summaries, cases = [], []
    for label, target, positive in CONTROLS:
        without_map = copy.deepcopy(combined.label_map)
        del without_map[label][target]
        without = replace(combined, label_map=without_map)
        mapping_rows = []
        for index, (kind, query) in enumerate([("POSITIVE_TOPIC", positive), *[("NEGATIVE_UNRELATED", q) for q in NEGATIVES[label]]]):
            before, after = ranks(without, query, label, target), ranks(combined, query, label, target)
            exposed = kind == "NEGATIVE_UNRELATED" and any(scope_exposure(before[k+"_rank"], after[k+"_rank"]) for k in ["off", "on"])
            row = {"control_id": f"{target}:{index}", "label": label, "citation_id": target,
                   "kind": kind, "synthetic_query": query, "without_target_mapping": before,
                   "with_target_mapping": after, "new_negative_scope_exposure": exposed}
            cases.append(row)
            mapping_rows.append(row)
        positive_hit = any(mapping_rows[0]["with_target_mapping"][k+"_rank"] is not None
                           and mapping_rows[0]["with_target_mapping"][k+"_rank"] <= 5 for k in ["off", "on"])
        exposure_count = sum(r["new_negative_scope_exposure"] for r in mapping_rows)
        summaries.append({"label": label, "citation_id": target, "positive_top5_in_either_view": positive_hit,
                          "negative_exposure_cases": exposure_count,
                          "control_verdict": "HOLD_SCOPE_EXPOSURE" if exposure_count else
                          "HOLD_POSITIVE_COVERAGE_GAP" if not positive_hit else "NO_FAILURE_IN_LIMITED_SYNTHETIC_CONTROLS",
                          "owner_decision": "", "legal_approval": False})
    # No synthetic pass authorizes legal activation; keep all10 outside the recommended label map.
    recommended = copy.deepcopy(amended)
    for label, cid, _ in CONTROLS:
        del recommended[label][cid]
    output.mkdir(parents=True, exist_ok=False)
    draft = output/"draft"
    draft.mkdir()
    raw = [json.loads(s) for s in (wp2_dir/"provisions.jsonl").read_text(encoding="utf-8").splitlines()]
    (draft/"provisions.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False)+"\n"
        for p in raw if p["citation_id"] not in DELEGATED), encoding="utf-8")
    (draft/"edges.jsonl").write_bytes((wp2_dir/"edges.jsonl").read_bytes())
    (draft/"label_map.yaml").write_text(yaml.safe_dump(recommended, allow_unicode=True, sort_keys=True), encoding="utf-8")
    manifest = {"corpus_version": "legal_corpus_2026-11-24_v2_wp2_scope_draft_v04",
                "graph_version": "data_graph_2026-11-24_wp2_scope_draft_v04", "timezone": "Asia/Ho_Chi_Minh",
                "release_status": "DRAFT", "checksums": {n: hashlib.sha256((draft/n).read_bytes()).hexdigest()
                    for n in ["provisions.jsonl", "edges.jsonl", "label_map.yaml"]}}
    (draft/"manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    load_corpus(draft, allow_draft=True)
    for name in ["sources_pending.json", "provenance_pending.json", "mapping_review_pending.json"]:
        data = json.loads((wp2_dir/name).read_text(encoding="utf-8"))
        if name == "provenance_pending.json":
            data = [r for r in data if r["citation_id"] not in DELEGATED]
        if name == "mapping_review_pending.json":
            data = recommended_review_rows(data)
            for row in data:
                if row["citation_id"] == "BLLD2019:art26":
                    row["label"] = "COMPENSATION_BENEFITS"
                    row["rationale"] = "Probation salary content; label revised after independent audit. Still DRAFT."
            expected_pairs = {(label, cid) for label, weights in recommended.items() for cid in weights}
            if {(row["label"], row["citation_id"]) for row in data} != expected_pairs:
                raise ValueError("WP2 review queue must match every recommended label-citation pair")
        (output/name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (output/"held_delegated_provisions.json").write_text(json.dumps(
        [p for p in raw if p["citation_id"] in DELEGATED], ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    summary = {"status": "WP2_DRAFT_NOT_LEGAL_APPROVAL", "original_provisions": 125,
               "recommended_provisions": 118, "delegated_provisions_held": sorted(DELEGATED),
               "original_mapping_pairs": 100, "trial_mapping_pairs": 93, "recommended_mapping_pairs": 83,
               "broad_mapping_count": 10, "synthetic_cases": len(cases), "manual_edges": 0,
               "negative_exposure_case_count": sum(r["new_negative_scope_exposure"] for r in cases),
               "mapping_summaries": summaries, "new_owner_approvals": 0, "held_out_used": False,
               "limitations": ["Only1 positive and2 negatives per link, not statistical validation or legal approval.",
                               "Rank promotion is retrieval exposure, not measured M2 false positives.",
                               "Original scans, current effectivity and source rights remain pending."]}
    (output/"scope_controls.json").write_text(json.dumps({"summary": summary, "cases": cases}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", type=Path, required=True)
    parser.add_argument("--wp2-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.base_dir, args.wp2_dir, args.output)))
