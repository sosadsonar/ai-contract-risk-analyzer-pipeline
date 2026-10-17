import json
import subprocess
import sys
import threading
from pathlib import Path
from app.core.config import settings
from app.core.upload_limits import UploadCapacityError

_WORKER_PATH = Path(__file__).with_name('pdf_worker.py')
_parser_slots = threading.BoundedSemaphore(settings.pdf_max_concurrent_uploads)


def extract_pdf_text(file_bytes: bytes) -> str:
    if len(file_bytes) > settings.pdf_max_bytes:
        raise ValueError('PDF exceeds upload byte limit')
    if not _parser_slots.acquire(blocking=False):
        raise UploadCapacityError('PDF parser capacity is busy')
    try:
        result = subprocess.run(
            [sys.executable, str(_WORKER_PATH), str(settings.pdf_max_bytes),
             str(settings.pdf_max_pages), str(settings.pdf_max_text_chars),
             str(settings.pdf_worker_memory_mb)],
            input=file_bytes, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=settings.pdf_parse_timeout_seconds,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
        )
        try:
            payload = json.loads(result.stdout)
        except (ValueError, UnicodeDecodeError):
            raise ValueError('Invalid PDF or PDF resource limit exceeded') from None
        if result.returncode == 2 and 'capacity_error' in payload:
            raise UploadCapacityError('Parser memory limit unavailable')
        if result.returncode or not isinstance(payload.get('text'), str):
            raise ValueError('Invalid PDF or PDF resource limit exceeded')
        if len(payload['text']) > settings.pdf_max_text_chars:
            raise ValueError('PDF exceeds extracted text limit')
        return payload['text']
    except subprocess.TimeoutExpired:
        # subprocess.run kills AND waits for the child before raising.
        raise ValueError('PDF parsing timed out') from None
    finally:
        _parser_slots.release()
