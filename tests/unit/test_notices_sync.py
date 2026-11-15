"""FR-25: disclaimer/data notice backend (final_result, export) trùng chữ với frontend (Upload/Result)."""

import re
from pathlib import Path

from app.result.notices import DATA_NOTICE, DISCLAIMER

TS = (Path(__file__).resolve().parents[2] / "frontend/src/lib/notices.ts").read_text(encoding="utf-8")


def _ts_const(name: str) -> str:
    block = re.search(rf"export const {name} =(.*?);", TS, re.S).group(1)
    return "".join(re.findall(r'"([^"]*)"', block))


def test_notices_match_frontend():
    assert _ts_const("DISCLAIMER") == DISCLAIMER
    assert _ts_const("DATA_NOTICE") == DATA_NOTICE
    assert "an toàn" not in DISCLAIMER + DATA_NOTICE
