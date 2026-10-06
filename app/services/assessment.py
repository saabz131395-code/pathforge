"""Level check scoring and the personalised start guide.

Scoring is pure Python (easy to test). The start guide combines the result with
catalogue data. Locked rule: nothing here predicts a finish date.
"""

from __future__ import annotations

import json

from ..db import get_db
from . import catalog

LEVEL_ORDER = ('beginner', 'intermediate', 'advanced')

LEVEL_COPY = {
    'beginner': {
        'title': 'Beginner — start with the foundations',
        'summary': 'You are at the start of this path, which is exactly where everyone begins. Your guide focuses on one beginner resource and a first small project.',
    },
    'intermediate': {
        'title': 'Intermediate — you know the basics',
        'summary': 'You already have the foundations. Skip what you know, fill the gaps below, and move quickly into a portfolio project.',
    },
    'advanced': {
        'title': 'Advanced — go straight to deep work',
        'summary': 'You answered the hard questions well. Your guide skips the basics and points you at advanced resources and a production-quality project.',
    },
}

STUDY_METHOD = {
    'beginner': [
        'Follow one resource in order. Don\'t jump between courses; that is the most common reason beginners stall.',
        'Type every example yourself instead of only watching or reading.',
        'Keep a simple notes file: three things you learned and one question after every session.',
    ],
    'intermediate': [
        'Skim the parts you already know and slow down on the topics listed under "Review these topics".',
        'Start your project early and learn whatever it needs as you go.',
        'Publish your work as you build (GitHub, Behance, a blog), not only at the end.',
    ],
    'advanced': [
        'Use resources as references, not courses: go straight to your gaps.',
        'Build the advanced project to a professional standard, with tests, documentation and a live link.',
        'Get outside feedback: share your work in a community, with a mentor, or in an open-source project.',
    ],
}


def score_answers(questions: list[dict], answers: dict[str, str]) -> dict:
    """Score submitted answers.

    ``questions`` need ``slug``, ``tier`` and ``answer_index``; ``answers`` maps
    slug -> submitted option index (as a string). Unanswered counts as missed.
    """
    correct_by_tier = {'basic': 0, 'intermediate': 0, 'advanced': 0}
    missed = []
    for q in questions:
        given = answers.get(q['slug'])
        if given is not None and given.isdigit() and int(given) == q['answer_index']:
            correct_by_tier[q['tier']] += 1
        else:
            missed.append(q['slug'])

    score = sum(correct_by_tier.values())
    if score >= 5 and correct_by_tier['advanced'] >= 1:
        level = 'advanced'
    elif score >= 3:
        level = 'intermediate'
    else:
        level = 'beginner'
    return {'score': score, 'total': len(questions), 'level': level, 'missed': missed,
            'by_tier': correct_by_tier}


# ---- Database-backed helpers ------------------------------------------------

def get_questions(path_id: int) -> list[dict]:
    rows = get_db().execute(
        'SELECT * FROM assessment_questions WHERE path_id = ? ORDER BY position', (path_id,)
    ).fetchall()
    return [{**dict(row), 'options': json.loads(row['options'])} for row in rows]


def _levels_from(level: str) -> list[str]:
    """The chosen level first, then lower levels as fallbacks."""
    index = LEVEL_ORDER.index(level)
    return [level] + list(reversed(LEVEL_ORDER[:index]))


def build_start_guide(path_id: int, level: str, missed_slugs: list[str]) -> dict:
    """Everything the personalised plan page needs."""
    questions = get_questions(path_id)
    by_slug = {q['slug']: q for q in questions}
    review = [by_slug[slug] for slug in missed_slugs if slug in by_slug]
    for q in review:
        q['correct_answer'] = q['options'][q['answer_index']]

    resources: list = []
    for candidate_level in _levels_from(level):
        resources = catalog.list_resources(path_id, level=candidate_level)
        if resources:
            break

    projects: list = []
    for candidate_level in _levels_from(level):
        projects = catalog.list_projects(path_id, candidate_level)
        if projects:
            break

    return {
        'level_copy': LEVEL_COPY[level],
        'study_method': STUDY_METHOD[level],
        'review': review,
        'first_resource': resources[0] if resources else None,
        'backup_resource': resources[1] if len(resources) > 1 else None,
        'project': projects[0] if projects else None,
    }
