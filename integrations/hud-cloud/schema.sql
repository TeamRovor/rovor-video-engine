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

-- Cloud-only Groq chat; account-key and private prompts are never stored here.
-- Atomic reservations survive Worker restarts and do not require a Mac.
CREATE TABLE IF NOT EXISTS hud_groq_chat_admission (
  id INTEGER PRIMARY KEY CHECK(id=1),
  day_id INTEGER NOT NULL,
  attempts INTEGER NOT NULL,
  last_started_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS hud_groq_chat_receipts (
  id TEXT PRIMARY KEY,
  created_at INTEGER NOT NULL,
  model TEXT NOT NULL,
  prompt_tokens INTEGER NOT NULL,
  completion_tokens INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS hud_groq_chat_receipts_time ON hud_groq_chat_receipts(created_at);
