CREATE OR REPLACE FUNCTION search_chunks(
    query_embedding vector(768),
    match_count int DEFAULT 5,
    filter_user_id uuid DEFAULT NULL
)
RETURNS TABLE (
    chunk_id uuid,
    chunk_content text,
    chunk_index int,
    page_id uuid,
    page_title text,
    page_url text,
    page_notion_id text,
    similarity_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pc.id as chunk_id,
        pc.content as chunk_content,
        pc.chunk_index,
        np.id as page_id,
        np.title as page_title,
        np.url as page_url,
        np.notion_page_id as page_notion_id,
        1 - (pc.embedding <=> query_embedding) as similarity_score
    FROM page_chunks pc
    INNER JOIN notion_pages np ON pc.page_id = np.id
    INNER JOIN integrations i ON np.integration_id = i.id
    WHERE (filter_user_id IS NULL OR i.user_id = filter_user_id)
    ORDER BY pc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
