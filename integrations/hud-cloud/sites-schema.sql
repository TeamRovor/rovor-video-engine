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
