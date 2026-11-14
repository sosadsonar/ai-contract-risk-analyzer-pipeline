"""X-24: parser Điều/Khoản, mở rộng label_map nháp, nút Điều-tiêu-đề không làm seed BM25."""

import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from app.legal.baseline_retriever import BaselineRetriever  # noqa: E402
from app.legal.corpus_loader import LegalCorpus, LegalProvision  # noqa: E402
from app.legal.corpus_validator import validate_corpus  # noqa: E402
from expand_label_map import expand  # noqa: E402
from parse_legal_text import parse  # noqa: E402

TEXT = """Chương III
HỢP ĐỒNG LAO ĐỘNG
Điều 24. Thử việc
1. Người sử dụng lao động và người lao động có thể thỏa thuận nội dung thử việc.
2. Không áp dụng thử việc đối với người lao động giao kết hợp đồng dưới 01 tháng.
Điều 25. Thời gian thử việc
Thời gian thử việc do hai bên thỏa thuận và chỉ được thử việc một lần, bảo đảm điều kiện sau:
1. Không quá 180 ngày đối với công việc của người quản lý doanh nghiệp;
2. Không quá 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ cao đẳng trở lên;
a) điểm minh họa thuộc khoản 2;
Điều 26. Tiền lương thử việc
Tiền lương thử việc do hai bên thỏa thuận nhưng ít nhất phải bằng 85% mức lương của công việc đó.
"""


def _rows(**kw):
    return parse(TEXT, document_id="TEST", document_name="Luật thử", version="v", effective_from="2021-01-01", **kw)


def _corpus(rows, label_map=None):
    provisions = tuple(LegalProvision(**{**r, "parent_path": tuple(r["parent_path"]),
                                         "effective_from": date.fromisoformat(r["effective_from"]),
                                         "effective_to": None}) for r in rows)
    return LegalCorpus("c", "g", "Asia/Ho_Chi_Minh", "APPROVED", provisions, (),
                       label_map or {"CONTRACT_TERM": {"TEST:art26": 0.5}})


def test_parse_article_title_nodes_and_clause_nodes():
    rows = {r["citation_id"]: r for r in _rows()}
    assert rows["TEST:art25"]["content"].startswith("Điều 25. Thời gian thử việc\nThời gian thử việc do")
    assert rows["TEST:art24"]["content"] == "Điều 24. Thử việc"                      # chỉ tiêu đề
    assert rows["TEST:art25:cl2"]["content"].endswith("a) điểm minh họa thuộc khoản 2;")  # điểm nằm trong Khoản
    assert rows["TEST:art25:cl1"]["parent_path"] == ["TEST", "art25", "cl1"]
    assert "85%" in rows["TEST:art26"]["content"] and rows["TEST:art26"]["clause"] is None  # Điều không chia khoản
    validate_corpus(_corpus(_rows()))


def test_parse_article_filter():
    assert {r["article"] for r in _rows(articles=["26"])} == {"26"}


def test_expand_label_map_article_to_clauses():
    out, missing = expand({"CONTRACT_TERM": {"TEST:art25": 1.0, "TEST:art26": 0.5, "BHXH2024:art1": 1.0}}, _rows())
    assert out == {"CONTRACT_TERM": {"TEST:art25:cl1": 1.0, "TEST:art25:cl2": 1.0, "TEST:art26": 0.5}}
    assert missing == ["CONTRACT_TERM: BHXH2024:art1"]
    validate_corpus(_corpus(_rows(), out))


def test_title_only_article_never_wins_on_bm25():
    retriever = BaselineRetriever(_corpus(_rows()), final_k=3, seed_k=1)
    pool = retriever.retrieve("thời gian thử việc", ["CONTRACT_TERM"], as_of=date(2026, 1, 1)).baseline_pool
    by_id = {c.citation_id: c for c in pool}
    assert pool[0].citation_id != "TEST:art25"
    assert by_id.get("TEST:art25") is None or by_id["TEST:art25"].bm25_normalized == 0


def test_cli_outputs_jsonl(tmp_path):
    import subprocess
    src = tmp_path / "luat.txt"
    src.write_text(TEXT, encoding="utf-8")
    res = subprocess.run([sys.executable, str(ROOT / "scripts/parse_legal_text.py"), str(src), "--document-id", "TEST",
                          "--document-name", "Luật thử", "--version", "v", "--effective-from", "2021-01-01"],
                         capture_output=True, text=True, encoding="utf-8", env= {**os.environ, "PYTHONUTF8": "1"}, check=True)
    assert len([json.loads(x) for x in res.stdout.splitlines()]) == 7
