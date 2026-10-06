-- PathForge schema.
--
-- paths / resources / projects are rebuilt from catalog/*.yaml on every seed.
-- url_checks is NOT rebuilt: it holds the history written by scraper/recheck.py,
-- keyed by the permanent resource slug, so re-seeding never erases real checks.

PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS resource_catalog;
DROP TABLE IF EXISTS assessment_questions;
DROP TABLE IF EXISTS resources;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS paths;

CREATE TABLE paths (
    id               INTEGER PRIMARY KEY,
    path_key         TEXT    NOT NULL UNIQUE,
    path_name        TEXT    NOT NULL,
    icon             TEXT    NOT NULL,
    tagline          TEXT    NOT NULL,
    description      TEXT    NOT NULL,
    beginner_focus   TEXT    NOT NULL,
    practice_summary TEXT    NOT NULL,
    why_recommended  TEXT    NOT NULL,
    display_order    INTEGER NOT NULL,
    active           INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE resources (
    id                     INTEGER PRIMARY KEY,
    slug                   TEXT    NOT NULL UNIQUE,
    path_id                INTEGER NOT NULL REFERENCES paths (id),
    name                   TEXT    NOT NULL,
    url                    TEXT    NOT NULL,
    source                 TEXT    NOT NULL,
    type                   TEXT    NOT NULL CHECK (type IN ('course', 'tutorial', 'doc', 'video', 'book', 'tool')),
    level                  TEXT    NOT NULL CHECK (level IN ('beginner', 'intermediate', 'advanced')),
    duration_hours_min     INTEGER NOT NULL,
    duration_hours_max     INTEGER NOT NULL,
    learning_cost          TEXT    NOT NULL CHECK (learning_cost IN ('free', 'free_audit', 'freemium', 'paid')),
    certificate_cost       TEXT    NOT NULL CHECK (certificate_cost IN ('free', 'paid', 'not_applicable')),
    learning_cost_check    TEXT    NOT NULL CHECK (learning_cost_check IN ('PASS', 'FAIL', 'PENDING')),
    certificate_cost_check TEXT    NOT NULL CHECK (certificate_cost_check IN ('PASS', 'FAIL', 'PENDING')),
    skill_check            TEXT    NOT NULL CHECK (skill_check IN ('PASS', 'FAIL', 'PENDING')),
    level_check            TEXT    NOT NULL CHECK (level_check IN ('PASS', 'FAIL', 'PENDING')),
    notes                  TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE projects (
    id                         INTEGER PRIMARY KEY,
    slug                       TEXT    NOT NULL UNIQUE,
    path_id                    INTEGER NOT NULL REFERENCES paths (id),
    title                      TEXT    NOT NULL,
    project_type               TEXT    NOT NULL CHECK (project_type IN ('artifact_based', 'outcome_based')),
    difficulty                 TEXT    NOT NULL CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    estimated_effort_hours_min INTEGER NOT NULL,
    estimated_effort_hours_max INTEGER NOT NULL,
    description                TEXT    NOT NULL,
    skills_proved              TEXT    NOT NULL,
    proof_required             TEXT    NOT NULL,
    cv_line                    TEXT    NOT NULL
);

-- Level-check questions. options is a JSON list, already shuffled; answer_index points into it.
CREATE TABLE assessment_questions (
    id           INTEGER PRIMARY KEY,
    slug         TEXT    NOT NULL UNIQUE,
    path_id      INTEGER NOT NULL REFERENCES paths (id),
    tier         TEXT    NOT NULL CHECK (tier IN ('basic', 'intermediate', 'advanced')),
    position     INTEGER NOT NULL,
    topic        TEXT    NOT NULL,
    prompt       TEXT    NOT NULL,
    options      TEXT    NOT NULL,
    answer_index INTEGER NOT NULL,
    explanation  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS url_checks (
    resource_slug TEXT PRIMARY KEY,
    status        TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'BLOCKED')),
    detail        TEXT NOT NULL DEFAULT '',
    checked_on    DATE NOT NULL
);

-- The one place that decides what "verified" means: every curator check passed
-- AND a real URL check passed. Never checked = PENDING. BLOCKED = the site refuses
-- automated checks, so the resource stays visible but is not verified.
CREATE VIEW resource_catalog AS
SELECT
    r.*,
    COALESCE(u.status, 'PENDING')  AS url_check,
    u.detail                       AS url_check_detail,
    u.checked_on                   AS last_checked,
    date(u.checked_on, '+90 days') AS next_review_due,
    CASE
        WHEN u.status = 'PASS'
         AND r.learning_cost_check = 'PASS'
         AND r.certificate_cost_check = 'PASS'
         AND r.skill_check = 'PASS'
         AND r.level_check = 'PASS'
        THEN 'verified'
        ELSE 'needs_review'
    END                            AS verification_status
FROM resources r
LEFT JOIN url_checks u ON u.resource_slug = r.slug;

CREATE INDEX idx_paths_active_order ON paths (active, display_order);
CREATE INDEX idx_resources_path_level ON resources (path_id, level);
CREATE INDEX idx_projects_path_difficulty ON projects (path_id, difficulty);
CREATE INDEX idx_questions_path ON assessment_questions (path_id, position);
