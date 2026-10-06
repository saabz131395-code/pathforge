"""Recommendation rules (pure Python — no database, easy to unit test).

Rules that are locked for V1:
* An explicit path choice is always respected; the quiz never overrides it.
* The level comes from the per-path level check (see assessment.py), never from a
  self-reported guess, and it never produces a completion-date estimate.
* Budget does not influence the recommendation.
"""

from __future__ import annotations

# Each answer adds one point to every path it lists. Paths are spread across
# different pairings in each question so combinations of answers separate them.
# The last question names one path per option and is used as the tie-breaker.
# tests/test_recommendation.py checks every path can win and ties stay small.
QUIZ = [
    {
        'id': 'afternoon',
        'prompt': 'How would you rather spend a free afternoon?',
        'options': [
            {'id': 'build', 'label': 'Building something that works', 'paths': ['web_dev', 'mobile_dev', 'game_dev']},
            {'id': 'visual', 'label': 'Making something look or feel great', 'paths': ['ui_ux', 'graphic_design', 'content_video']},
            {'id': 'numbers', 'label': 'Digging into numbers and patterns', 'paths': ['data_analysis', 'ai_ml', 'digital_marketing']},
            {'id': 'break', 'label': 'Finding what is broken or risky', 'paths': ['software_testing', 'cybersecurity']},
            {'id': 'words', 'label': 'Writing or explaining things clearly', 'paths': ['technical_writing', 'content_writing']},
            {'id': 'business', 'label': 'Running a small business idea', 'paths': ['ecommerce', 'digital_marketing']},
            {'id': 'systems', 'label': 'Figuring out how a system works under the hood', 'paths': ['cloud_it', 'python_data']},
        ],
    },
    {
        'id': 'result',
        'prompt': 'Which finished result would you be proudest to show?',
        'options': [
            {'id': 'live_app', 'label': 'A website or app people can use', 'paths': ['web_dev', 'ui_ux', 'mobile_dev']},
            {'id': 'insight', 'label': 'A report or model that answers a real question', 'paths': ['data_analysis', 'python_data', 'ai_ml']},
            {'id': 'audience', 'label': 'A video, post or campaign people react to', 'paths': ['content_video', 'digital_marketing', 'graphic_design']},
            {'id': 'secured', 'label': 'A system you set up, secured and documented', 'paths': ['cybersecurity', 'cloud_it']},
            {'id': 'quality', 'label': 'A clear guide, article or test report', 'paths': ['technical_writing', 'software_testing', 'content_writing']},
            {'id': 'product', 'label': 'A game people play or a store people buy from', 'paths': ['game_dev', 'ecommerce']},
        ],
    },
    {
        'id': 'style',
        'prompt': 'Which way of working suits you best?',
        'options': [
            {'id': 'code', 'label': 'Writing code until it finally works', 'paths': ['web_dev', 'python_data', 'game_dev']},
            {'id': 'sketch', 'label': 'Sketching, designing and iterating', 'paths': ['ui_ux', 'graphic_design', 'content_video']},
            {'id': 'checklist', 'label': 'Careful step-by-step checklists', 'paths': ['software_testing', 'cloud_it', 'ecommerce']},
            {'id': 'words', 'label': 'Finding the right words for an audience', 'paths': ['technical_writing', 'content_writing', 'digital_marketing']},
            {'id': 'investigate', 'label': 'Investigating why something happened', 'paths': ['data_analysis', 'cybersecurity', 'ai_ml']},
            {'id': 'tinker', 'label': 'Tinkering with apps and gadgets', 'paths': ['mobile_dev', 'ai_ml', 'cloud_it']},
        ],
    },
    {
        'id': 'task',
        'prompt': 'Which small task for someone else sounds most enjoyable?',
        'options': [
            {'id': 'site', 'label': 'Build or fix a small website', 'paths': ['web_dev']},
            {'id': 'app', 'label': 'Build a simple phone app', 'paths': ['mobile_dev']},
            {'id': 'screens', 'label': 'Improve the screens of an app', 'paths': ['ui_ux']},
            {'id': 'graphics', 'label': 'Design posts, posters or a logo', 'paths': ['graphic_design']},
            {'id': 'automate', 'label': 'Automate a boring task with a script', 'paths': ['python_data']},
            {'id': 'report', 'label': 'Turn messy data into a clear report', 'paths': ['data_analysis']},
            {'id': 'ai', 'label': 'Build something that uses AI to predict or generate', 'paths': ['ai_ml']},
            {'id': 'grow', 'label': 'Help a page grow its audience', 'paths': ['digital_marketing']},
            {'id': 'video', 'label': 'Edit a video', 'paths': ['content_video']},
            {'id': 'write', 'label': 'Write blog posts or product descriptions', 'paths': ['content_writing']},
            {'id': 'test', 'label': 'Test a product before it launches', 'paths': ['software_testing']},
            {'id': 'server', 'label': 'Set up a server or cloud account', 'paths': ['cloud_it']},
            {'id': 'docs', 'label': 'Write a how-to guide for a tool', 'paths': ['technical_writing']},
            {'id': 'secure', 'label': 'Check a website for security problems', 'paths': ['cybersecurity']},
            {'id': 'store', 'label': 'Set up and run an online store', 'paths': ['ecommerce']},
            {'id': 'game', 'label': 'Make a small game', 'paths': ['game_dev']},
        ],
    },
]


# When totals are equal, the more concrete questions decide: first the client
# task, then the finished result. Anything still equal is shown as a tie.
TIE_BREAK_ORDER = ('task', 'result')


def quiz_paths() -> set[str]:
    """Every path key the quiz can point to (used by tests to catch gaps)."""
    return {key for question in QUIZ for option in question['options'] for key in option['paths']}


def score_quiz(answers: dict[str, str], valid_paths: list[str]) -> dict:
    """Score quiz answers.

    ``answers`` maps question id -> option id. ``valid_paths`` is the ordered list of
    active path keys; it decides tie order and filters out inactive paths.

    Returns one of:
      {'type': 'incomplete'}                       not every question answered
      {'type': 'winner', 'path_key': key}
      {'type': 'tie', 'candidates': [key, ...]}    two or more equal top scores
    """
    # Score = (total points, points from tie-break questions in priority order).
    scores = {key: [0] * (1 + len(TIE_BREAK_ORDER)) for key in valid_paths}
    for question in QUIZ:
        chosen = answers.get(question['id'])
        option = next((o for o in question['options'] if o['id'] == chosen), None)
        if option is None:
            return {'type': 'incomplete'}
        for key in option['paths']:
            if key in scores:
                scores[key][0] += 1
                if question['id'] in TIE_BREAK_ORDER:
                    scores[key][1 + TIE_BREAK_ORDER.index(question['id'])] += 1

    best = max(scores.values(), default=[0])
    if best[0] == 0:
        return {'type': 'incomplete'}
    winners = [key for key in valid_paths if scores[key] == best]
    if len(winners) == 1:
        return {'type': 'winner', 'path_key': winners[0]}
    return {'type': 'tie', 'candidates': winners}
