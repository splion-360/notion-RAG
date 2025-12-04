CREATE TABLE notion_pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_id UUID NOT NULL REFERENCES integrations(id) ON DELETE CASCADE,
    notion_page_id TEXT NOT NULL,
    title TEXT,
    url TEXT,
    last_edited_time TIMESTAMPTZ,
    last_synced_at TIMESTAMPTZ,
    UNIQUE (integration_id, notion_page_id)
);

CREATE INDEX idx_notion_pages_integration ON notion_pages(integration_id);
CREATE INDEX idx_notion_pages_last_edited ON notion_pages(last_edited_time);

CREATE TABLE page_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    page_id UUID NOT NULL REFERENCES notion_pages(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    token_count INT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_page_chunks_page ON page_chunks(page_id);
CREATE INDEX idx_page_chunks_embedding ON page_chunks USING ivfflat (embedding vector_cosine_ops);

CREATE TRIGGER update_page_chunks_timestamp
    BEFORE UPDATE ON page_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();
