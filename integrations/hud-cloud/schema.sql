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

-- Read-only Groq catalogue and rate-limit header cache. The model's public
-- presence and headers DO NOT attest a $0 billing plan or permission to infer.
CREATE TABLE IF NOT EXISTS hud_groq_quota_probe (
  id INTEGER PRIMARY KEY CHECK(id=1),
  checked_at INTEGER NOT NULL,
  observed_at INTEGER,
  status TEXT NOT NULL CHECK(status IN ('checking','catalog_received','auth_rejected','rate_limited','upstream_error','invalid_catalog','unavailable')),
  model_present INTEGER CHECK(model_present IN (0,1)),
  rpd_limit INTEGER,
  rpd_remaining INTEGER,
  rpd_reset_at TEXT,
  tpm_limit INTEGER,
  tpm_remaining INTEGER,
  tpm_reset_at TEXT
);

-- Per-Google-model request admission and usage receipts, without prompts, keys,
-- client data or generated output. Additive to the existing project-wide caps.
CREATE TABLE IF NOT EXISTS hud_gemini_chat_model_usage (
  day TEXT NOT NULL,
  model TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  completed INTEGER NOT NULL DEFAULT 0,
  failures INTEGER NOT NULL DEFAULT 0,
  input_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  last_error_code TEXT,
  PRIMARY KEY (day, model)
);

-- Gemini verified-model and provider-429 evidence. Metadata only: no keys,
-- prompts, output, or assumed Google-wide quota. Forward-only and idempotent.
CREATE TABLE IF NOT EXISTS hud_gemini_model_health (
  model TEXT PRIMARY KEY,
  last_success_at INTEGER,
  success_count INTEGER NOT NULL DEFAULT 0,
  last_rate_limited_at INTEGER,
  cooldown_until INTEGER,
  last_failure_at INTEGER,
  last_failure_code TEXT
);

-- Owner-private suggestion intake. It never starts models or GitHub writes.
-- Only human-reviewed canonical queue tasks can become cloud worker jobs.
CREATE TABLE IF NOT EXISTS hud_idea_intake_limits (
  day_id INTEGER PRIMARY KEY,
  submissions INTEGER NOT NULL,
  last_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS hud_idea_inbox (
  id TEXT PRIMARY KEY,
  created_at INTEGER NOT NULL,
  content TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending_review'
    CHECK(state IN ('pending_review')),
  source TEXT NOT NULL CHECK(source IN ('ask_rovor'))
);
CREATE INDEX IF NOT EXISTS hud_idea_inbox_recent
  ON hud_idea_inbox(created_at DESC);

-- Evidence-backed GitHub proposals. One immutable source key per finding,
-- with a durable six-per-UTC-day limit, independent of visible inbox length.
-- Never a provider job or approval. Writer-only admission.
CREATE TABLE IF NOT EXISTS hud_auto_discovery_inbox (
  id TEXT PRIMARY KEY,
  discovery_key TEXT NOT NULL UNIQUE,
  day_id INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  content TEXT NOT NULL,
  priority INTEGER NOT NULL CHECK(priority BETWEEN 1 AND 100),
  state TEXT NOT NULL DEFAULT 'pending_review' CHECK(state IN ('pending_review'))
);
CREATE INDEX IF NOT EXISTS hud_auto_discovery_day
  ON hud_auto_discovery_inbox(day_id);
CREATE INDEX IF NOT EXISTS hud_auto_discovery_recent
  ON hud_auto_discovery_inbox(created_at DESC);


-- Separate Mac-independent, owner-approved Gemini pilot lane. Never shares
-- the ChatGPT Site's private D1 or claims to sync its owner PASS/FAIL ledger.
-- A singleton STOP gate defaults to disabled; no preexisting job replays.
CREATE TABLE IF NOT EXISTS hud_cloud_workforce_control (
 id INTEGER PRIMARY KEY CHECK(id=1),
 enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1))
);
INSERT OR IGNORE INTO hud_cloud_workforce_control(id,enabled) VALUES(1,0);

CREATE TABLE IF NOT EXISTS hud_cloud_workforce_jobs (
 id TEXT PRIMARY KEY,
 task_id TEXT NOT NULL,
 employee TEXT NOT NULL,
 kind TEXT NOT NULL,
 title TEXT NOT NULL,
 prompt TEXT NOT NULL,
 source_commit TEXT NOT NULL,
 revision TEXT NOT NULL,
 created_at INTEGER NOT NULL,
 started_at INTEGER,
 finished_at INTEGER,
 state TEXT NOT NULL DEFAULT 'queued'
  CHECK(state IN ('queued','running','needs_review','failed','uncertain')),
 actual_model TEXT,
 output TEXT,
 output_sha256 TEXT,
 error_code TEXT,
 human_review TEXT NOT NULL DEFAULT 'not_recorded'
  CHECK(human_review IN ('not_recorded','passed','failed')),
 reviewed_at INTEGER,
 CHECK((human_review='not_recorded' AND reviewed_at IS NULL) OR
       (human_review IN ('passed','failed') AND reviewed_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS hud_cloud_workforce_queue
 ON hud_cloud_workforce_jobs(state,created_at,id);
CREATE INDEX IF NOT EXISTS hud_cloud_workforce_attempts
 ON hud_cloud_workforce_jobs(started_at);

-- Explicit, time-limited standing owner authorization for fresh discovery triage.
-- Never inferred from a one-shot pilot. STOP disarms this independently.
CREATE TABLE IF NOT EXISTS hud_cloud_workforce_series (
 id INTEGER PRIMARY KEY CHECK(id=1),
 active INTEGER NOT NULL DEFAULT 0 CHECK(active IN (0,1)),
 source_commit TEXT,
 approved_at INTEGER,
 expires_at INTEGER,
 CHECK(active=0 OR (source_commit IS NOT NULL AND LENGTH(source_commit)=40 AND approved_at IS NOT NULL AND expires_at>approved_at))
);
INSERT OR IGNORE INTO hud_cloud_workforce_series(id,active) VALUES(1,0);

-- Append-only native Cloudflare scheduler observations; independent of manual
-- API ticks and of the private Site ledger. No prompt, output or credential.
CREATE TABLE IF NOT EXISTS hud_cloud_workforce_native_ticks (
 id TEXT PRIMARY KEY,
 scheduled_at INTEGER NOT NULL,
 started_at INTEGER NOT NULL,
 finished_at INTEGER NOT NULL CHECK(finished_at>=started_at),
 result_state TEXT NOT NULL,
 http_status INTEGER NOT NULL,
 dispatch_reported INTEGER NOT NULL CHECK(dispatch_reported IN (0,1)),
 job_id TEXT,
 inference_completed INTEGER NOT NULL CHECK(inference_completed IN (0,1)),
 CHECK(inference_completed=0 OR (dispatch_reported=1 AND job_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS hud_cloud_workforce_native_ticks_recent
 ON hud_cloud_workforce_native_ticks(started_at DESC);

-- Exact token usage belongs to the same immutable workforce output digest.
-- Old completed jobs are not backfilled from aggregate chat usage.
CREATE TABLE IF NOT EXISTS hud_cloud_workforce_usage (
 job_id TEXT PRIMARY KEY REFERENCES hud_cloud_workforce_jobs(id),
 output_sha256 TEXT NOT NULL CHECK(LENGTH(output_sha256)=64),
 provider TEXT NOT NULL CHECK(provider='google-gemini-cloud'),
 requested_model TEXT NOT NULL,
 actual_model TEXT NOT NULL,
 tokens_input INTEGER NOT NULL CHECK(tokens_input>=0),
 tokens_output INTEGER NOT NULL CHECK(tokens_output>=0),
 recorded_at INTEGER NOT NULL
);

-- Latest authenticated completion rate-limit headers, not billing evidence.
CREATE TABLE IF NOT EXISTS hud_groq_completion_quota (
 id INTEGER PRIMARY KEY CHECK(id=1),
 observed_at INTEGER NOT NULL,
 response_status INTEGER NOT NULL CHECK(response_status IN (200,429)),
 rpd_limit INTEGER, rpd_remaining INTEGER, rpd_reset_at TEXT,
 tpm_limit INTEGER, tpm_remaining INTEGER, tpm_reset_at TEXT
);

-- One durable lease and bounded readback for native GitHub discovery.
CREATE TABLE IF NOT EXISTS hud_native_discovery_clock (
 id INTEGER PRIMARY KEY CHECK(id=1),
 started_at INTEGER NOT NULL,
 finished_at INTEGER,
 result_state TEXT NOT NULL,
 discovery_key TEXT
);

-- Separate owner-authorized tool attempts. One immutable model output may
-- become one draft PR; a failed/uncertain write never automatically replays.
CREATE TABLE IF NOT EXISTS hud_github_patch_jobs (
 job_id TEXT PRIMARY KEY REFERENCES hud_cloud_workforce_jobs(id),
 output_sha256 TEXT NOT NULL,base_commit TEXT NOT NULL,path TEXT NOT NULL,branch TEXT NOT NULL UNIQUE,
 authorized_at INTEGER NOT NULL,expires_at INTEGER NOT NULL,started_at INTEGER,finished_at INTEGER,
 state TEXT NOT NULL CHECK(state IN ('queued','running','opened','failed','uncertain')),
 error_code TEXT,commit_sha TEXT,pr_number INTEGER
);
CREATE INDEX IF NOT EXISTS hud_github_patch_queue ON hud_github_patch_jobs(state,authorized_at);
CREATE TABLE IF NOT EXISTS hud_github_patch_events (
 job_id TEXT NOT NULL REFERENCES hud_github_patch_jobs(job_id),
 step TEXT NOT NULL CHECK(step IN ('tree','commit','branch','draft_pr')),
 reference TEXT NOT NULL,recorded_at INTEGER NOT NULL,PRIMARY KEY(job_id,step)
);
