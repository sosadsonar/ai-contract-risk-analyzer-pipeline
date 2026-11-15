"""Corpus luật phải là LF để khớp checksum đã ghim (PR #30 note: VS Code đổi sang CRLF)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("name", ["provisions.jsonl", "edges.jsonl", "label_map.yaml", "manifest.yaml"])
def test_legal_corpus_files_have_no_crlf(name):
    data = (ROOT / "data/legal_corpus" / name).read_bytes()
    assert b"\r\n" not in data, (
        f"{name} có CRLF: chạy `git checkout -- data/legal_corpus` để khôi phục LF, không băm lại checksum"
    )
