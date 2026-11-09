CREATE TABLE IF NOT EXISTS hud_latest (
  period TEXT PRIMARY KEY,
  observed_at INTEGER NOT NULL,
  received_at INTEGER NOT NULL,
  body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hud_history (
  minute INTEGER PRIMARY KEY,
  observed_at INTEGER NOT NULL,
  received_at INTEGER NOT NULL,
  body TEXT NOT NULL
);

-- Private outbound OmniRoute chat. Prompts/results are temporary, not public task receipts.
CREATE TABLE IF NOT EXISTS hud_chat_bridge (
  id INTEGER PRIMARY KEY CHECK(id = 1),
  updated_at INTEGER NOT NULL,
  models TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hud_chat_jobs (
  id TEXT PRIMARY KEY,
  state TEXT NOT NULL CHECK(state IN ('queued','running','complete','failed')),
  model TEXT NOT NULL,
  request_body TEXT,
  created_at INTEGER NOT NULL,
  started_at INTEGER,
  finished_at INTEGER,
  output TEXT,
  error TEXT
);
CREATE INDEX IF NOT EXISTS hud_chat_jobs_queue ON hud_chat_jobs(state, created_at);

-- Cloud Gemini direct API admission/receipts. No prompts or model output stored.
-- Immutable attempts within day/minute buckets enforce a conservative free usage cap.
CREATE TABLE IF NOT EXISTS hud_gemini_chat_budget (
  bucket TEXT PRIMARY KEY,
  attempts INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS hud_gemini_chat_usage (
  day TEXT PRIMARY KEY,
  completed INTEGER NOT NULL DEFAULT 0,
  input_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0
);
