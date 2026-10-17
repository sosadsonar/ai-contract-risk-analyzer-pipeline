"""Offline regressions for upload resource budgets (no legal contract fixtures)."""
import os
import asyncio
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('DATABASE_URL', 'sqlite://')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pymupdf as fitz
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.contract import Contract
from app.services.document_service import extract_pdf_text
from app.services import document_service
from app.repositories.contract_repository import create_contract
from app.core.upload_limits import UploadLimitsMiddleware, UploadCapacityError
from app.api.routes.contracts import upload_contract
from starlette.datastructures import UploadFile


def pdf_bytes(pages=1, text='Employment agreement'):
    with fitz.open() as document:
        for _ in range(pages):
            page = document.new_page()
            if text:
                page.insert_text((72, 72), text)
        return document.tobytes()


class UploadLimitsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', poolclass=StaticPool,
                                    connect_args={'check_same_thread': False})
        Base.metadata.create_all(self.engine)
        def database():
            with Session(self.engine) as db:
                yield db
        app.dependency_overrides[get_db] = database
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()
        self.engine.dispose()

    def count(self):
        with Session(self.engine) as db:
            return db.scalar(select(func.count()).select_from(Contract))

    def test_regular_pdf_keeps_success_payload_and_full_text(self):
        response = self.client.post('/api/v1/contracts/upload', files={'file':('contract.PDF',pdf_bytes(),'application/pdf')})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(set(response.json()), {'id','filename','status','text_length'})
        self.assertEqual(response.json()['status'], 'uploaded')
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(Contract.original_text)), 'Employment agreement\n')
        self.assertEqual(response.json()['text_length'], 21)

    def test_file_over_byte_budget_never_creates_record(self):
        with patch.dict(settings.__dict__, pdf_max_bytes=64):
            response = self.client.post('/api/v1/contracts/upload', files={'file':('large.pdf',pdf_bytes(),'application/pdf')})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.count(), 0)

    def test_page_budget_rejects_small_many_page_pdf(self):
        with patch.dict(settings.__dict__, pdf_max_pages=1):
            with self.assertRaises(ValueError):
                extract_pdf_text(pdf_bytes(pages=2))

    def test_text_budget_rejects_instead_of_truncating(self):
        with patch.dict(settings.__dict__, pdf_max_text_chars=5):
            with self.assertRaises(ValueError):
                extract_pdf_text(pdf_bytes())

    def test_repeated_uploads_stop_at_storage_quota(self):
        with patch.dict(settings.__dict__, pdf_max_stored_contracts=1):
            first = self.client.post('/api/v1/contracts/upload', files={'file':('first.pdf',pdf_bytes(),'application/pdf')})
            second = self.client.post('/api/v1/contracts/upload', files={'file':('second.pdf',pdf_bytes(),'application/pdf')})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 503)
        self.assertEqual(self.count(), 1)

    def test_non_pdf_and_empty_text_remain_rejected(self):
        self.assertEqual(self.client.post('/api/v1/contracts/upload', files={'file':('file.txt',b'plain')}).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/contracts/upload', files={'file':('empty.pdf',pdf_bytes(text=''))}).status_code, 422)
        self.assertEqual(self.count(), 0)

    def test_aggregate_text_quota_counts_existing_records(self):
        with patch.dict(settings.__dict__, pdf_max_stored_text_chars=25):
            a = self.client.post('/api/v1/contracts/upload', files={'file':('a.pdf',pdf_bytes())})
            b = self.client.post('/api/v1/contracts/upload', files={'file':('b.pdf',pdf_bytes())})
        self.assertEqual(a.status_code, 200)
        self.assertEqual(b.status_code, 503)
        self.assertEqual(self.count(), 1)

    def test_nul_text_cannot_bypass_database_length_quota(self):
        with Session(self.engine) as db:
            with self.assertRaises(ValueError):
                create_contract(db, 'bad.pdf', 'A\0' + 'B' * 10)
        self.assertEqual(self.count(), 0)

    def test_malformed_pdf_has_controlled_error_and_no_record(self):
        response = self.client.post('/api/v1/contracts/upload', files={'file':('bad.pdf',b'not PDF')})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.count(), 0)

    def test_real_slow_child_is_killed_and_parser_slot_reusable(self):
        processes = []
        real_popen = subprocess.Popen
        def spawn(*args, **kwargs):
            child_process = real_popen(*args, **kwargs)
            processes.append(child_process)
            return child_process
        with tempfile.TemporaryDirectory() as directory:
            child = Path(directory) / 'slow.py'
            child.write_text('import os,sys,time\nprint(os.getpid(),flush=True)\ntime.sleep(10)\n',encoding='utf-8')
            with patch.object(document_service, '_WORKER_PATH', child), patch.dict(settings.__dict__, pdf_parse_timeout_seconds=0.3), patch.object(subprocess, 'Popen', side_effect=spawn):
                started = time.monotonic()
                with self.assertRaisesRegex(ValueError, 'timed out'):
                    extract_pdf_text(pdf_bytes())
                self.assertLess(time.monotonic() - started, 3)
                self.assertIsNotNone(processes[0].poll())
        self.assertEqual(extract_pdf_text(pdf_bytes()), 'Employment agreement\n')

    def test_os_memory_limit_denies_allocation_in_disposable_child(self):
        code = '''import sys
sys.path.insert(0, sys.argv[1])
from app.services.pdf_worker import limit_memory
handle = limit_memory(128)
try:
    data = bytearray(256 * 1024 * 1024)
except MemoryError:
    print('allocation denied')
else:
    raise SystemExit('memory limit not enforced')
'''
        result = subprocess.run([sys.executable,'-c',code,str(Path(__file__).resolve().parents[1])],capture_output=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        self.assertEqual(result.stdout.strip(),b'allocation denied')


class AdmissionTests(unittest.IsolatedAsyncioTestCase):
    async def call(self, middleware, chunks, *, path='/api/v1/contracts/upload', root_path='', receive=None):
        queue = iter(chunks)
        output = []
        async def next_chunk():
            return {'type':'http.request','body':next(queue),'more_body':True}
        async def send(message):
            output.append(message)
        await middleware({'type':'http','method':'POST','path':path,'root_path':root_path,'headers':[]}, receive or next_chunk, send)
        return output

    async def test_stream_without_length_and_with_root_path_is_bounded(self):
        async def downstream(scope, receive, send):
            try:
                await receive()
                await receive()
            except Exception as error:
                from starlette.exceptions import HTTPException
                self.assertIsInstance(error, HTTPException)
                self.assertEqual(error.status_code, 413)
                return
            self.fail('Unbounded body reached downstream')
        middleware = UploadLimitsMiddleware(downstream)
        with patch.dict(settings.__dict__, pdf_max_bytes=1):
            await self.call(middleware, [b'a'*32000,b'b'*34000],path='/prefix/api/v1/contracts/upload',root_path='/prefix')
        self.assertEqual(middleware.active, 0)

    async def test_slow_body_deadline_and_capacity_release(self):
        async def downstream(scope, receive, send):
            from starlette.exceptions import HTTPException
            with self.assertRaises(HTTPException) as caught:
                await receive()
            self.assertEqual(caught.exception.status_code,408)
        async def slow_receive():
            await asyncio.sleep(1)
        middleware = UploadLimitsMiddleware(downstream)
        with patch.dict(settings.__dict__, pdf_body_timeout_seconds=0.02):
            await self.call(middleware, [], receive=slow_receive)
        self.assertEqual(middleware.active,0)

    async def test_rate_and_concurrency_admission_reject_before_body_read(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def downstream(scope, receive, send):
            entered.set()
            await release.wait()
        async def unread():
            self.fail('Rejected request body was read')
        middleware = UploadLimitsMiddleware(downstream)
        with patch.dict(settings.__dict__,pdf_max_concurrent_uploads=1,pdf_uploads_per_minute=1):
            first = asyncio.create_task(self.call(middleware, []))
            await entered.wait()
            denied = await self.call(middleware, [], receive=unread)
            self.assertEqual(denied[0]['status'],429)
            release.set()
            await first
        other = UploadLimitsMiddleware(downstream)
        other.active = 1
        with patch.dict(settings.__dict__,pdf_max_concurrent_uploads=1):
            denied = await self.call(other, [], receive=unread)
        self.assertEqual(denied[0]['status'],503)

    async def test_cancelled_route_waits_for_underlying_work_before_returning(self):
        import io
        started, completed, release = threading.Event(), threading.Event(), threading.Event()
        class Result:
            id=1; filename='a.pdf'; status='uploaded'
        def controlled_processing(**kwargs):
            started.set()
            release.wait(3)
            completed.set()
            return Result(), 1
        file = UploadFile(io.BytesIO(b'PDF'),filename='a.pdf')
        with patch('app.api.routes.contracts.process_uploaded_contract', controlled_processing):
            task = asyncio.create_task(upload_contract(file,object()))
            while not started.is_set():
                await asyncio.sleep(0.01)
            task.cancel()
            await asyncio.sleep(0.05)
            self.assertFalse(task.done())
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(completed.is_set())

    async def test_real_multipart_overflow_closes_partially_spooled_file(self):
        boundary = b'audit-boundary'
        prefix = b'--'+boundary+b'\r\nContent-Disposition: form-data; name="file"; filename="a.pdf"\r\nContent-Type: application/pdf\r\n\r\n'
        chunks = iter([prefix + b'a'*(1024*1024+100), b'b'*70000])
        messages, files = [], []
        real_spool = tempfile.SpooledTemporaryFile
        def spool(*args, **kwargs):
            file = real_spool(*args, **kwargs)
            files.append(file)
            return file
        async def receive():
            return {'type':'http.request','body':next(chunks),'more_body':True}
        async def send(message):
            messages.append(message)
        scope = {'type':'http','method':'POST','path':'/api/v1/contracts/upload','root_path':'',
                 'headers':[(b'content-type',b'multipart/form-data; boundary='+boundary)],
                 'query_string':b'','http_version':'1.1','scheme':'http','server':('test',80),'client':('test',1)}
        # Actual installed multipart parser, real disk spool, no Content-Length.
        with patch.dict(settings.__dict__,pdf_max_bytes=1024*1024), patch('starlette.formparsers.SpooledTemporaryFile',side_effect=spool):
            await app(scope,receive,send)
        self.assertEqual(messages[0]['status'],413)
        self.assertEqual(len(files),1)
        self.assertTrue(files[0].closed)


if __name__ == '__main__':
    unittest.main()
