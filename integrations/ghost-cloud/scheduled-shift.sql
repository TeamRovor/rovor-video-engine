-- Append as a NEW schema-only migration to the existing private ROVOR Site D1.
-- Not installed merely by merging this file. Do not rewrite an applied migration.
CREATE TABLE IF NOT EXISTS ghost_cloud_shift_runs (
  id TEXT PRIMARY KEY,
  started_at INTEGER NOT NULL,
  finished_at INTEGER,
  status TEXT NOT NULL CHECK(status IN ('running','idle','stopped','dispatched','failed')),
  queued INTEGER NOT NULL DEFAULT 0,
  duplicates INTEGER NOT NULL DEFAULT 0,
  dispatched INTEGER NOT NULL DEFAULT 0,
  reason TEXT
);
CREATE INDEX IF NOT EXISTS ghost_cloud_shift_runs_time ON ghost_cloud_shift_runs(started_at);
