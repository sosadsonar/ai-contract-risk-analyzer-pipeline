#!/usr/bin/env python3
"""
split_doc.py - Tách tài liệu Markdown lớn (BRD / SRS / SDD / TDD) thành các
file con nhỏ, có mục lục + chỉ mục ID, để AI chỉ đọc đúng phần cần thiết.

Chỉ dùng thư viện chuẩn (Python >= 3.9). Không gọi mạng.

VÍ DỤ
-----
  # Chạy từ project root (mặc định: đọc docs/*.md, ghi docs/splitted_docs/)
  python scripts/split_doc.py

  # Tách riêng file TDD, mỗi file con tối đa ~8000 ký tự
  python split_doc.py docs/TDD_AI_Labor_Contract_Risk_Analyzer_v0.2.md --max-chars 8000

  # Chỉ xem sẽ tách thế nào (không ghi file)
  python split_doc.py docs --dry-run

  # Tìm ID (FR-12, DEC-27, C-05, M8, TDD-10, ...) nằm ở file con nào
  python scripts/split_doc.py --find FR-12

KẾT QUẢ (trong thư mục -o, mặc định docs/splitted_docs/ so với project root)
------------------------------------------------
  INDEX.md           mục lục tổng: mỗi tài liệu có bao nhiêu file con
  ID_INDEX.md        ID (FR-xx, DEC-xx, ...) -> file con chứa hàng bảng định nghĩa
  manifest.json      cùng thông tin cho công cụ/script
  <DOC>/_INDEX.md    mục lục từng tài liệu (file, tiêu đề, kích thước, ID)
  <DOC>/NN_slug.md   các file con (mỗi file có 1 dòng comment: nguồn, đường dẫn mục)

CÁCH TÁCH
---------
  1. Làm sạch: bỏ ảnh base64 (chiếm >40% dung lượng SDD/SRS), bỏ ký tự escape
     của Google Docs (\\-\\> -> ->, clause\\_id -> clause_id), rút gọn dòng
     phân cách bảng, bỏ khoảng trắng cuối dòng.
  2. Chọn mức heading để tách (--level, mặc định auto = mức nông nhất có >= 3 heading).
  3. Mục nào vượt --max-chars thì tách tiếp theo heading con; nếu không có
     heading con thì tách theo đoạn / theo dòng bảng (lặp lại dòng tiêu đề bảng).
  4. Không coi dòng '# ...' bên trong khối code ``` là heading.

Ước lượng token chỉ là xấp xỉ (ký tự / 3 cho tiếng Việt), dùng để so sánh.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# Regex
# --------------------------------------------------------------------------
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
# [image1]: <data:image/png;base64,....>
IMG_DEF_RE = re.compile(r"^\[[^\]]+\]:\s*<?data:image/\S+>?\s*$")
# ![alt][image1]  hoặc  ![alt](data:image/...)
IMG_REF_RE = re.compile(r"!\[([^\]]*)\]\[[^\]]+\]|!\[([^\]]*)\]\(data:image[^)]*\)")
# Escape kiểu Google Docs. Cố ý KHÔNG gỡ \| \* \` \\ để không phá bảng/in đậm/code.
ESC_RE = re.compile(r"\\([_\-.>+=#!~<\[\](){}])")
TABLE_SEP_RE = re.compile(r"^\s*\|(?:\s*:?-{3,}:?\s*\|)+\s*$")
# Hàng bảng bắt đầu bằng ID: | FR-01 | ... |, | M3a | ... |, | BL-1 | ... |
ID_ROW_RE = re.compile(r"^\|\s*\**`?([A-Z]{1,5}(?:-[A-Z]{2,6})?-?\d{1,3}[a-z]?)`?\**\s*\|", re.M)

# split_doc.py nằm ở <project_root>/scripts/ -> project root là thư mục cha của thư mục chứa file này.
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOCS = ROOT / "docs"
DEFAULT_OUT = DEFAULT_DOCS / "splitted_docs"

GENERATED_NAMES = {
    "AI_CONTEXT.md", "SKELETON.md", "ARCHITECTURE.md", "PROGRESS.md",
    "README.md", "INDEX.md", "ID_INDEX.md",
}


# --------------------------------------------------------------------------
# Tiện ích
# --------------------------------------------------------------------------
def slugify(text: str, max_len: int = 50) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return (text[:max_len].strip("-")) or "muc"


def est_tokens(chars: int) -> int:
    return round(chars / 3)


def clean_heading(raw: str) -> str:
    t = ESC_RE.sub(r"\1", raw)
    t = t.replace("**", "").replace("__", "")
    t = re.sub(r"\s+", " ", t).strip(" *_`")
    return t.strip()


def clean_lines(lines: list[str], keep_images: bool, keep_escapes: bool) -> list[str]:
    out: list[str] = []
    in_fence = False
    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line.rstrip())
            continue
        if in_fence:
            out.append(line.rstrip())
            continue
        if not keep_images:
            if IMG_DEF_RE.match(line):
                continue

            def _img(m: re.Match) -> str:
                alt = (m.group(1) or m.group(2) or "").strip()
                return f"[Hình: {alt}]" if alt else ""

            line = IMG_REF_RE.sub(_img, line)
        if not keep_escapes:
            line = ESC_RE.sub(r"\1", line)
        if TABLE_SEP_RE.match(line):
            line = "|" + "---|" * (line.count("|") - 1)
        out.append(line.rstrip())
    # gộp dòng trống liên tiếp, bỏ dòng trống đầu/cuối
    res: list[str] = []
    blank = 0
    for l in out:
        if l.strip() == "":
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        res.append(l)
    while res and not res[0].strip():
        res.pop(0)
    while res and not res[-1].strip():
        res.pop()
    return res


# --------------------------------------------------------------------------
# Parse -> Section
# --------------------------------------------------------------------------
@dataclass
class Section:
    level: int                       # 0 = phần trước heading đầu tiên
    title: str
    lines: list[str] = field(default_factory=list)
    path: list[str] = field(default_factory=list)

    def render(self) -> str:
        body = "\n".join(self.lines).strip("\n")
        if self.level == 0:
            return body
        head = f"{'#' * self.level} {self.title}"
        return f"{head}\n\n{body}" if body else head


def parse_sections(text: str, keep_images: bool, keep_escapes: bool) -> list[Section]:
    sections = [Section(0, "Preamble", [], [])]
    stack: list[tuple[int, str]] = []
    in_fence, fence_tok = False, ""
    for raw in text.splitlines():
        m = FENCE_RE.match(raw)
        if m:
            tok = m.group(1)
            if not in_fence:
                in_fence, fence_tok = True, tok
            elif tok == fence_tok:
                in_fence = False
            sections[-1].lines.append(raw)
            continue
        if not in_fence:
            h = HEADING_RE.match(raw)
            if h:
                title = clean_heading(h.group(2))
                if not title:        # '###' rỗng do Google Docs xuất ra
                    continue
                level = len(h.group(1))
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, title))
                sections.append(Section(level, title, [], [t for _, t in stack]))
                continue
        sections[-1].lines.append(raw)
    for s in sections:
        s.lines = clean_lines(s.lines, keep_images, keep_escapes)
    return sections


def auto_level(sections: list[Section]) -> int:
    counts = Counter(s.level for s in sections if s.level)
    for lvl in range(1, 7):
        if counts.get(lvl, 0) >= 3:
            return lvl
    return min(counts) if counts else 1


# --------------------------------------------------------------------------
# Chunk + tách theo kích thước
# --------------------------------------------------------------------------
@dataclass
class Piece:
    title: str
    path: list[str]
    text: str


def render_all(sections: list[Section]) -> str:
    return "\n\n".join(r for r in (s.render() for s in sections) if r.strip())


def build_chunks(sections: list[Section], level: int) -> list[list[Section]]:
    chunks: list[list[Section]] = []
    cur: list[Section] = []
    for s in sections:
        if s.level == 0 or s.level <= level:
            if cur:
                chunks.append(cur)
            cur = [s]
        else:
            cur.append(s)
    if cur:
        chunks.append(cur)
    return [c for c in chunks if render_all(c).strip()]


def _split_table(block: str, max_chars: int) -> list[str]:
    lines = block.split("\n")
    if len(lines) < 4:
        return _split_lines(block, max_chars)
    header, rows = lines[:2], lines[2:]
    head_txt = "\n".join(header)
    parts, cur = [], []
    size = len(head_txt)
    for r in rows:
        if cur and size + len(r) + 1 > max_chars:
            parts.append(head_txt + "\n" + "\n".join(cur))
            cur, size = [], len(head_txt)
        cur.append(r)
        size += len(r) + 1
    if cur:
        parts.append(head_txt + "\n" + "\n".join(cur))
    return parts


def _split_lines(block: str, max_chars: int) -> list[str]:
    parts, cur, size = [], [], 0
    for ln in block.split("\n"):
        if cur and size + len(ln) + 1 > max_chars:
            parts.append("\n".join(cur))
            cur, size = [], 0
        cur.append(ln)
        size += len(ln) + 1
    if cur:
        parts.append("\n".join(cur))
    return parts


def split_blocks(text: str, max_chars: int) -> list[str]:
    blocks: list[str] = []
    cur: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if FENCE_RE.match(line):
            in_fence = not in_fence
        if not line.strip() and not in_fence:
            if cur:
                blocks.append("\n".join(cur))
                cur = []
        else:
            cur.append(line)
    if cur:
        blocks.append("\n".join(cur))

    expanded: list[str] = []
    for b in blocks:
        if len(b) <= max_chars:
            expanded.append(b)
        elif b.lstrip().startswith("|"):
            expanded.extend(_split_table(b, max_chars))
        else:
            expanded.extend(_split_lines(b, max_chars))

    parts: list[str] = []
    cur_txt = ""
    for b in expanded:
        if cur_txt and len(cur_txt) + 2 + len(b) > max_chars:
            parts.append(cur_txt)
            cur_txt = b
        else:
            cur_txt = f"{cur_txt}\n\n{b}" if cur_txt else b
    if cur_txt:
        parts.append(cur_txt)
    return parts


def split_oversize(sections: list[Section], max_chars: int) -> list[Piece]:
    text = render_all(sections)
    first = sections[0]
    if len(text) <= max_chars:
        return [Piece(first.title, first.path, text)]

    base = first.level
    deeper = sorted({s.level for s in sections[1:] if s.level > base})
    for sub in deeper:                       # thử heading con nông nhất trước
        pieces: list[list[Section]] = []
        cur = [first]
        for s in sections[1:]:
            if s.level <= sub:
                pieces.append(cur)
                cur = [s]
            else:
                cur.append(s)
        pieces.append(cur)
        if len(pieces) > 1:
            out: list[Piece] = []
            for p in pieces:
                out.extend(split_oversize(p, max_chars))
            return out

    parts = split_blocks(text, max_chars)    # không còn heading con -> tách theo khối
    n = len(parts)
    if n == 1:
        return [Piece(first.title, first.path, text)]
    return [Piece(f"{first.title} (phần {i}/{n})", first.path, p)
            for i, p in enumerate(parts, 1)]


# --------------------------------------------------------------------------
# Xử lý một tài liệu
# --------------------------------------------------------------------------
def doc_key(path: Path, used: set[str]) -> str:
    first = path.stem.split("_")[0]
    key = first if (first.isalpha() and first.isupper() and len(first) <= 6) else slugify(path.stem, 30)
    if key in used:
        key = slugify(path.stem, 40)
    used.add(key)
    return key


def process_doc(path: Path, key: str, args) -> dict:
    raw = path.read_text(encoding="utf-8-sig")
    sections = parse_sections(raw, args.keep_images, args.keep_escapes)
    level = auto_level(sections) if args.level == "auto" else int(args.level)
    pieces: list[Piece] = []
    for chunk in build_chunks(sections, level):
        pieces.extend(split_oversize(chunk, args.max_chars))

    width = 3 if len(pieces) > 99 else 2
    entries = []
    for i, p in enumerate(pieces):
        fname = f"{i:0{width}d}_{slugify(p.title)}.md"
        ids = list(dict.fromkeys(ID_ROW_RE.findall(p.text)))
        entries.append({
            "file": fname,
            "title": p.title,
            "path": " > ".join(p.path) if p.path else p.title,
            "chars": len(p.text),
            "ids": ids,
            "_text": p.text,
        })
    return {
        "key": key,
        "source": path.name,
        "split_level": level,
        "raw_chars": len(raw),
        "clean_chars": sum(e["chars"] for e in entries),
        "chunks": entries,
    }


def write_doc(doc: dict, out_root: Path) -> None:
    d = out_root / doc["key"]
    if d.exists():
        if any(d.iterdir()) and not (d / "_INDEX.md").exists():
            raise SystemExit(f"Từ chối xóa thư mục không phải do split_doc tạo: {d}")
        shutil.rmtree(d)
    d.mkdir(parents=True)
    chunks = doc["chunks"]
    for i, e in enumerate(chunks):
        prev_f = chunks[i - 1]["file"] if i > 0 else "-"
        next_f = chunks[i + 1]["file"] if i + 1 < len(chunks) else "-"
        header = (f"<!-- nguồn: {doc['source']} | mục: {e['path']} | "
                  f"{e['chars']} ký tự | trước: {prev_f} | sau: {next_f} -->\n\n")
        (d / e["file"]).write_text(header + e["_text"] + "\n", encoding="utf-8", newline="\n")

    lines = [
        f"# Mục lục {doc['key']} ({doc['source']})",
        "",
        f"Tách ở heading mức {doc['split_level']}. Gốc {doc['raw_chars']:,} ký tự "
        f"-> sau làm sạch {doc['clean_chars']:,} ký tự (~{est_tokens(doc['clean_chars']):,} token).",
        "",
        "| File | Mục | Ký tự | ID hàng bảng |",
        "|---|---|---|---|",
    ]
    for e in chunks:
        ids = ", ".join(e["ids"][:10]) + (" ..." if len(e["ids"]) > 10 else "")
        lines.append(f"| [{e['file']}]({e['file']}) | {e['path']} | {e['chars']:,} | {ids} |")
    (d / "_INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def natural_key(s: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def write_root_indexes(docs: list[dict], out_root: Path) -> None:
    # INDEX.md
    lines = [
        "# Tài liệu đã tách (tạo bởi split_doc.py)",
        "",
        "Đọc `ID_INDEX.md` để tìm ID (FR-xx, DEC-xx, C-xx, ...), hoặc `<DOC>/_INDEX.md` để xem mục lục.",
        "Chỉ mở file con cần thiết; không đọc nguyên tài liệu gốc.",
        "",
        "| Tài liệu | Nguồn | Số file | Ký tự | ~Token |",
        "|---|---|---|---|---|",
    ]
    for d in docs:
        lines.append(f"| [{d['key']}]({d['key']}/_INDEX.md) | {d['source']} | {len(d['chunks'])} | "
                     f"{d['clean_chars']:,} | {est_tokens(d['clean_chars']):,} |")
    (out_root / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    # ID_INDEX.md
    idmap: dict[str, list[str]] = {}
    for d in docs:
        for e in d["chunks"]:
            for i in e["ids"]:
                idmap.setdefault(i, []).append(f"{d['key']}/{e['file']}")
    lines = [
        "# Chỉ mục ID",
        "",
        "ID xuất hiện ở đầu hàng bảng (thường là nơi định nghĩa; một số ID còn xuất hiện ở bảng truy vết).",
        "",
        "| ID | File con |",
        "|---|---|",
    ]
    for i in sorted(idmap, key=natural_key):
        links = "; ".join(f"[{p}]({p})" for p in idmap[i])
        lines.append(f"| {i} | {links} |")
    (out_root / "ID_INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    manifest = {
        "docs": {
            d["key"]: {
                "source": d["source"],
                "split_level": d["split_level"],
                "raw_chars": d["raw_chars"],
                "clean_chars": d["clean_chars"],
                "chunks": [{k: v for k, v in e.items() if k != "_text"} for e in d["chunks"]],
            } for d in docs
        }
    }
    (out_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------
# --find
# --------------------------------------------------------------------------
def find_id(id_: str, out_root: Path) -> int:
    mf = out_root / "manifest.json"
    if not mf.exists():
        print(f"Không thấy {mf}. Chạy split_doc.py trước.", file=sys.stderr)
        return 2
    data = json.loads(mf.read_text(encoding="utf-8"))
    hits, mentions = [], []
    pat = re.compile(rf"(?<![A-Za-z0-9-]){re.escape(id_)}(?![A-Za-z0-9])")
    for key, d in data["docs"].items():
        for c in d["chunks"]:
            if id_ in c["ids"]:
                hits.append(f"{key}/{c['file']}  —  {c['path']}")
            else:
                f = out_root / key / c["file"]
                if f.exists() and pat.search(f.read_text(encoding="utf-8")):
                    mentions.append(f"{key}/{c['file']}  —  {c['path']}")
    if hits:
        print(f"[{id_}] định nghĩa (đầu hàng bảng):")
        print("\n".join("  " + h for h in hits))
    if mentions:
        print(f"[{id_}] chỉ được nhắc đến:")
        print("\n".join("  " + m for m in mentions[:15]))
        if len(mentions) > 15:
            print(f"  ... và {len(mentions) - 15} file khác")
    if not hits and not mentions:
        print(f"Không tìm thấy {id_}")
        return 1
    return 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def collect_inputs(paths: list[str], exclude: set[str]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            files.extend(sorted(x for x in pp.glob("*.md") if x.name not in exclude))
        elif pp.is_file():
            files.append(pp)
        else:
            raise SystemExit(f"Không tìm thấy: {p}")
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Tách tài liệu Markdown lớn thành các file con để AI đọc đỡ tốn token.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("paths", nargs="*", default=[str(DEFAULT_DOCS)],
                    help=f"File .md hoặc thư mục chứa .md (mặc định: {DEFAULT_DOCS})")
    ap.add_argument("-o", "--out", default=str(DEFAULT_OUT), help=f"Thư mục kết quả (mặc định: {DEFAULT_OUT})")
    ap.add_argument("--level", default="auto",
                    help="Mức heading để tách (1-6) hoặc 'auto' (mặc định)")
    ap.add_argument("--max-chars", type=int, default=12000,
                    help="Kích thước tối đa mỗi file con (ký tự, mặc định 12000 ~ 4000 token)")
    ap.add_argument("--keep-images", action="store_true", help="Giữ ảnh base64 (mặc định: bỏ)")
    ap.add_argument("--keep-escapes", action="store_true", help="Giữ ký tự escape \\ của Google Docs")
    ap.add_argument("--exclude", action="append", default=[],
                    help="Tên file bỏ qua khi quét thư mục (có thể lặp lại)")
    ap.add_argument("--dry-run", action="store_true", help="Chỉ in kế hoạch tách, không ghi file")
    ap.add_argument("--find", metavar="ID", help="Tìm ID (vd FR-12, DEC-27) trong thư mục -o đã tách")
    args = ap.parse_args(argv)

    out_root = Path(args.out)
    if args.find:
        return find_id(args.find, out_root)
    if args.level != "auto" and not (args.level.isdigit() and 1 <= int(args.level) <= 6):
        ap.error("--level phải là 1-6 hoặc 'auto'")
    if args.max_chars < 1000:
        ap.error("--max-chars tối thiểu 1000")

    exclude = GENERATED_NAMES | set(args.exclude)
    files = collect_inputs(args.paths, exclude)
    if not files:
        print("Không có file .md để tách.", file=sys.stderr)
        return 1

    used: set[str] = set()
    docs = [process_doc(f, doc_key(f, used), args) for f in files]

    tot_raw = tot_clean = 0
    for d in docs:
        tot_raw += d["raw_chars"]
        tot_clean += d["clean_chars"]
        biggest = max(e["chars"] for e in d["chunks"])
        print(f"{d['key']:<8} {d['source']}")
        print(f"         level={d['split_level']}  files={len(d['chunks'])}  "
              f"gốc={d['raw_chars']:,}  sạch={d['clean_chars']:,} ký tự "
              f"(~{est_tokens(d['clean_chars']):,} token)  file lớn nhất={biggest:,}")
        if args.dry_run:
            for e in d["chunks"]:
                print(f"           {e['file']:<58} {e['chars']:>7,}  {', '.join(e['ids'][:6])}")
    print(f"TỔNG     gốc={tot_raw:,} -> sạch={tot_clean:,} ký tự "
          f"(~{est_tokens(tot_clean):,} token; ước lượng ký tự/3)")

    if args.dry_run:
        return 0
    out_root.mkdir(parents=True, exist_ok=True)
    for d in docs:
        write_doc(d, out_root)
    write_root_indexes(docs, out_root)
    print(f"Đã ghi vào {out_root}/  (bắt đầu từ {out_root}/INDEX.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
