ALTER TABLE integrations DROP COLUMN IF EXISTS app_id;

DROP INDEX IF EXISTS idx_integrations_user_app_account;
CREATE UNIQUE INDEX idx_integrations_user_account ON integrations(user_id, account_id);


