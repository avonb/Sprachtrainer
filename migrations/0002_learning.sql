-- Personal vocabulary collection. Timestamps are UTC Unix seconds.
ALTER TABLE vocabulary ADD COLUMN transliteration TEXT NOT NULL DEFAULT '';
ALTER TABLE vocabulary ADD COLUMN example_persian TEXT NOT NULL DEFAULT '';
ALTER TABLE vocabulary ADD COLUMN example_german TEXT NOT NULL DEFAULT '';
ALTER TABLE vocabulary ADD COLUMN notes TEXT NOT NULL DEFAULT '';
ALTER TABLE vocabulary ADD COLUMN created_at INTEGER NOT NULL DEFAULT 0;
ALTER TABLE vocabulary ADD COLUMN updated_at INTEGER NOT NULL DEFAULT 0;
ALTER TABLE vocabulary ADD COLUMN archived_at INTEGER;
UPDATE vocabulary SET created_at = unixepoch(), updated_at = unixepoch();

CREATE TABLE learning_state (
    vocabulary_id INTEGER PRIMARY KEY REFERENCES vocabulary(id),
    due_at INTEGER NOT NULL,
    interval_days INTEGER NOT NULL CHECK (interval_days >= 0),
    repetitions INTEGER NOT NULL CHECK (repetitions >= 0),
    lapses INTEGER NOT NULL CHECK (lapses >= 0),
    last_reviewed_at INTEGER NOT NULL,
    revision INTEGER NOT NULL CHECK (revision > 0)
);
CREATE INDEX learning_state_due ON learning_state(due_at);

CREATE TABLE reviews (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(id) > 0),
    vocabulary_id INTEGER NOT NULL REFERENCES vocabulary(id),
    rating TEXT NOT NULL CHECK (rating IN ('again', 'hard', 'good', 'easy')),
    reviewed_at INTEGER NOT NULL,
    previous_revision INTEGER NOT NULL CHECK (previous_revision >= 0),
    due_at INTEGER NOT NULL CHECK (due_at > reviewed_at),
    interval_days INTEGER NOT NULL CHECK (interval_days >= 0),
    repetitions INTEGER NOT NULL CHECK (repetitions >= 0),
    lapses INTEGER NOT NULL CHECK (lapses >= 0)
);
CREATE INDEX reviews_vocabulary_time ON reviews(vocabulary_id, reviewed_at);

-- Check and update in the same INSERT transaction: concurrent reviews cannot
-- overwrite each other, and a failed write cannot leave half a review behind.
CREATE TRIGGER reviews_validate BEFORE INSERT ON reviews BEGIN
    SELECT RAISE(ABORT, 'vocabulary missing or archived')
    WHERE NOT EXISTS (
        SELECT 1 FROM vocabulary WHERE id = NEW.vocabulary_id AND archived_at IS NULL
    );
    SELECT RAISE(ABORT, 'stale learning state')
    WHERE NEW.previous_revision != COALESCE((
        SELECT revision FROM learning_state WHERE vocabulary_id = NEW.vocabulary_id
    ), 0);
    SELECT RAISE(ABORT, 'review predates previous review')
    WHERE NEW.reviewed_at < COALESCE((
        SELECT last_reviewed_at FROM learning_state WHERE vocabulary_id = NEW.vocabulary_id
    ), NEW.reviewed_at);
END;

CREATE TRIGGER reviews_update_state AFTER INSERT ON reviews BEGIN
    INSERT INTO learning_state (
        vocabulary_id, due_at, interval_days, repetitions, lapses,
        last_reviewed_at, revision
    ) VALUES (
        NEW.vocabulary_id, NEW.due_at, NEW.interval_days, NEW.repetitions,
        NEW.lapses, NEW.reviewed_at, NEW.previous_revision + 1
    ) ON CONFLICT(vocabulary_id) DO UPDATE SET
        due_at = excluded.due_at,
        interval_days = excluded.interval_days,
        repetitions = excluded.repetitions,
        lapses = excluded.lapses,
        last_reviewed_at = excluded.last_reviewed_at,
        revision = excluded.revision;
END;
