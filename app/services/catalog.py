"""All SQL lives here. Routes call these functions and never query the database directly."""

from __future__ import annotations

import sqlite3

from ..db import get_db

LEVELS = ('beginner', 'intermediate', 'advanced')
RESOURCE_TYPES = ('course', 'tutorial', 'doc', 'video', 'book', 'tool')


# ---- Paths -----------------------------------------------------------------

def list_active_paths() -> list[sqlite3.Row]:
    return get_db().execute(
        'SELECT * FROM paths WHERE active = 1 ORDER BY display_order'
    ).fetchall()


def get_path(path_id: int) -> sqlite3.Row | None:
    return get_db().execute(
        'SELECT * FROM paths WHERE id = ? AND active = 1', (path_id,)
    ).fetchone()


def get_path_by_key(path_key: str) -> sqlite3.Row | None:
    return get_db().execute(
        'SELECT * FROM paths WHERE path_key = ? AND active = 1', (path_key,)
    ).fetchone()


def get_paths_by_keys(path_keys: list[str]) -> list[sqlite3.Row]:
    """Active paths for the given keys, in the order the keys were given."""
    if not path_keys:
        return []
    placeholders = ','.join('?' for _ in path_keys)
    rows = get_db().execute(
        f'SELECT * FROM paths WHERE active = 1 AND path_key IN ({placeholders})', path_keys
    ).fetchall()
    by_key = {row['path_key']: row for row in rows}
    return [by_key[key] for key in path_keys if key in by_key]


def get_path_stats(path_id: int) -> dict[str, int]:
    row = get_db().execute(
        '''SELECT
               (SELECT COUNT(*) FROM resource_catalog
                 WHERE path_id = :pid AND url_check != 'FAIL')                AS resource_count,
               (SELECT COUNT(*) FROM resource_catalog
                 WHERE path_id = :pid AND verification_status = 'verified')  AS verified_count,
               (SELECT COUNT(*) FROM projects WHERE path_id = :pid)          AS project_count''',
        {'pid': path_id},
    ).fetchone()
    return dict(row)


# ---- Resources -------------------------------------------------------------

def list_resources(path_id: int, level: str | None = None, resource_type: str | None = None,
                   verified_only: bool = False, free_cert_only: bool = False) -> list[sqlite3.Row]:
    # Resources whose URL check FAILED are hidden; never-checked ones show as "review pending".
    where = ['path_id = ?', "url_check != 'FAIL'"]
    args: list[object] = [path_id]
    if level in LEVELS:
        where.append('level = ?')
        args.append(level)
    if resource_type in RESOURCE_TYPES:
        where.append('type = ?')
        args.append(resource_type)
    if verified_only:
        where.append("verification_status = 'verified'")
    if free_cert_only:
        where.append("certificate_cost = 'free'")
    return get_db().execute(
        f'''SELECT * FROM resource_catalog
            WHERE {' AND '.join(where)}
            ORDER BY verification_status = 'verified' DESC, CASE level WHEN 'beginner' THEN 0 WHEN 'intermediate' THEN 1 ELSE 2 END, duration_hours_min, name''',
        args,
    ).fetchall()


# ---- Projects --------------------------------------------------------------

def list_projects(path_id: int, level: str | None = None) -> list[sqlite3.Row]:
    if level in LEVELS:
        return get_db().execute(
            '''SELECT * FROM projects WHERE path_id = ? AND difficulty = ?
               ORDER BY estimated_effort_hours_min, title''',
            (path_id, level),
        ).fetchall()
    return get_db().execute(
        '''SELECT * FROM projects WHERE path_id = ?
           ORDER BY CASE difficulty WHEN 'beginner' THEN 0 WHEN 'intermediate' THEN 1 ELSE 2 END, estimated_effort_hours_min, title''',
        (path_id,),
    ).fetchall()
