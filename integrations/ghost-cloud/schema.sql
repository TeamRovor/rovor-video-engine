-- Runtime execution ledger only; canonical ownership remains coordination/tasks.json.
CREATE TABLE IF NOT EXISTS ghost_cloud_control (id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL DEFAULT 0);
INSERT OR IGNORE INTO ghost_cloud_control(id,enabled) VALUES(1,0);
CREATE TABLE IF NOT EXISTS ghost_cloud_jobs (
 id TEXT PRIMARY KEY, employee TEXT NOT NULL, task_id TEXT NOT NULL,
 kind TEXT NOT NULL, title TEXT NOT NULL, prompt TEXT NOT NULL,
 input_bytes INTEGER NOT NULL, source_commit TEXT NOT NULL, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS ghost_cloud_attempts (
 id TEXT PRIMARY KEY, job_id TEXT NOT NULL UNIQUE REFERENCES ghost_cloud_jobs(id),
 provider TEXT NOT NULL, model TEXT NOT NULL, pool TEXT NOT NULL,
 started_at INTEGER NOT NULL, finished_at INTEGER, reserved_tokens INTEGER NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('running','needs_review','failed','uncertain')),
 error_code TEXT, actual_model TEXT, tokens_input INTEGER, tokens_output INTEGER,
 output TEXT, retry_after INTEGER,
 human_review TEXT NOT NULL DEFAULT 'not_recorded'
);
CREATE INDEX IF NOT EXISTS ghost_cloud_attempts_time ON ghost_cloud_attempts(started_at);
CREATE INDEX IF NOT EXISTS ghost_cloud_attempts_pool ON ghost_cloud_attempts(pool,started_at);
