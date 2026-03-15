"""Supabase client singleton and required table DDL reference.

Required Supabase tables (run in Supabase SQL editor):
-------------------------------------------------------

-- Enable pgvector extension first:
-- CREATE EXTENSION IF NOT EXISTS vector;

-- research_sessions
CREATE TABLE IF NOT EXISTS research_sessions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         text,
    topic           text,
    depth           text,
    status          text DEFAULT 'running',   -- 'running' | 'complete' | 'failed'
    logs            jsonb DEFAULT '[]',
    final_report    jsonb,
    sources         jsonb DEFAULT '[]',
    overall_confidence float,
    is_complete     bool DEFAULT false,
    user_override   text,
    token_usage     int DEFAULT 0,
    created_at      timestamptz DEFAULT now(),
    deleted_at      timestamptz
);

-- research_chunks  (pgvector, dim=384 for all-MiniLM-L6-v2)
CREATE TABLE IF NOT EXISTS research_chunks (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id     uuid REFERENCES research_sessions(id),
    content         text,
    embedding       vector(384),
    metadata        jsonb,
    created_at      timestamptz DEFAULT now()
);

-- Cosine-similarity index
CREATE INDEX IF NOT EXISTS research_chunks_embedding_idx
    ON research_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Supabase RPC for similarity search (run in SQL editor):
CREATE OR REPLACE FUNCTION match_research_chunks(
    query_embedding vector(384),
    match_research_id uuid,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id uuid,
    content text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        rc.id,
        rc.content,
        rc.metadata,
        1 - (rc.embedding <=> query_embedding) AS similarity
    FROM research_chunks rc
    WHERE rc.research_id = match_research_id
    ORDER BY rc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""

from supabase import create_client, Client
from core.config import settings


def get_supabase_client() -> Client:
    """Return an authenticated Supabase client using the service role key."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


# Module-level singleton used throughout the app.
supabase: Client = get_supabase_client()
