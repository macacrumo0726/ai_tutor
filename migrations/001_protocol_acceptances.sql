-- Protocol acceptance migration for existing SQLite installations.
-- The application also executes this idempotently during repository startup.
CREATE TABLE IF NOT EXISTS protocol_acceptances (
    acceptance_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    protocol_version TEXT NOT NULL,
    accepted INTEGER NOT NULL CHECK(accepted IN (0, 1)),
    accepted_at_utc TEXT NOT NULL,
    UNIQUE(user_id, protocol_version)
);

CREATE INDEX IF NOT EXISTS idx_protocol_acceptances_user_date
    ON protocol_acceptances(user_id, accepted_at_utc DESC);
