-- FORWARD-ONLY, optional owner-private Site D1 migration.
-- Never modify an applied migration or mix with the existing Groq RPD table.
-- Derived from authenticated Mistral inference response headers only;
-- no prompts, raw credentials, pricing or fabricated reset times are stored.
CREATE TABLE IF NOT EXISTS ghost_cloud_mistral_minute_quota (
 model TEXT NOT NULL CHECK(length(model) BETWEEN 1 AND 200),
 unit TEXT NOT NULL CHECK(unit IN ('tokens','requests')),
 observed_at INTEGER NOT NULL CHECK(observed_at>0),
 used INTEGER NOT NULL CHECK(used>=0),
 quota_limit INTEGER NOT NULL CHECK(quota_limit>0),
 remaining INTEGER NOT NULL CHECK(remaining>=0 AND remaining<=quota_limit AND used=quota_limit-remaining),
 source TEXT NOT NULL CHECK(source='authenticated_mistral_inference_minute_headers'),
 PRIMARY KEY(model,unit)
);
