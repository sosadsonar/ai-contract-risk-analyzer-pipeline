"""Typed exception của pipeline (TDD §7.2, AI_CONTEXT §8).

ValidationReject (segmenter, TOO_MANY_CLAUSES) + nhóm lỗi AI (AiTimeout, AiProviderError,
AiOutputInvalid — N1 thêm ở W3 vì `ai/` cần raise chúng). PipelineInternalError và
LegalCorpusConflict (N4) cũng nằm ở file này — đừng tạo file thứ hai.
"""


class ValidationReject(Exception):
    """Lỗi đầu vào/phạm vi → session chuyển REJECTED (cuối, không retry)."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code
        self.message = message


class _CodedError(Exception):
    """Lỗi có mã ổn định (SKELETON §8) — không chứa nội dung hợp đồng/prompt/response."""

    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "") -> None:
        super().__init__(f"{self.code}: {message}" if message else self.code)
        self.message = message


class AiTimeout(_CodedError):
    """Provider hết thời gian sau retry → session FAILED, retry thủ công được."""

    code = "AI_TIMEOUT"


class AiProviderError(_CodedError):
    """Provider lỗi (HTTP 4xx/5xx, mạng, key sai...) → FAILED, retry thủ công được."""

    code = "AI_PROVIDER_ERROR"

    def __init__(self, message: str = "", *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class AiOutputInvalid(_CodedError):
    """Response sai schema/ID/nhãn sau retry ≤1 → FAILED (INV-05)."""

    code = "AI_OUTPUT_INVALID"


class StageCancelled(Exception):
    """Người dùng End/cancel giữa các batch; orchestrator quyết định state, không phải lỗi."""


class PipelineInternalError(_CodedError):
    """Lỗi chạy cục bộ không do người dùng/provider (invariant vỡ, nhãn ngoài taxonomy...) → FAILED."""

    code = "INTERNAL_ERROR"


class LegalCorpusConflict(_CodedError):
    """Kho luật mâu thuẫn (overlap hiệu lực, cạnh lạ, PARENT_OF có chu trình...) → service fail-fast lúc startup."""

    code = "LEGAL_CORPUS_CONFLICT"
