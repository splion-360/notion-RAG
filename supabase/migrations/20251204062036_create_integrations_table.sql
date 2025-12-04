CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    app_id TEXT NOT NULL,
    app_name TEXT NOT NULL,
    account_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE UNIQUE INDEX idx_integrations_user_app_account ON integrations(user_id, app_id, account_id);
CREATE INDEX idx_integrations_user ON integrations(user_id);

ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;


-- allow users to read their own data
CREATE POLICY "Users can view their own integrations"
    ON integrations
    FOR SELECT
    USING (auth.uid() = user_id);

-- allow users to insert their own data
CREATE POLICY "Users can create their own integrations"
    ON integrations
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- allow users to update their own data
CREATE POLICY "Users can update their own integrations"
    ON integrations
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- allow users to delete their own data
CREATE POLICY "Users can delete their own integrations"
    ON integrations
    FOR DELETE
    USING (auth.uid() = user_id);


CREATE TRIGGER update_integrations_timestamp
    BEFORE UPDATE ON integrations
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();
