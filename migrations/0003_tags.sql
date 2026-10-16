CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK (length(name) BETWEEN 1 AND 80)
);

CREATE TABLE vocabulary_tags (
    vocabulary_id INTEGER NOT NULL REFERENCES vocabulary(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (vocabulary_id, tag_id)
);
CREATE INDEX vocabulary_tags_by_tag ON vocabulary_tags(tag_id, vocabulary_id);
