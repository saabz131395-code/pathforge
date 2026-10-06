import unittest
from collections import Counter
from contextlib import closing
from urllib.parse import parse_qs, urlparse
import sqlite3

from app.services.assessment import score_answers
from database.init_db import load_assessments, load_catalog, shuffled_options
from tests.helpers import AppTestCase

QUESTIONS = [
    {'slug': 'b1', 'tier': 'basic', 'answer_index': 0},
    {'slug': 'b2', 'tier': 'basic', 'answer_index': 1},
    {'slug': 'i1', 'tier': 'intermediate', 'answer_index': 2},
    {'slug': 'i2', 'tier': 'intermediate', 'answer_index': 3},
    {'slug': 'a1', 'tier': 'advanced', 'answer_index': 0},
    {'slug': 'a2', 'tier': 'advanced', 'answer_index': 1},
]
ALL_RIGHT = {'b1': '0', 'b2': '1', 'i1': '2', 'i2': '3', 'a1': '0', 'a2': '1'}


class ScoringTests(unittest.TestCase):
    def test_all_correct_is_advanced(self):
        result = score_answers(QUESTIONS, ALL_RIGHT)
        self.assertEqual((result['score'], result['level'], result['missed']), (6, 'advanced', []))

    def test_nothing_answered_is_beginner_and_everything_is_missed(self):
        result = score_answers(QUESTIONS, {})
        self.assertEqual(result['level'], 'beginner')
        self.assertEqual(len(result['missed']), 6)

    def test_basics_plus_one_intermediate_is_intermediate(self):
        result = score_answers(QUESTIONS, {'b1': '0', 'b2': '1', 'i1': '2'})
        self.assertEqual((result['score'], result['level']), (3, 'intermediate'))

    def test_five_right_without_any_advanced_is_not_advanced(self):
        answers = dict(ALL_RIGHT, a1='3', a2='3')
        self.assertEqual(score_answers(QUESTIONS, answers)['level'], 'intermediate')

    def test_skip_and_garbage_count_as_missed(self):
        answers = dict(ALL_RIGHT, b1='skip', b2='-1')
        result = score_answers(QUESTIONS, answers)
        self.assertEqual(result['missed'], ['b1', 'b2'])
        self.assertEqual(result['score'], 4)


class AssessmentContentTests(unittest.TestCase):
    def test_every_path_has_two_questions_per_tier(self):
        paths = load_catalog()[0]
        questions = load_assessments({p['key'] for p in paths})
        counts = Counter((q['path'], q['tier']) for q in questions)
        for path in paths:
            for tier in ('basic', 'intermediate', 'advanced'):
                self.assertEqual(counts[(path['key'], tier)], 2, (path['key'], tier))

    def test_shuffle_is_stable_and_keeps_the_right_answer(self):
        question = {'id': 'x', 'correct': 'right', 'wrong': ['a', 'b', 'c']}
        first = shuffled_options(question)
        self.assertEqual(first, shuffled_options(question))
        options, index = first
        self.assertEqual(options[index], 'right')
        self.assertEqual(sorted(options), ['a', 'b', 'c', 'right'])

    def test_correct_answers_are_not_always_in_the_same_position(self):
        paths = load_catalog()[0]
        questions = load_assessments({p['key'] for p in paths})
        positions = Counter(shuffled_options(q)[1] for q in questions)
        self.assertEqual(len(positions), 4)
        self.assertLess(max(positions.values()), len(questions) * 0.4)


class AssessmentFlowTests(AppTestCase):
    def _questions(self, key):
        with closing(sqlite3.connect(self.db_path)) as conn:
            return conn.execute(
                '''SELECT q.slug, q.answer_index, q.tier FROM assessment_questions q
                   JOIN paths p ON p.id = q.path_id WHERE p.path_key = ? ORDER BY q.position''', (key,)
            ).fetchall()

    def test_level_check_page_shows_six_questions_in_tier_order(self):
        page = self.client.get(f'/path/{self.path_id("web_dev")}/assess').get_data(as_text=True)
        self.assertEqual(page.count('class="assess-question"'), 6)
        self.assertLess(page.index('data-tier="basic"'), page.index('data-tier="advanced"'))

    def test_all_correct_leads_to_advanced_plan(self):
        pid = self.path_id('software_testing')
        data = {slug: str(answer) for slug, answer, _ in self._questions('software_testing')}
        response = self.client.post(f'/path/{pid}/assess', data=data)
        query = parse_qs(urlparse(response.headers['Location']).query)
        self.assertEqual(query['level'], ['advanced'])
        self.assertEqual(query['score'], ['6'])
        page = self.client.get(response.headers['Location']).get_data(as_text=True)
        self.assertIn('Advanced — go straight to deep work', page)
        self.assertIn('Build a Playwright Automation Framework with CI', page)

    def test_missed_questions_appear_as_topics_to_review(self):
        pid = self.path_id('software_testing')
        data = {slug: (str(answer) if tier == 'basic' else 'skip')
                for slug, answer, tier in self._questions('software_testing')}
        response = self.client.post(f'/path/{pid}/assess', data=data)
        page = self.client.get(response.headers['Location']).get_data(as_text=True)
        self.assertIn('Beginner — start with the foundations', page)
        self.assertIn('4 things worth learning next', page)
        self.assertIn('Boundary value analysis', page)

    def test_plan_without_level_redirects_to_level_check(self):
        pid = self.path_id('web_dev')
        response = self.client.get(f'/path/{pid}/plan')
        self.assertEqual(urlparse(response.headers['Location']).path, f'/path/{pid}/assess')

    def test_plan_ignores_tampered_parameters(self):
        pid = self.path_id('web_dev')
        response = self.client.get(f'/path/{pid}/plan?level=intermediate&score=99&missed=<b>x</b>,other-path-q')
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('<b>x</b>', page)
        self.assertNotIn('REVIEW THESE TOPICS', page)
        self.assertNotIn('score-ring', page)

    def test_skip_link_gives_beginner_plan_with_a_resource_and_project(self):
        pid = self.path_id('cybersecurity')
        page = self.client.get(f'/path/{pid}/plan?level=beginner').get_data(as_text=True)
        self.assertIn('Where to start', page)
        self.assertIn('What to build', page)
        self.assertIn('data-key="guide_beginner_where"', page)

    def test_every_path_and_level_produces_a_complete_plan(self):
        with closing(sqlite3.connect(self.db_path)) as conn:
            ids = [row[0] for row in conn.execute('SELECT id FROM paths')]
        for pid in ids:
            for level in ('beginner', 'intermediate', 'advanced'):
                with self.subTest(path=pid, level=level):
                    page = self.client.get(f'/path/{pid}/plan?level={level}').get_data(as_text=True)
                    self.assertIn('guide-resource', page)
                    self.assertNotIn('No resource is available', page)


if __name__ == '__main__':
    unittest.main()
