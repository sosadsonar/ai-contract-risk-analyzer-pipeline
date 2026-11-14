"""X-24: parse văn bản luật (text đã chép từ nguồn chính thức) thành provisions.jsonl mức Khoản.

Dùng một lần cho mọi văn bản. KHÔNG thay thẩm định pháp lý: đầu ra là bản nháp để N2 + reviewer đối chiếu
nguyên văn, điều/khoản và hiệu lực trước khi đưa vào corpus (README `data/legal_corpus`, X-25).

Quy tắc (PROGRESS X-24):
  * Nút Điều: `<DOC>:art<N>`, content = DÒNG TIÊU ĐỀ (+ đoạn dẫn trước khoản 1 nếu có) khi Điều có khoản —
    retriever không dùng nút này làm seed BM25; Điều KHÔNG chia khoản ⇒ content = toàn văn Điều.
  * Nút Khoản: `<DOC>:art<N>:cl<K>`, content = toàn văn Khoản kể cả các điểm a), b)... (không tách nút điểm).
  * parent_path chuẩn [DOC, artN(, clK)]; `clause`/`point` theo schema corpus.

Dùng:
  python scripts/parse_legal_text.py luat.txt --document-id BLLD2019 --document-name "Bộ luật Lao động số 45/2019/QH14" \\
      --version 45/2019/QH14 --effective-from 2021-01-01 [--articles 25,26,35] > draft.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from typing import Iterable

ARTICLE = re.compile(r"^\s*Điều\s+(\d+[a-zđ]?)\s*[.:]\s*(.*)$", re.IGNORECASE)
CLAUSE = re.compile(r"^\s*(\d{1,3})\s*[.)]\s+(\S.*)$")
STRUCTURE_BREAK = re.compile(r"^\s*(Chương|Mục)\s+[IVXLCDM\d]+\b", re.IGNORECASE)


def parse(text: str, *, document_id: str, document_name: str, version: str, effective_from: str,
          effective_to: str | None = None, articles: Iterable[str] | None = None) -> list[dict]:
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    wanted = {a.lower() for a in articles} if articles else None
    out: list[dict] = []
    art_num = art_title = None
    art_body: list[str] = []
    clauses: list[tuple[str, list[str]]] = []

    def base(cid: str, article: str, clause: str | None, path: list[str], content: str) -> dict:
        return {"citation_id": cid, "document_id": document_id, "document_name": document_name, "version": version,
                "article": article, "clause": clause, "point": None, "parent_path": path,
                "content": content.strip(), "effective_from": effective_from, "effective_to": effective_to}

    def flush() -> None:
        if art_num is None or (wanted is not None and art_num.lower() not in wanted):
            return
        art_id = f"{document_id}:art{art_num}"
        title_line = f"Điều {art_num}. {art_title}".strip()
        if clauses:
            # Đoạn dẫn trước khoản 1 (nếu có) giữ cùng nút Điều để không mất chữ; nút này vẫn không làm seed BM25.
            out.append(base(art_id, art_num, None, [document_id, f"art{art_num}"], "\n".join([title_line, *art_body])))
            seen = set()
            for num, lines in clauses:
                if num in seen:
                    raise ValueError(f"Điều {art_num}: khoản {num} lặp lại")
                seen.add(num)
                out.append(base(f"{art_id}:cl{num}", art_num, num, [document_id, f"art{art_num}", f"cl{num}"],
                                "\n".join(lines)))
        else:
            out.append(base(art_id, art_num, None, [document_id, f"art{art_num}"],
                            "\n".join([title_line, *art_body])))

    for raw in text.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        m = ARTICLE.match(line)
        if m:
            flush()
            art_num, art_title, art_body, clauses = m.group(1), m.group(2).strip(), [], []
            continue
        if STRUCTURE_BREAK.match(line):
            flush()
            art_num, art_body, clauses = None, [], []
            continue
        if art_num is None:
            continue
        c = CLAUSE.match(line)
        if c:
            clauses.append((c.group(1), [line.strip()]))
        elif clauses:
            clauses[-1][1].append(line.strip())
        else:
            art_body.append(line.strip())
    flush()
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("source")
    ap.add_argument("--document-id", required=True)
    ap.add_argument("--document-name", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--effective-from", required=True)
    ap.add_argument("--effective-to")
    ap.add_argument("--articles", help="danh sách Điều cần lấy, vd 25,26,35 (mặc định: tất cả)")
    args = ap.parse_args()
    with open(args.source, encoding="utf-8") as fh:
        rows = parse(fh.read(), document_id=args.document_id, document_name=args.document_name,
                     version=args.version, effective_from=args.effective_from, effective_to=args.effective_to,
                     articles=args.articles.split(",") if args.articles else None)
    for row in rows:
        sys.stdout.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
