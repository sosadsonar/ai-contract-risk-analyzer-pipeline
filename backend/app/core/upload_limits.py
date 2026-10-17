"""Admission and actual byte counting before FastAPI parses multipart data."""
import asyncio
import threading
import time
from collections import deque

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette._utils import get_route_path
from app.core.config import settings


class UploadLimitsMiddleware:
    def __init__(self, app):
        self.app = app
        self.lock = threading.Lock()
        self.active = 0
        self.attempts = deque()

    async def __call__(self, scope, receive, send):
        if (scope['type'] != 'http' or scope['method'] != 'POST'
                or get_route_path(scope).rstrip('/') != '/api/v1/contracts/upload'):
            return await self.app(scope, receive, send)
        limit = settings.pdf_max_bytes + 64 * 1024
        now = time.monotonic()
        rejection = None
        with self.lock:
            while self.attempts and self.attempts[0] <= now - 60:
                self.attempts.popleft()
            if len(self.attempts) >= settings.pdf_uploads_per_minute:
                rejection = (429, 'Upload rate limit reached')
            elif self.active >= settings.pdf_max_concurrent_uploads:
                rejection = (503, 'Upload capacity is busy')
            else:
                self.attempts.append(now)
                self.active += 1
        if rejection:
            return await JSONResponse({'detail': rejection[1]}, rejection[0],
                                      headers={'Retry-After': '60'})(scope, receive, send)
        try:
            lengths = [v for k,v in scope['headers'] if k.lower() == b'content-length']
            if any(not v.isdigit() for v in lengths):
                return await JSONResponse({'detail':'Invalid Content-Length'}, 400)(scope, receive, send)
            if any(int(v) > limit for v in lengths):
                return await JSONResponse({'detail':'Upload request is too large'}, 413)(scope, receive, send)
            received = 0
            deadline = now + settings.pdf_body_timeout_seconds
            async def bounded_receive():
                nonlocal received
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise HTTPException(408, 'Upload body timed out')
                try:
                    message = await asyncio.wait_for(receive(), remaining)
                except asyncio.TimeoutError:
                    raise HTTPException(408, 'Upload body timed out') from None
                if message['type'] == 'http.request':
                    received += len(message.get('body', b''))
                    if received > limit:
                        raise HTTPException(413, 'Upload request is too large')
                return message
            await self.app(scope, bounded_receive, send)
        finally:
            with self.lock:
                self.active -= 1


class UploadCapacityError(RuntimeError):
    pass
