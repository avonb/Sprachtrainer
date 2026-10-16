"""Internal D1 data access for one personal collection; no HTTP access yet."""

import json
import math
import time
import unicodedata
from uuid import uuid4

DAY = 86400
RATINGS = ('again', 'hard', 'good', 'easy')
WORD_FIELDS = ('persian', 'german', 'transliteration', 'example_persian',
               'example_german', 'notes')
WORD_COLUMNS = ('id', *WORD_FIELDS, 'created_at', 'updated_at', 'archived_at')
STATE_COLUMNS = ('vocabulary_id', 'due_at', 'interval_days', 'repetitions',
                 'lapses', 'last_reviewed_at', 'revision')
REVIEW_COLUMNS = ('id', 'vocabulary_id', 'rating', 'reviewed_at',
                  'previous_revision', 'due_at', 'interval_days',
                  'repetitions', 'lapses')
TAG_SELECTION = (
    '(SELECT json_group_array(name) FROM ('
    'SELECT t.name FROM tags t JOIN vocabulary_tags vt ON vt.tag_id=t.id '
    'WHERE vt.vocabulary_id=v.id ORDER BY t.name)) AS tags_json'
)


def normalize_tag(name):
    if not isinstance(name, str):
        raise ValueError('tag must be a string')
    name = unicodedata.normalize('NFC', ' '.join(name.split()).casefold())
    if not 1 <= len(name) <= 80:
        raise ValueError('tag must contain between 1 and 80 characters')
    return name


def word_dict(row, *, due=False):
    word = row_dict(row, (*WORD_COLUMNS, 'due_at') if due else WORD_COLUMNS)
    if word is not None:
        word['tags'] = json.loads(row.tags_json)
    return word


def row_dict(row, columns):
    """D1 returns JS objects in Python Workers."""
    return None if row is None else {name: getattr(row, name) for name in columns}


def schedule(state, rating, now):
    """Simple interval rules, deliberately not presented as FSRS or SM-2."""
    if rating not in RATINGS:
        raise ValueError('rating must be again, hard, good or easy')
    state = state or {}
    if now < state.get('last_reviewed_at', now):
        raise ValueError('review predates previous review')
    interval = state.get('interval_days', 0)
    lapses = state.get('lapses', 0)
    repetitions = state.get('repetitions', 0)
    if rating == 'again':
        return dict(due_at=now + 600, interval_days=0, repetitions=0,
                    lapses=lapses + 1)
    if rating == 'hard':
        interval = max(1, math.ceil(interval * 1.2))
    elif rating == 'good':
        interval = 1 if repetitions == 0 else (3 if repetitions == 1 else max(1, interval * 2))
    else:
        interval = max(4, interval * 3)
    interval = min(interval, 365)
    return dict(due_at=now + interval * DAY, interval_days=interval,
                repetitions=repetitions + 1, lapses=lapses)


class VocabularyStore:
    def __init__(self, db):
        self.db = db

    def statement(self, sql, *args):
        return self.db.prepare(sql).bind(*args)

    async def get(self, vocabulary_id):
        row = await self.statement(
            'SELECT v.*,' + TAG_SELECTION + ' FROM vocabulary v WHERE v.id=?',
            vocabulary_id).first()
        return word_dict(row)

    async def save(self, *, persian, german, transliteration='', example_persian='',
                   example_german='', notes='', vocabulary_id=None, now=None):
        now = int(time.time()) if now is None else now
        values = (persian, german, transliteration, example_persian, example_german, notes)
        if any(not isinstance(value, str) for value in values):
            raise ValueError('vocabulary fields must be strings')
        values = tuple(unicodedata.normalize('NFC', value).strip() for value in values)
        if not values[0] or not values[1]:
            raise ValueError('persian and german must not be empty')
        if any(len(value) > 10000 for value in values):
            raise ValueError('vocabulary fields must not exceed 10000 characters')
        if vocabulary_id is None:
            row = await self.statement(
                'INSERT INTO vocabulary (' + ','.join(WORD_FIELDS) + ',created_at,updated_at) '
                'VALUES (?,?,?,?,?,?,?,?) RETURNING *', *values, now, now).first()
        else:
            row = await self.statement(
                'UPDATE vocabulary SET ' + ','.join(name + '=?' for name in WORD_FIELDS)
                + ',updated_at=? WHERE id=? RETURNING *', *values, now, vocabulary_id).first()
            if row is None:
                raise ValueError('vocabulary not found')
        return await self.get(row.id)

    async def archive(self, vocabulary_id, *, archived=True, now=None):
        now = int(time.time()) if now is None else now
        row = await self.statement(
            'UPDATE vocabulary SET archived_at=?,updated_at=? WHERE id=? RETURNING *',
            now if archived else None, now, vocabulary_id).first()
        if row is None:
            raise ValueError('vocabulary not found')
        return await self.get(row.id)

    async def tags(self, vocabulary_id):
        word = await self.get(vocabulary_id)
        if word is None:
            raise ValueError('vocabulary not found')
        return word['tags']

    async def add_tag(self, vocabulary_id, name):
        name = normalize_tag(name)
        # Verify the word before creating a catalog entry.
        await self.tags(vocabulary_id)
        await self.statement('INSERT INTO tags(name) VALUES (?) '
                             'ON CONFLICT(name) DO NOTHING', name).run()
        await self.statement(
            'INSERT INTO vocabulary_tags(vocabulary_id,tag_id) '
            'SELECT ?,id FROM tags WHERE name=? '
            'ON CONFLICT(vocabulary_id,tag_id) DO NOTHING', vocabulary_id, name).run()
        return await self.tags(vocabulary_id)

    async def remove_tag(self, vocabulary_id, name):
        name = normalize_tag(name)
        await self.tags(vocabulary_id)
        await self.statement(
            'DELETE FROM vocabulary_tags WHERE vocabulary_id=? '
            'AND tag_id IN (SELECT id FROM tags WHERE name=?)', vocabulary_id, name).run()
        return await self.tags(vocabulary_id)

    async def list_tags(self):
        result = await self.statement(
            'SELECT t.name,COUNT(v.id) AS vocabulary_count FROM tags t '
            'LEFT JOIN vocabulary_tags vt ON vt.tag_id=t.id '
            'LEFT JOIN vocabulary v ON v.id=vt.vocabulary_id AND v.archived_at IS NULL '
            'GROUP BY t.id,t.name ORDER BY t.name').all()
        return [row_dict(row, ('name', 'vocabulary_count')) for row in result.results]

    async def state(self, vocabulary_id):
        row = await self.statement(
            'SELECT * FROM learning_state WHERE vocabulary_id=?', vocabulary_id).first()
        return row_dict(row, STATE_COLUMNS)

    async def due(self, *, now=None, limit=20, tag=None):
        now = int(time.time()) if now is None else now
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('limit must be between 1 and 100')
        tag_filter = ''
        args = [now]
        if tag is not None:
            tag_filter = (' AND EXISTS (SELECT 1 FROM vocabulary_tags vt '
                          'JOIN tags t ON t.id=vt.tag_id '
                          'WHERE vt.vocabulary_id=v.id AND t.name=?)')
            args.append(normalize_tag(tag))
        result = await self.statement(
            'SELECT v.*,COALESCE(s.due_at,v.created_at) AS due_at,' + TAG_SELECTION + ' '
            'FROM vocabulary v LEFT JOIN learning_state s ON s.vocabulary_id=v.id '
            'WHERE v.archived_at IS NULL AND COALESCE(s.due_at,v.created_at)<=? '
            + tag_filter + ' ORDER BY due_at,v.id LIMIT ?', *args, limit).all()
        return [word_dict(row, due=True) for row in result.results]

    async def review(self, vocabulary_id, rating, *, review_id=None, now=None):
        """Retry with the same review_id to avoid counting a result twice.

        A concurrent, distinct review raises 'stale learning state'; callers can
        reload and retry. Persisted timestamps come from the server/caller clock.
        """
        if rating not in RATINGS:
            raise ValueError('rating must be again, hard, good or easy')
        if review_id is None:
            review_id = str(uuid4())
        if not isinstance(review_id, str) or not review_id.strip() or len(review_id) > 200:
            raise ValueError('invalid review_id')

        async def existing():
            row = await self.statement('SELECT * FROM reviews WHERE id=?', review_id).first()
            result = row_dict(row, REVIEW_COLUMNS)
            if result and (result['vocabulary_id'] != vocabulary_id or result['rating'] != rating):
                raise ValueError('review_id already used for a different result')
            return result

        previous = await existing()
        if previous:
            return previous
        now = int(time.time()) if now is None else now
        state = await self.state(vocabulary_id)
        next_state = schedule(state, rating, now)
        values = (review_id, vocabulary_id, rating, now,
                  state['revision'] if state else 0, next_state['due_at'],
                  next_state['interval_days'], next_state['repetitions'], next_state['lapses'])
        try:
            row = await self.statement(
                'INSERT INTO reviews (' + ','.join(REVIEW_COLUMNS) + ') '
                'VALUES (?,?,?,?,?,?,?,?,?) RETURNING *', *values).first()
        except Exception:
            # Another request with the same ID may have committed meanwhile.
            previous = await existing()
            if previous:
                return previous
            raise
        return row_dict(row, REVIEW_COLUMNS)

    async def history(self, vocabulary_id, *, limit=50):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('limit must be between 1 and 100')
        result = await self.statement(
            'SELECT * FROM reviews WHERE vocabulary_id=? '
            'ORDER BY reviewed_at DESC,previous_revision DESC LIMIT ?', vocabulary_id, limit).all()
        return [row_dict(row, REVIEW_COLUMNS) for row in result.results]
