"""Typed exception của pipeline (TDD §7.2, AI_CONTEXT §8).

Hiện chỉ có ValidationReject (cần cho `clause.segmenter`, TOO_MANY_CLAUSES). N4 bổ sung các lỗi
còn lại (AiTimeout, AiProviderError, AiOutputInvalid, PipelineInternalError, LegalCorpusConflict)
vào CÙNG file này khi dựng orchestrator — đừng tạo file thứ hai.
"""


class ValidationReject(Exception):
    """Lỗi đầu vào/phạm vi → session chuyển REJECTED (cuối, không retry)."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code
        self.message = message
