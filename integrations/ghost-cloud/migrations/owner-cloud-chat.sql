-- Forward-only migration for the EXISTING owner-private ROVOR Site D1 binding.
-- This table is separate from the immutable worker job/review ledger.
-- Apply through the existing Site migration journal before publishing the
-- cloud-only Ask ROVOR bundle. Do not modify a previously applied migration.
CREATE TABLE IF NOT EXISTS ghost_cloud_owner_chat (
 id TEXT PRIMARY KEY, actor TEXT NOT NULL, provider TEXT NOT NULL,
 model TEXT NOT NULL, pool TEXT NOT NULL, started_at INTEGER NOT NULL,
 finished_at INTEGER, reserved_tokens INTEGER NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('running','complete','failed','uncertain')),
 error_code TEXT, actual_model TEXT, tokens_input INTEGER, tokens_output INTEGER,
 output TEXT, retry_after INTEGER
);
CREATE INDEX IF NOT EXISTS ghost_cloud_owner_chat_pool ON ghost_cloud_owner_chat(pool,started_at);
