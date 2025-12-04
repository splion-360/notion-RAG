CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    name TEXT, 
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_users_email ON users(email);
ALTER TABLE users ENABLE ROW LEVEL SECURITY;


-- allow users to read their own data
CREATE POLICY "Users can view their own profile"
    ON users
    FOR SELECT
    USING (auth.uid() = id);

-- allow users to insert their own data
CREATE POLICY "Users can create their own profile"
    ON users
    FOR INSERT
    WITH CHECK (auth.uid() = id);

-- allow users to update their own data
CREATE POLICY "Users can update their own profile"
    ON users
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- allow users to delete their own data
CREATE POLICY "Users can delete their own profile"
    ON users
    FOR DELETE
    USING (auth.uid() = id);


CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_timestamp
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();
