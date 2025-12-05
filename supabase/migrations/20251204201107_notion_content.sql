CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


CREATE TABLE notion_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    integration_id UUID NOT NULL REFERENCES integrations(id) ON DELETE CASCADE,
    notion_page_id TEXT NOT NULL,
    title TEXT,
    url TEXT,
    content TEXT,
    media_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE (integration_id, notion_page_id)
);

CREATE INDEX idx_notion_pages_integration ON notion_pages(integration_id);

CREATE TRIGGER update_notion_pages_timestamp
    BEFORE UPDATE ON notion_pages
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TABLE page_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID NOT NULL REFERENCES notion_pages(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_page_chunks_page ON page_chunks(page_id);

CREATE TRIGGER update_page_chunks_timestamp
    BEFORE UPDATE ON page_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Enable Row Level Security
ALTER TABLE notion_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE page_chunks ENABLE ROW LEVEL SECURITY;


CREATE POLICY "Users can view their own notion pages"
ON notion_pages FOR SELECT
USING (
  integration_id IN (
    SELECT id FROM integrations WHERE user_id = auth.uid()
  )
);

CREATE POLICY "Users can insert their own notion pages"
ON notion_pages FOR INSERT
WITH CHECK (
  integration_id IN (
    SELECT id FROM integrations WHERE user_id = auth.uid()
  )
);

CREATE POLICY "Users can update their own notion pages"
ON notion_pages FOR UPDATE
USING (
  integration_id IN (
    SELECT id FROM integrations WHERE user_id = auth.uid()
  )
);

CREATE POLICY "Users can delete their own notion pages"
ON notion_pages FOR DELETE
USING (
  integration_id IN (
    SELECT id FROM integrations WHERE user_id = auth.uid()
  )
);

-- RLS Policies for page_chunks
CREATE POLICY "Users can view their own page chunks"
ON page_chunks FOR SELECT
USING (
  page_id IN (
    SELECT id FROM notion_pages WHERE integration_id IN (
      SELECT id FROM integrations WHERE user_id = auth.uid()
    )
  )
);

CREATE POLICY "Users can insert their own page chunks"
ON page_chunks FOR INSERT
WITH CHECK (
  page_id IN (
    SELECT id FROM notion_pages WHERE integration_id IN (
      SELECT id FROM integrations WHERE user_id = auth.uid()
    )
  )
);

CREATE POLICY "Users can update their own page chunks"
ON page_chunks FOR UPDATE
USING (
  page_id IN (
    SELECT id FROM notion_pages WHERE integration_id IN (
      SELECT id FROM integrations WHERE user_id = auth.uid()
    )
  )
);

CREATE POLICY "Users can delete their own page chunks"
ON page_chunks FOR DELETE
USING (
  page_id IN (
    SELECT id FROM notion_pages WHERE integration_id IN (
      SELECT id FROM integrations WHERE user_id = auth.uid()
    )
  )
);
