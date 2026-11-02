"""Typed exception của pipeline (TDD §7.2, AI_CONTEXT §8).

ValidationReject phục vụ segmentation; LegalCorpusConflict phục vụ C-12 (N2).
Các lỗi provider/orchestrator còn lại do N4 bổ sung vào cùng file này.
"""


class ValidationReject(Exception):
    """Lỗi đầu vào/phạm vi → session chuyển REJECTED (cuối, không retry)."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code
        self.message = message


class LegalCorpusConflict(Exception):
    """Corpus sai cấu trúc, hiệu lực hoặc provenance: chặn build/reload index."""

    code = "LEGAL_CORPUS_CONFLICT"
