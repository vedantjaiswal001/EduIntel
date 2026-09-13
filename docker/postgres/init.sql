-- Ensure the pgvector extension is available on first database init.
-- (The pgvector/pgvector image ships the extension; this enables it.)
CREATE EXTENSION IF NOT EXISTS vector;
