import itertools
import unittest

from app.services.recommendation import QUIZ, quiz_paths, score_quiz
from database.init_db import load_catalog

PATH_KEYS = [path['key'] for path in load_catalog()[0]]


def answers(*option_ids):
    return dict(zip([question['id'] for question in QUIZ], option_ids))


class QuizTests(unittest.TestCase):
    def test_consistent_answers_give_a_clear_winner(self):
        result = score_quiz(answers('build', 'live_app', 'code', 'site'), PATH_KEYS)
        self.assertEqual(result, {'type': 'winner', 'path_key': 'web_dev'})

    def test_testing_minded_answers_pick_software_testing(self):
        result = score_quiz(answers('break', 'quality', 'checklist', 'test'), PATH_KEYS)
        self.assertEqual(result['path_key'], 'software_testing')

    def test_missing_answer_is_incomplete(self):
        self.assertEqual(score_quiz(answers('build'), PATH_KEYS)['type'], 'incomplete')

    def test_unknown_option_is_incomplete(self):
        self.assertEqual(score_quiz(answers('build', 'live_app', 'code', 'hacked'), PATH_KEYS)['type'], 'incomplete')

    def test_inactive_paths_are_never_recommended(self):
        active = [key for key in PATH_KEYS if key != 'web_dev']
        result = score_quiz(answers('build', 'live_app', 'code', 'site'), active)
        self.assertNotEqual(result.get('path_key'), 'web_dev')
        self.assertNotIn('web_dev', result.get('candidates', []))

    def test_every_catalog_path_is_reachable_by_the_quiz(self):
        self.assertEqual(quiz_paths(), set(PATH_KEYS))

    def test_quiz_only_mentions_real_paths(self):
        self.assertTrue(quiz_paths() <= set(PATH_KEYS))

    def test_every_path_can_win(self):
        winners = set()
        options = [[option['id'] for option in question['options']] for question in QUIZ]
        for combo in itertools.product(*options):
            result = score_quiz(answers(*combo), PATH_KEYS)
            if result['type'] == 'winner':
                winners.add(result['path_key'])
        self.assertEqual(winners, set(PATH_KEYS))

    def test_most_answer_combinations_give_a_winner_and_ties_stay_small(self):
        options = [[option['id'] for option in question['options']] for question in QUIZ]
        results = [score_quiz(answers(*combo), PATH_KEYS) for combo in itertools.product(*options)]
        winners = sum(1 for result in results if result['type'] == 'winner')
        self.assertGreater(winners / len(results), 0.75)
        largest_tie = max(len(result['candidates']) for result in results if result['type'] == 'tie')
        self.assertLessEqual(largest_tie, 3)


if __name__ == '__main__':
    unittest.main()
