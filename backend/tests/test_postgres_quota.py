"""Set TEST_POSTGRES_URL to a disposable local PostgreSQL instance to run."""
import os
import sys
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('DATABASE_URL','sqlite://')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, text, select, func
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import Base
from app.core.upload_limits import UploadCapacityError
from app.models.contract import Contract
from app.repositories.contract_repository import create_contract


@unittest.skipUnless(os.environ.get('TEST_POSTGRES_URL'), 'Requires disposable PostgreSQL TEST_POSTGRES_URL')
class PostgresQuotaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = 'upload_test_' + uuid.uuid4().hex
        cls.admin = create_engine(os.environ['TEST_POSTGRES_URL'])
        with cls.admin.begin() as db:
            db.execute(text('CREATE SCHEMA '+cls.schema))
        cls.engine = create_engine(os.environ['TEST_POSTGRES_URL'],
                                  connect_args={'options':'-csearch_path='+cls.schema})
        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
        with cls.admin.begin() as db:
            db.execute(text('DROP SCHEMA '+cls.schema+' CASCADE'))
        cls.admin.dispose()

    def setUp(self):
        with self.engine.begin() as db:
            db.execute(text('TRUNCATE contracts'))

    def test_concurrent_insertions_cannot_exceed_global_count_quota(self):
        barrier = threading.Barrier(2)
        def insert():
            with Session(self.engine) as db:
                barrier.wait(timeout=3)
                try:
                    create_contract(db,'a.pdf','ordinary text')
                    return 'accepted'
                except UploadCapacityError:
                    return 'rejected'
        with patch.dict(settings.__dict__,pdf_max_stored_contracts=1):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _:insert(), range(2)))
        self.assertEqual(sorted(results),['accepted','rejected'])
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Contract)),1)

    def test_competing_lock_rejects_without_commit_then_recovers(self):
        with Session(self.engine) as holder:
            holder.execute(text('SELECT pg_advisory_xact_lock(1129464146, 1)'))
            with Session(self.engine) as other:
                with self.assertRaises(UploadCapacityError):
                    create_contract(other,'a.pdf','text')
            holder.rollback()
        with Session(self.engine) as db:
            contract = create_contract(db,'a.pdf','text')
            self.assertEqual(contract.original_text,'text')

    def test_existing_text_counts_against_aggregate_quota(self):
        with patch.dict(settings.__dict__,pdf_max_stored_text_chars=10):
            with Session(self.engine) as db:
                create_contract(db,'first.pdf','123456')
            with Session(self.engine) as db:
                with self.assertRaises(UploadCapacityError):
                    create_contract(db,'second.pdf','12345')
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.sum(func.length(Contract.original_text)))),6)


if __name__ == '__main__':
    unittest.main()
