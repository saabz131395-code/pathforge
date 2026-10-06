import io
import sqlite3
import unittest
from contextlib import closing, redirect_stdout
from pathlib import Path

from database import init_db
from database.init_db import CatalogError, load_catalog
from scraper import recheck
from tests.helpers import AppTestCase


class CatalogTests(unittest.TestCase):
    def test_catalog_loads_and_every_path_has_content(self):
        paths, resources, projects = load_catalog()
        for path in paths:
            with self.subTest(path=path['key']):
                self.assertGreaterEqual(sum(r['path'] == path['key'] for r in resources), 3)
                self.assertGreaterEqual(sum(p['path'] == path['key'] for p in projects), 3)

    def test_home_content_is_valid(self):
        from app.services.home import load_home_content
        content = load_home_content()
        self.assertGreaterEqual(len(content['tips']), 3)
        self.assertGreaterEqual(len(content['tools']), 4)
        self.assertGreaterEqual(len(content['freelance_steps']), 3)

    def test_all_resource_urls_use_https(self):
        _, resources, _ = load_catalog()
        for resource in resources:
            self.assertTrue(resource['url'].startswith('https://'), resource['id'])

    def test_bad_catalog_gives_a_readable_error(self):
        original = init_db.CATALOG_DIR
        broken = Path(self.id().replace('.', '_'))
        try:
            broken.mkdir(exist_ok=True)
            for name in ('paths.yaml', 'resources.yaml', 'projects.yaml'):
                (broken / name).write_text((original / name).read_text(encoding='utf-8'), encoding='utf-8')
            text = (broken / 'resources.yaml').read_text(encoding='utf-8')
            (broken / 'resources.yaml').write_text(text.replace('path: web_dev', 'path: web_devv', 1), encoding='utf-8')
            init_db.CATALOG_DIR = broken
            with self.assertRaisesRegex(CatalogError, 'unknown path "web_devv"'):
                load_catalog()
        finally:
            init_db.CATALOG_DIR = original
            for child in broken.glob('*'):
                child.unlink()
            broken.rmdir()


class RecheckTests(AppTestCase):
    def _status(self, slug):
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            row = conn.execute('SELECT url_check FROM resource_catalog WHERE slug = ?', (slug,)).fetchone()
        return row[0]

    def test_recheck_records_pass_and_fail(self):
        def fake_checker(url):
            return ('mozilla' in url, 'HTTP 200' if 'mozilla' in url else 'HTTP 404')

        with redirect_stdout(io.StringIO()):
            failures = recheck.run(self.db_path, path_key='web_dev', checker=fake_checker, delay=0)
        self.assertEqual(self._status('mdn-learn-web-development'), 'PASS')
        self.assertEqual(self._status('freecodecamp-responsive-web-design'), 'FAIL')
        self.assertEqual(failures, 4)  # 6 web_dev resources, 2 on mozilla.org

    def test_blocked_sites_stay_visible_but_unverified(self):
        with redirect_stdout(io.StringIO()):
            failures = recheck.run(self.db_path, path_key='web_dev', delay=0,
                                   checker=lambda url: ('BLOCKED', 'HTTP 403'))
        self.assertEqual(failures, 0)
        self.assertEqual(self._status('mdn-learn-web-development'), 'BLOCKED')
        pid = self.path_id('web_dev')
        page = self.client.get(f'/path/{pid}/resources').get_data(as_text=True)
        self.assertIn('MDN — Learn Web Development', page)
        self.assertIn('blocks automated link checks', page)
        self.assertNotIn('✓ VERIFIED', page)

    def test_head_404_is_retried_with_get(self):
        from unittest import mock
        calls = []

        class FakeResponse:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False

        def fake_urlopen(request, timeout):
            calls.append(request.get_method())
            if request.get_method() == 'HEAD':
                raise recheck.urllib.error.HTTPError(request.full_url, 404, 'Not Found', {}, None)
            return FakeResponse()

        with mock.patch.object(recheck.urllib.request, 'urlopen', fake_urlopen):
            self.assertEqual(recheck.check_url('https://www.kaggle.com/learn/python'), ('PASS', 'HTTP 200'))
        self.assertEqual(calls, ['HEAD', 'GET'])

    def test_old_database_is_upgraded_and_keeps_history(self):
        from database.init_db import initialize_database
        self.mark_url('mdn-learn-web-development', 'PASS')
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.executescript('''
                DROP VIEW resource_catalog;
                ALTER TABLE url_checks RENAME TO tmp;
                CREATE TABLE url_checks (resource_slug TEXT PRIMARY KEY,
                    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL')),
                    detail TEXT NOT NULL DEFAULT '', checked_on DATE NOT NULL);
                INSERT INTO url_checks SELECT * FROM tmp; DROP TABLE tmp;''')
        initialize_database(self.db_path)
        self.assertEqual(self._status('mdn-learn-web-development'), 'PASS')
        self.mark_url('sqlzoo', 'BLOCKED')
        self.assertEqual(self._status('sqlzoo'), 'BLOCKED')

    def test_network_errors_are_not_saved(self):
        with redirect_stdout(io.StringIO()):
            failures = recheck.run(self.db_path, path_key='web_dev', delay=0,
                                   checker=lambda url: ('ERROR', 'getaddrinfo failed'))
        self.assertEqual(failures, 0)
        self.assertEqual(self._status('mdn-learn-web-development'), 'PENDING')

    def test_dns_failure_is_reported_as_error_not_fail(self):
        from unittest import mock

        def offline(request, timeout):
            raise recheck.urllib.error.URLError('[Errno 11002] getaddrinfo failed')

        with mock.patch.object(recheck.urllib.request, 'urlopen', offline):
            status, _ = recheck.check_url('https://example.com/')
        self.assertEqual(status, 'ERROR')

    def test_retry_failed_only_rechecks_failed_links(self):
        self.mark_url('mdn-learn-web-development', 'FAIL')
        self.mark_url('mdn-javascript-guide', 'PASS')
        seen = []
        with redirect_stdout(io.StringIO()):
            recheck.run(self.db_path, retry_failed=True, delay=0,
                        checker=lambda url: (seen.append(url) or True, 'HTTP 200'))
        self.assertEqual(seen, ['https://developer.mozilla.org/en-US/docs/Learn_web_development'])
        self.assertEqual(self._status('mdn-learn-web-development'), 'PASS')

    def test_dry_run_saves_nothing(self):
        with redirect_stdout(io.StringIO()):
            recheck.run(self.db_path, limit=2, dry_run=True, checker=lambda url: (True, 'HTTP 200'), delay=0)
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM url_checks').fetchone()[0], 0)

    def test_pending_only_skips_checked_links(self):
        self.mark_url('mdn-learn-web-development', 'PASS')
        seen = []
        with redirect_stdout(io.StringIO()):
            recheck.run(self.db_path, path_key='web_dev', pending_only=True,
                        checker=lambda url: (seen.append(url) or True, 'HTTP 200'), delay=0)
        self.assertNotIn('https://developer.mozilla.org/en-US/docs/Learn_web_development', seen)
        self.assertEqual(len(seen), 5)


if __name__ == '__main__':
    unittest.main()
