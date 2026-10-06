"""Recheck that curated resource links still work, and record the result.

Humans decide what belongs in catalog/resources.yaml and confirm cost, level and
skill fit. This script only checks URL health. Results go into the url_checks
table, which survives re-seeding, and the resource_catalog view combines them
with the curator checks to decide what counts as "verified".

Usage:
    python -m scraper.recheck                    # check every resource
    python -m scraper.recheck --path web_dev     # one path
    python -m scraper.recheck --pending-only     # only links never checked
    python -m scraper.recheck --retry-failed     # only links that failed last time
    python -m scraper.recheck --limit 3 --dry-run
"""

from __future__ import annotations

import argparse
import sqlite3
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from database.init_db import DEFAULT_DB, initialize_database

USER_AGENT = 'PathForgeLinkCheck/2.0 (+https://github.com/saabz131395-code)'
DELAY_SECONDS = 0.5  # be polite to the sites we check


BLOCKED_CODES = (401, 403, 429)  # site refuses automated requests; says nothing about the page


def check_url(url: str, timeout: int = 12) -> tuple[str, str]:
    """Return (status, detail) where status is PASS, FAIL, BLOCKED or ERROR.

    ERROR means we could not reach the site at all (no internet, DNS failure,
    timeout). That says nothing about the link, so ERROR results are never saved.

    Tries a cheap HEAD request first. Many sites answer HEAD wrongly (Kaggle and
    PortSwigger return 404 for pages that exist), so ANY HEAD failure is retried
    with a normal GET, and only the GET result counts.
    """
    headers = {'User-Agent': USER_AGENT, 'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8'}
    detail = 'No response'
    for method in ('HEAD', 'GET'):
        request = urllib.request.Request(url, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                code = response.status
                if 200 <= code < 400:
                    return 'PASS', f'HTTP {code}'
                detail = f'HTTP {code}'
        except urllib.error.HTTPError as exc:
            detail = f'HTTP {exc.code}'
            if method == 'GET' and exc.code in BLOCKED_CODES:
                return 'BLOCKED', f'{detail} — site blocks automated checks; confirm by hand'
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            detail = str(getattr(exc, 'reason', exc))
            if method == 'GET':
                return 'ERROR', f'{detail} — could not reach the site; check your internet and try again'
    return 'FAIL', detail


def run(db_path: str | Path = DEFAULT_DB, path_key: str | None = None, limit: int | None = None,
        dry_run: bool = False, pending_only: bool = False, retry_failed: bool = False,
        checker=check_url,
        delay: float = DELAY_SECONDS) -> int:
    """Check links and store results. Returns the number of FAILED links (blocked ones don't count)."""
    db_path = Path(db_path)
    if not db_path.exists():
        initialize_database(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    sql = '''SELECT r.slug, r.name, r.url, p.path_name, r.url_check
             FROM resource_catalog r JOIN paths p ON p.id = r.path_id WHERE 1 = 1'''
    args: list[object] = []
    if path_key:
        sql += ' AND p.path_key = ?'
        args.append(path_key)
    if pending_only and retry_failed:
        sql += " AND r.url_check IN ('PENDING', 'FAIL')"
    elif pending_only:
        sql += " AND r.url_check = 'PENDING'"
    elif retry_failed:
        sql += " AND r.url_check = 'FAIL'"
    sql += ' ORDER BY p.display_order, r.id'
    if limit:
        sql += ' LIMIT ?'
        args.append(limit)

    rows = conn.execute(sql, args).fetchall()
    if not rows:
        print('No matching resources.')
    today = date.today().isoformat()
    counts = {'PASS': 0, 'FAIL': 0, 'BLOCKED': 0, 'ERROR': 0}

    for index, row in enumerate(rows):
        if index and delay:
            time.sleep(delay)
        status, detail = checker(row['url'])
        if isinstance(status, bool):  # allow simple True/False checkers
            status = 'PASS' if status else 'FAIL'
        counts[status] += 1
        print(f'[{status}] {row["path_name"]} — {row["name"]} ({detail})')
        if not dry_run and status != 'ERROR':
            conn.execute(
                '''INSERT INTO url_checks (resource_slug, status, detail, checked_on)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT (resource_slug)
                   DO UPDATE SET status = excluded.status, detail = excluded.detail,
                                 checked_on = excluded.checked_on''',
                (row['slug'], status, detail, today),
            )

    if not dry_run:
        conn.commit()
    conn.close()
    print(f"\nChecked {len(rows)} link(s): {counts['PASS']} OK, {counts['FAIL']} failed, "
          f"{counts['BLOCKED']} blocked (check those by hand)"
          + (f", {counts['ERROR']} not reached (not saved, run again later)" if counts['ERROR'] else '') + '.'
          + (' (dry run — nothing saved)' if dry_run else ''))
    return counts['FAIL']


def main() -> None:
    parser = argparse.ArgumentParser(description='Recheck PathForge resource links.')
    parser.add_argument('--path', dest='path_key', help='Only one path, e.g. web_dev')
    parser.add_argument('--limit', type=int, help='Only the first N matching resources')
    parser.add_argument('--pending-only', action='store_true', help='Only links never checked before')
    parser.add_argument('--retry-failed', action='store_true', help='Only links whose last check failed')
    parser.add_argument('--dry-run', action='store_true', help='Check links without saving results')
    parser.add_argument('--db', default=str(DEFAULT_DB), help='Database file (default: %(default)s)')
    args = parser.parse_args()
    failures = run(args.db, args.path_key, args.limit, args.dry_run, args.pending_only, args.retry_failed)
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
