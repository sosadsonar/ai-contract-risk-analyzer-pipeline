"""Periodic inactivity cleanup and metadata tombstone retention."""
import asyncio
from datetime import datetime, timedelta

from app.session.orchestrator import Orchestrator
from app.session.store import utcnow


class CleanupScheduler:
    def __init__(self, orchestrator: Orchestrator, ttl_minutes: int, tombstone_hours: int):
        self.orchestrator = orchestrator
        self.ttl_minutes = ttl_minutes
        self.tombstone_hours = tombstone_hours

    def run_once(self, now: datetime | None = None) -> None:
        now = now or utcnow()
        store = self.orchestrator.store
        for sid in store.expired(now - timedelta(minutes=self.ttl_minutes)):
            self.orchestrator.end(sid, now)
        if store.metadata:
            store.metadata.prune_tombstones(now - timedelta(hours=self.tombstone_hours))

    async def run(self) -> None:
        while True:
            await asyncio.sleep(60)
            self.run_once()
