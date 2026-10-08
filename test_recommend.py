import sqlite3
import unittest

from flask import g

from app import app, recommend


class RecommendTests(unittest.TestCase):
    def setUp(self):
        self.context = app.app_context()
        self.context.push()
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        g.db = self.db
        self.db.executescript('''
            CREATE TABLE users (id INTEGER, username TEXT);
            CREATE TABLE posts (id INTEGER, user_id INTEGER, content TEXT, created_at TEXT);
            CREATE TABLE follows (follower_id INTEGER, followed_id INTEGER);
            CREATE TABLE reactions (user_id INTEGER, post_id INTEGER, reaction_type TEXT);
            INSERT INTO users VALUES (1, 'reader'), (2, 'maker'), (3, 'other');
        ''')
        self.db.executemany('INSERT INTO posts VALUES (?, ?, ?, ?)', [
            (1, 2, 'DIY wood furniture', '2026-01-01'),
            *[(i, 3, 'DIY wood furniture project', f'2026-01-{i:02d}')
              for i in range(2, 7)],
            (7, 3, 'Football match stadium', '2026-02-01'),
            (8, 1, 'DIY wood furniture', '2026-03-01'),
            (9, 3, '', '2026-04-01'),
        ])

    def tearDown(self):
        self.context.pop()

    def ids(self, user_id=1, following=False):
        return [post['id'] for post in recommend(user_id, following)]

    def test_positive_reactions_select_relevant_posts_then_order_by_date(self):
        for reaction in ('like', 'love', 'laugh', 'wow'):
            with self.subTest(reaction=reaction):
                self.db.execute('DELETE FROM reactions')
                self.db.execute('INSERT INTO reactions VALUES (1, 1, ?)', (reaction,))
                self.assertEqual(self.ids(), [6, 5, 4, 3, 2])

    def test_following_learns_content_and_enforces_filter(self):
        self.db.execute('INSERT INTO follows VALUES (1, 2)')
        self.assertNotIn(7, self.ids())
        self.assertEqual(self.ids(following=True), [1])

    def test_negative_reactions_do_not_seed_interests(self):
        for reaction in ('sad', 'angry'):
            self.db.execute('DELETE FROM reactions')
            self.db.execute('INSERT INTO reactions VALUES (1, 1, ?)', (reaction,))
            self.assertEqual(self.ids(), [9, 7, 6, 5, 4])

    def test_cold_start_and_empty_candidates(self):
        self.assertEqual(self.ids(), [9, 7, 6, 5, 4])
        self.assertEqual(self.ids(None), [9, 8, 7, 6, 5])
        self.assertEqual(self.ids(following=True), [])
        self.db.execute('DELETE FROM posts')
        self.assertEqual(self.ids(), [])

    def test_empty_text_interest_is_safe(self):
        self.db.execute("INSERT INTO reactions VALUES (1, 9, 'like')")
        self.assertEqual(self.ids(), [7, 6, 5, 4, 3])


if __name__ == '__main__':
    unittest.main()
