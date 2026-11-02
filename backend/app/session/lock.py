"""Non-blocking single-session processing lease."""
from threading import Lock
from uuid import UUID, uuid4


class ProcessingLease:
    def __init__(self):
        self._lock = Lock()
        self._owner: UUID | None = None

    def try_acquire(self, owner: UUID | None = None) -> UUID | None:
        with self._lock:
            if self._owner is not None:
                return None
            self._owner = owner or uuid4()
            return self._owner

    def assign_owner(self, owner: UUID) -> None:
        with self._lock:
            if self._owner is None:
                raise RuntimeError("Lease not held")
            self._owner = owner

    def release(self, owner: UUID) -> bool:
        with self._lock:
            if self._owner != owner:
                return False
            self._owner = None
            return True

    def holder(self) -> UUID | None:
        with self._lock:
            return self._owner
