"""Opt-in integration check: creates and removes one word in configured dev D1.

Run from the repository root with Cloudflare credentials:
    python scripts/check_d1.py
"""

import asyncio
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from urllib.request import Request, urlopen
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.learning import VocabularyStore  # noqa: E402


class Statement:
    def __init__(self, db, sql):
        self.db, self.sql, self.args = db, sql, ()

    def bind(self, *args):
        self.args = args
        return self

    async def all(self):
        request = Request(self.db.url, method='POST',
                          data=json.dumps({'sql': self.sql, 'params': self.args}).encode(),
                          headers={'Authorization': 'Bearer ' + os.environ['CLOUDFLARE_API_TOKEN'],
                                   'Content-Type': 'application/json'})
        with urlopen(request, timeout=30) as response:
            data = json.load(response)
        if not data['success']:
            raise RuntimeError('D1 query failed')
        return SimpleNamespace(results=[SimpleNamespace(**row)
                                        for row in data['result'][0]['results']])

    async def first(self):
        result = await self.all()
        return result.results[0] if result.results else None

    async def run(self):
        return await self.all()


class Database:
    def __init__(self):
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / 'wrangler.jsonc').read_text())
        database_id = config['d1_databases'][0]['database_id']
        account = os.environ['CLOUDFLARE_ACCOUNT_ID']
        self.url = f'https://api.cloudflare.com/client/v4/accounts/{account}/d1/database/{database_id}/query'

    def prepare(self, sql):
        return Statement(self, sql)


async def main():
    db = Database()
    store = VocabularyStore(db)
    word = await store.save(persian='کتاب', german='Buch', transliteration='ketāb',
                            notes='Temporary integration check; deleted afterwards')
    tag = 'integration-' + str(uuid4())
    try:
        assert await store.add_tag(word['id'], tag.upper()) == [tag]
        assert (await store.get(word['id']))['tags'] == [tag]
        assert (await store.get(word['id']))['persian'] == 'کتاب'
        review = await store.review(word['id'], 'good')
        assert await store.review(word['id'], 'good', review_id=review['id']) == review
        assert (await VocabularyStore(db).state(word['id']))['revision'] == 1
        assert any(row['id'] == word['id'] for row in await store.due(now=review['due_at'], tag=tag))
        assert len(await store.history(word['id'])) == 1
        await store.archive(word['id'])
        assert not any(row['id'] == word['id'] for row in await store.due(now=review['due_at']))
        assert await store.remove_tag(word['id'], tag) == []
        print('OK: remote D1 vocabulary, tags, persistent review, retry, due list and archive')
    finally:
        for table in ('reviews', 'learning_state'):
            await db.prepare(f'DELETE FROM {table} WHERE vocabulary_id=?').bind(word['id']).all()
        await db.prepare('DELETE FROM vocabulary WHERE id=?').bind(word['id']).all()
        await db.prepare('DELETE FROM tags WHERE name=?').bind(tag).all()
        print('Temporary check data removed')


if __name__ == '__main__':
    asyncio.run(main())
