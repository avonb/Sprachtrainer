import sqlite3
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.learning import DAY, VocabularyStore, schedule


class Statement:
    """Execute the production SQL against SQLite with D1's result shape."""
    def __init__(self, connection, sql):
        self.connection, self.sql, self.args = connection, sql, ()

    def bind(self, *args):
        self.args = args
        return self

    async def first(self):
        row = self.connection.execute(self.sql, self.args).fetchone()
        return SimpleNamespace(**dict(row)) if row is not None else None

    async def all(self):
        rows = self.connection.execute(self.sql, self.args).fetchall()
        return SimpleNamespace(results=[SimpleNamespace(**dict(row)) for row in rows])

    async def run(self):
        self.connection.execute(self.sql, self.args)


class Database:
    def __init__(self, connection):
        self.connection = connection

    def prepare(self, sql):
        return Statement(self.connection, sql)


class LearningTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:', isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        migrations = Path(__file__).resolve().parents[1] / 'migrations'
        self.db.executescript((migrations / '0001_vocabulary.sql').read_text())
        self.db.execute("INSERT INTO vocabulary VALUES (1,'سلام','Hallo')")
        self.db.executescript((migrations / '0002_learning.sql').read_text())
        self.db.executescript((migrations / '0003_tags.sql').read_text())
        self.store = VocabularyStore(Database(self.db))

    def tearDown(self):
        self.db.close()

    async def word(self):
        return await self.store.save(persian=' کتاب ', german=' Buch ',
                                     transliteration='ketāb', now=1000)

    async def test_migration_preserves_existing_words(self):
        word = await self.store.get(1)
        self.assertEqual((word['persian'], word['german']), ('سلام', 'Hallo'))
        self.assertGreater(word['created_at'], 0)
        self.assertEqual(word['transliteration'], '')

    async def test_save_edit_and_archive_preserve_learning(self):
        word = await self.word()
        self.assertEqual(word['persian'], 'کتاب')
        review = await self.store.review(word['id'], 'good', now=1000)
        await self.store.save(vocabulary_id=word['id'], persian='کتاب', german='das Buch', now=1001)
        self.assertEqual((await self.store.state(word['id']))['due_at'], review['due_at'])
        await self.store.archive(word['id'], now=1002)
        self.assertNotIn(word['id'], [w['id'] for w in await self.store.due(now=100000)])
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'archived'):
            await self.store.review(word['id'], 'easy', now=1003)
        await self.store.archive(word['id'], archived=False, now=1004)
        self.assertEqual(len(await self.store.history(word['id'])), 1)

    async def test_due_time_boundary_and_new_words(self):
        word = await self.word()
        self.assertEqual([w['id'] for w in await self.store.due(now=1000)], [word['id']])
        await self.store.review(word['id'], 'again', now=1000)
        self.assertEqual(await self.store.due(now=1599), [])
        self.assertEqual([w['id'] for w in await self.store.due(now=1600)], [word['id']])

    async def test_review_retry_is_idempotent_after_later_reviews(self):
        word = await self.word()
        first = await self.store.review(word['id'], 'good', review_id='one', now=1000)
        await self.store.review(word['id'], 'easy', review_id='two', now=2000)
        self.assertEqual(await self.store.review(word['id'], 'good', review_id='one', now=3000), first)
        self.assertEqual((await self.store.state(word['id']))['revision'], 2)
        self.assertEqual(len(await self.store.history(word['id'])), 2)
        with self.assertRaisesRegex(ValueError, 'different result'):
            await self.store.review(word['id'], 'again', review_id='one')

    async def test_stale_review_rolls_back_and_does_not_erase_history(self):
        word = await self.word()
        await self.store.review(word['id'], 'good', now=1000)
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'stale'):
            self.db.execute('INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,?)',
                            ('stale', word['id'], 'again', 1001, 0, 1601, 0, 0, 1))
        self.assertEqual((await self.store.state(word['id']))['revision'], 1)
        self.assertEqual(len(await self.store.history(word['id'])), 1)

    async def test_invalid_review_leaves_state_unchanged(self):
        word = await self.word()
        await self.store.review(word['id'], 'good', now=1000)
        with self.assertRaises(ValueError):
            await self.store.review(word['id'], 'unknown', now=1001)
        with self.assertRaises(ValueError):
            await self.store.review(word['id'], 'good', now=999)
        with self.assertRaises(sqlite3.IntegrityError):
            await self.store.review(9999, 'good', now=1001)
        self.assertEqual((await self.store.state(word['id']))['revision'], 1)

    async def test_validation_and_parameterized_text(self):
        with self.assertRaises(ValueError):
            await self.store.save(persian=' ', german='Hallo')
        with self.assertRaises(ValueError):
            await self.store.save(persian=42, german='Hallo')
        with self.assertRaises(ValueError):
            await self.store.due(limit=1000)
        text = "Buch'); DROP TABLE vocabulary; --"
        word = await self.store.save(persian='کتاب', german=text)
        self.assertEqual((await self.store.get(word['id']))['german'], text)

    async def test_tags_are_shared_normalized_and_idempotent(self):
        word = await self.word()
        self.assertEqual(await self.store.add_tag(word['id'], '  Alltag  '), ['alltag'])
        self.assertEqual(await self.store.add_tag(word['id'], 'ALLTAG'), ['alltag'])
        await self.store.add_tag(1, 'alltag')
        await self.store.add_tag(word['id'], 'Lektion   1')
        self.assertEqual((await self.store.get(word['id']))['tags'], ['alltag', 'lektion 1'])
        self.assertEqual(await self.store.list_tags(), [
            {'name': 'alltag', 'vocabulary_count': 2},
            {'name': 'lektion 1', 'vocabulary_count': 1}])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM tags').fetchone()[0], 2)

    async def test_remove_tag_does_not_change_other_words_or_learning(self):
        word = await self.word()
        await self.store.add_tag(1, 'Alltag')
        await self.store.add_tag(word['id'], 'Alltag')
        await self.store.review(word['id'], 'good', now=1000)
        state = await self.store.state(word['id'])
        self.assertEqual(await self.store.remove_tag(word['id'], 'ALLTAG'), [])
        self.assertEqual(await self.store.remove_tag(word['id'], 'alltag'), [])
        self.assertEqual(await self.store.tags(1), ['alltag'])
        self.assertEqual(await self.store.state(word['id']), state)
        self.assertEqual(len(await self.store.history(word['id'])), 1)

    async def test_due_tag_filter_respects_schedule_and_archive(self):
        word = await self.word()
        await self.store.add_tag(word['id'], 'Lesen')
        self.assertEqual([w['id'] for w in await self.store.due(now=1000, tag='LESEN')], [word['id']])
        self.assertEqual(await self.store.due(now=1000, tag='unbekannt'), [])
        await self.store.review(word['id'], 'good', now=1000)
        self.assertEqual(await self.store.due(now=1001, tag='lesen'), [])
        await self.store.archive(word['id'], now=1002)
        self.assertEqual(await self.store.due(now=100000, tag='lesen'), [])
        self.assertEqual(await self.store.tags(word['id']), ['lesen'])
        self.assertEqual(await self.store.list_tags(), [{'name': 'lesen', 'vocabulary_count': 0}])

    async def test_tag_validation_and_parameterized_names(self):
        word = await self.word()
        for invalid in ('  ', 'x' * 81, 42):
            with self.assertRaises(ValueError):
                await self.store.add_tag(word['id'], invalid)
        with self.assertRaises(ValueError):
            await self.store.add_tag(9999, 'missing word')
        self.assertEqual(await self.store.list_tags(), [])
        tag = "x'); drop table tags; --"
        self.assertEqual(await self.store.add_tag(word['id'], tag), [tag])

    def test_intervals_and_lapses(self):
        state = None
        for days in (1, 3, 6, 12):
            state = schedule(state, 'good', 1000)
            self.assertEqual(state['interval_days'], days)
            self.assertEqual(state['due_at'], 1000 + days * DAY)
        state = schedule(state, 'again', 2000)
        self.assertEqual((state['due_at'], state['repetitions'], state['lapses']), (2600, 0, 1))
        self.assertEqual(schedule(state, 'good', 2600)['interval_days'], 1)
        self.assertEqual(schedule(None, 'hard', 1000)['interval_days'], 1)
        self.assertEqual(schedule(None, 'easy', 1000)['interval_days'], 4)
        self.assertEqual(schedule({'interval_days': 300}, 'easy', 1000)['interval_days'], 365)


if __name__ == '__main__':
    unittest.main()
