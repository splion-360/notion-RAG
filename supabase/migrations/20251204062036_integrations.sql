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

CREATE TRIGGER update_integrations_timestamp
    BEFORE UPDATE ON integrations
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();
