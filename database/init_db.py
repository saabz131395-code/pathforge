"""Build the SQLite database from the YAML catalogue in catalog/.

Run with:  python seed.py

Paths, resources, projects and level-check questions are rebuilt from YAML every time, so the YAML files
are the single source of truth. URL-check history (url_checks) is kept.
"""

from __future__ import annotations

import json
import random
import sqlite3
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parents[1]
CATALOG_DIR = BASE_DIR / 'catalog'
SCHEMA_FILE = Path(__file__).resolve().parent / 'schema.sql'
DEFAULT_DB = Path(__file__).resolve().parent / 'pathforge.db'

CHECK_VALUES = {'PASS', 'FAIL', 'PENDING'}
CURATOR_CHECKS = ('learning_cost', 'certificate_cost', 'skill', 'level')


class CatalogError(ValueError):
    """Raised when a YAML catalogue file has a mistake a curator needs to fix."""


def _load(name: str, key: str) -> list[dict]:
    path = CATALOG_DIR / name
    with path.open(encoding='utf-8') as handle:
        data = yaml.safe_load(handle) or {}
    items = data.get(key)
    if not isinstance(items, list) or not items:
        raise CatalogError(f'{name}: expected a non-empty "{key}:" list')
    return items


def _require(item: dict, fields: tuple[str, ...], where: str) -> None:
    missing = [field for field in fields if item.get(field) in (None, '')]
    if missing:
        raise CatalogError(f'{where}: missing {", ".join(missing)}')


def _hours(item: dict, where: str) -> tuple[int, int]:
    hours = item.get('hours')
    if not (isinstance(hours, list) and len(hours) == 2 and all(isinstance(h, int) for h in hours)):
        raise CatalogError(f'{where}: "hours" must look like [min, max]')
    low, high = hours
    if low < 0 or low > high:
        raise CatalogError(f'{where}: hours min must be 0 or more and not larger than max')
    return low, high


def load_catalog() -> tuple[list[dict], list[dict], list[dict]]:
    """Load and validate all three YAML files, with errors a curator can act on."""
    paths = _load('paths.yaml', 'paths')
    resources = _load('resources.yaml', 'resources')
    projects = _load('projects.yaml', 'projects')

    path_keys: set[str] = set()
    for index, path in enumerate(paths, start=1):
        where = f'paths.yaml item {index}'
        _require(path, ('key', 'name', 'icon', 'tagline', 'description', 'beginner_focus',
                        'practice_summary', 'why_recommended'), where)
        if path['key'] in path_keys:
            raise CatalogError(f'{where}: duplicate key "{path["key"]}"')
        path_keys.add(path['key'])

    for filename, items in (('resources.yaml', resources), ('projects.yaml', projects)):
        seen: set[str] = set()
        for item in items:
            where = f'{filename} "{item.get("id", "?")}"'
            _require(item, ('id', 'path'), where)
            if item['id'] in seen:
                raise CatalogError(f'{where}: duplicate id')
            seen.add(item['id'])
            if item['path'] not in path_keys:
                raise CatalogError(f'{where}: unknown path "{item["path"]}"')
            _hours(item, where)

    for item in resources:
        where = f'resources.yaml "{item["id"]}"'
        _require(item, ('name', 'url', 'source', 'type', 'level', 'learning_cost', 'certificate_cost'), where)
        if not str(item['url']).startswith(('https://', 'http://')):
            raise CatalogError(f'{where}: url must start with https://')
        checks = item.get('curator_checks') or {}
        for check in CURATOR_CHECKS:
            if checks.get(check, 'PENDING') not in CHECK_VALUES:
                raise CatalogError(f'{where}: curator_checks.{check} must be PASS, FAIL or PENDING')

    for item in projects:
        _require(item, ('title', 'project_type', 'difficulty', 'description', 'skills_proved',
                        'proof_required', 'cv_line'), f'projects.yaml "{item["id"]}"')

    return paths, resources, projects


TIERS = ('basic', 'intermediate', 'advanced')
QUESTIONS_PER_TIER = 2


def load_assessments(path_keys: set[str]) -> list[dict]:
    """Load level-check questions: exactly 2 per tier for every path."""
    questions = _load('assessments.yaml', 'questions')
    seen: set[str] = set()
    per_path: dict[tuple[str, str], int] = {}
    for q in questions:
        where = f'assessments.yaml "{q.get("id", "?")}"'
        _require(q, ('id', 'path', 'tier', 'topic', 'prompt', 'correct', 'explanation'), where)
        if q['id'] in seen:
            raise CatalogError(f'{where}: duplicate id')
        seen.add(q['id'])
        if q['path'] not in path_keys:
            raise CatalogError(f'{where}: unknown path "{q["path"]}"')
        if q['tier'] not in TIERS:
            raise CatalogError(f'{where}: tier must be one of {", ".join(TIERS)}')
        wrong = q.get('wrong')
        if not (isinstance(wrong, list) and len(wrong) == 3 and all(str(w).strip() for w in wrong)):
            raise CatalogError(f'{where}: "wrong" must list exactly 3 wrong answers')
        if str(q['correct']) in [str(w) for w in wrong]:
            raise CatalogError(f'{where}: the correct answer also appears in "wrong"')
        key = (q['path'], q['tier'])
        per_path[key] = per_path.get(key, 0) + 1
    for path_key in path_keys:
        for tier in TIERS:
            count = per_path.get((path_key, tier), 0)
            if count != QUESTIONS_PER_TIER:
                raise CatalogError(f'assessments.yaml: path "{path_key}" needs {QUESTIONS_PER_TIER} '
                                   f'{tier} questions, found {count}')
    return questions


def shuffled_options(question: dict) -> tuple[list[str], int]:
    """Shuffle answer options the same way every time (seeded by the question id)."""
    options = [str(question['correct'])] + [str(w) for w in question['wrong']]
    random.Random(question['id']).shuffle(options)
    return options, options.index(str(question['correct']))


def _upgrade_url_checks(conn: sqlite3.Connection) -> None:
    """Older databases only allowed PASS/FAIL. Rebuild the table, keeping its rows."""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'url_checks'").fetchone()
    if row is None or 'BLOCKED' in row[0]:
        return
    conn.executescript('''
        DROP VIEW IF EXISTS resource_catalog;
        ALTER TABLE url_checks RENAME TO url_checks_old;
        CREATE TABLE url_checks (
            resource_slug TEXT PRIMARY KEY,
            status        TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'BLOCKED')),
            detail        TEXT NOT NULL DEFAULT '',
            checked_on    DATE NOT NULL
        );
        INSERT INTO url_checks SELECT * FROM url_checks_old;
        DROP TABLE url_checks_old;
    ''')


def initialize_database(db_path: str | Path | None = None) -> Path:
    """Create or refresh the database. Returns the path that was written."""
    db_path = Path(db_path or DEFAULT_DB)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    paths, resources, projects = load_catalog()
    questions = load_assessments({p['key'] for p in paths})

    conn = sqlite3.connect(db_path)
    try:
        _upgrade_url_checks(conn)
        conn.executescript(SCHEMA_FILE.read_text(encoding='utf-8'))
        conn.executemany(
            '''INSERT INTO paths (path_key, path_name, icon, tagline, description, beginner_focus,
                                  practice_summary, why_recommended, display_order, active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            [
                (p['key'], p['name'], p['icon'], p['tagline'], p['description'], p['beginner_focus'],
                 p['practice_summary'], p['why_recommended'], order, 0 if p.get('active') is False else 1)
                for order, p in enumerate(paths, start=1)
            ],
        )
        ids = dict(conn.execute('SELECT path_key, id FROM paths'))

        for r in resources:
            checks = r.get('curator_checks') or {}
            low, high = r['hours']
            conn.execute(
                '''INSERT INTO resources (slug, path_id, name, url, source, type, level,
                                          duration_hours_min, duration_hours_max, learning_cost,
                                          certificate_cost, learning_cost_check, certificate_cost_check,
                                          skill_check, level_check, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (r['id'], ids[r['path']], r['name'], r['url'], r['source'], r['type'], r['level'],
                 low, high, r['learning_cost'], r['certificate_cost'],
                 *(checks.get(check, 'PENDING') for check in CURATOR_CHECKS),
                 r.get('notes', '')),
            )

        for p in projects:
            low, high = p['hours']
            conn.execute(
                '''INSERT INTO projects (slug, path_id, title, project_type, difficulty,
                                         estimated_effort_hours_min, estimated_effort_hours_max,
                                         description, skills_proved, proof_required, cv_line)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (p['id'], ids[p['path']], p['title'], p['project_type'], p['difficulty'], low, high,
                 p['description'], p['skills_proved'], p['proof_required'], p['cv_line']),
            )

        tier_order = {tier: index for index, tier in enumerate(TIERS)}
        ordered = sorted(enumerate(questions), key=lambda item: (item[1]['path'], tier_order[item[1]['tier']], item[0]))
        for position, (_, q) in enumerate(ordered):
            options, answer_index = shuffled_options(q)
            conn.execute(
                '''INSERT INTO assessment_questions (slug, path_id, tier, position, topic, prompt,
                                                    options, answer_index, explanation)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (q['id'], ids[q['path']], q['tier'], position, q['topic'], q['prompt'],
                 json.dumps(options, ensure_ascii=False), answer_index, q['explanation']),
            )

        # Drop history for resources that were removed from the catalogue.
        conn.execute('DELETE FROM url_checks WHERE resource_slug NOT IN (SELECT slug FROM resources)')
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise CatalogError(f'Catalogue value not allowed by the database: {exc}') from exc
    finally:
        conn.close()
    return db_path
