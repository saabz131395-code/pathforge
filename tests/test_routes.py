import unittest
from urllib.parse import parse_qs, urlparse

from tests.helpers import AppTestCase


class PageTests(AppTestCase):
    def test_home_lists_every_path(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        for name in ('Web Development', 'Software Testing', 'Cybersecurity Basics'):
            self.assertIn(name, response.get_data(as_text=True))

    def test_every_path_screen_loads(self):
        pid = self.path_id('web_dev')
        for suffix in ('', '/resources', '/projects', '/progress', '/proof'):
            with self.subTest(screen=suffix or 'overview'):
                self.assertEqual(self.client.get(f'/path/{pid}{suffix}').status_code, 200)

    def test_unknown_path_is_404_with_friendly_page(self):
        response = self.client.get('/path/9999')
        self.assertEqual(response.status_code, 404)
        self.assertIn('Back to all paths', response.get_data(as_text=True))

    def test_garbage_filters_do_not_crash(self):
        pid = self.path_id('web_dev')
        response = self.client.get(f'/path/{pid}/resources?level=<script>&type=zzz&verified_only=yes')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('<script>', response.get_data(as_text=True))

    def test_credit_footer_is_present(self):
        self.assertIn('Built by', self.client.get('/').get_data(as_text=True))


class RecommendationFlowTests(AppTestCase):
    def test_choosing_a_path_goes_to_its_level_check(self):
        response = self.client.post('/recommend', data={'interest': 'ui_ux'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.headers['Location']).path, f'/path/{self.path_id("ui_ux")}/assess')

    def test_unknown_interest_is_rejected(self):
        self.assertEqual(self.client.post('/recommend', data={'interest': 'astronaut'}).status_code, 400)

    def test_home_path_cards_link_to_level_check(self):
        page = self.client.get('/').get_data(as_text=True)
        self.assertIn(f'/path/{self.path_id("web_dev")}/assess', page)
        self.assertNotIn('Where are you starting', page)

    def test_home_has_one_click_cards_for_every_path_and_no_duplicate_list(self):
        page = self.client.get('/').get_data(as_text=True)
        self.assertEqual(page.count('class="path-card card path-card-link"'), 16)
        self.assertNotIn('choice-link', page)
        self.assertIn('href="/recommend/quiz"', page)

    def test_home_shows_tips_tools_and_freelance_steps(self):
        page = self.client.get('/').get_data(as_text=True)
        for text in ('How to learn online without getting stuck', 'Where to publish your proof',
                     'From proof to your first small client', 'https://pages.github.com/'):
            self.assertIn(text, page)

    def test_not_sure_goes_to_quiz(self):
        response = self.client.post('/recommend', data={'interest': 'not_sure'})
        self.assertTrue(response.headers['Location'].startswith('/recommend/quiz'))

    def test_quiz_winner_goes_to_level_check(self):
        response = self.client.post('/recommend/quiz', data={
            'afternoon': 'break', 'result': 'quality', 'style': 'checklist', 'task': 'test'})
        self.assertEqual(urlparse(response.headers['Location']).path,
                         f'/path/{self.path_id("software_testing")}/assess')

    def test_incomplete_quiz_goes_back_with_message(self):
        response = self.client.post('/recommend/quiz', data={'afternoon': 'build'})
        self.assertIn('missing=1', response.headers['Location'])
        page = self.client.get(response.headers['Location']).get_data(as_text=True)
        self.assertIn('Please answer every question', page)

    def test_tie_screen_shows_only_real_candidates(self):
        response = self.client.get('/recommend/tie?candidates=web_dev,fake_path,ui_ux')
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('2 GOOD MATCHES', page)
        self.assertIn(f'/path/{self.path_id("ui_ux")}/assess', page)

    def test_empty_tie_redirects_home(self):
        self.assertEqual(self.client.get('/recommend/tie?candidates=fake').status_code, 302)


class VerificationTests(AppTestCase):
    """The core promise of the product: 'verified' must never be claimed without real checks."""

    def test_fresh_database_claims_nothing_is_verified(self):
        pid = self.path_id('web_dev')
        page = self.client.get(f'/path/{pid}/resources').get_data(as_text=True)
        self.assertNotIn('✓ VERIFIED', page)
        self.assertIn('REVIEW PENDING', page)

    def test_resource_becomes_verified_only_after_passing_url_check(self):
        pid = self.path_id('web_dev')
        self.mark_url('mdn-learn-web-development', 'PASS')
        page = self.client.get(f'/path/{pid}/resources?verified_only=1').get_data(as_text=True)
        self.assertIn('MDN — Learn Web Development', page)
        self.assertEqual(page.count('✓ VERIFIED'), 1)

    def test_pending_curator_checks_block_verification(self):
        pid = self.path_id('web_dev')
        self.mark_url('mdn-javascript-guide', 'PASS')  # curator checks still PENDING in YAML
        page = self.client.get(f'/path/{pid}/resources?verified_only=1').get_data(as_text=True)
        self.assertNotIn('MDN — JavaScript Guide', page)

    def test_broken_links_are_hidden(self):
        pid = self.path_id('web_dev')
        self.mark_url('mdn-learn-web-development', 'FAIL')
        page = self.client.get(f'/path/{pid}/resources').get_data(as_text=True)
        self.assertNotIn('MDN — Learn Web Development', page)

    def test_reseeding_keeps_url_check_history(self):
        from database.init_db import initialize_database
        self.mark_url('mdn-learn-web-development', 'PASS')
        initialize_database(self.db_path)
        pid = self.path_id('web_dev')
        page = self.client.get(f'/path/{pid}/resources?verified_only=1').get_data(as_text=True)
        self.assertIn('MDN — Learn Web Development', page)


class ProgressKeyTests(AppTestCase):
    def test_progress_uses_stable_keys_not_database_ids(self):
        pid = self.path_id('web_dev')
        page = self.client.get(f'/path/{pid}/progress').get_data(as_text=True)
        self.assertIn('window.PATH_KEY = "web_dev"', page)
        self.assertIn('data-key="project_build-a-responsive-personal-portfolio_built"', page)


if __name__ == '__main__':
    unittest.main()
