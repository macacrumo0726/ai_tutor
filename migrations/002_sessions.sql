-- Persistent bearer-session metadata. The raw token is never stored.
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sessions_token
    ON sessions(token_hash, revoked, expires_at);

CREATE INDEX IF NOT EXISTS idx_sessions_user
    ON sessions(user_id, expires_at);
