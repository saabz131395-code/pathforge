"""Shared test setup: every test class gets its own throwaway database."""

import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app import create_app
from database.init_db import initialize_database


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='pathforge-test-'))
        self.db_path = self.tmp / 'test.db'
        initialize_database(self.db_path)
        self.app = create_app({'TESTING': True, 'DATABASE': str(self.db_path)})
        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path_id(self, key):
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            return conn.execute('SELECT id FROM paths WHERE path_key = ?', (key,)).fetchone()[0]

    def mark_url(self, slug, status):
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO url_checks (resource_slug, status, detail, checked_on)"
                " VALUES (?, ?, 'test', '2026-10-01')",
                (slug, status),
            )
