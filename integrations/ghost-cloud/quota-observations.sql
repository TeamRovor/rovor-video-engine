-- Add as a NEW schema-only migration to the existing owner-private Site D1.
-- Never edit an already applied private migration or place API secrets in D1.
-- Observations are authenticated provider headers, not billing/free-tier proofs.
CREATE TABLE IF NOT EXISTS ghost_cloud_provider_quota (
 provider TEXT PRIMARY KEY CHECK(provider='groq'),
 observed_at INTEGER NOT NULL CHECK(observed_at>0),
 unit TEXT NOT NULL CHECK(unit='requests'),
 used INTEGER NOT NULL CHECK(used>=0),
 quota_limit INTEGER NOT NULL CHECK(quota_limit>0),
 remaining INTEGER NOT NULL CHECK(remaining>=0 AND remaining<=quota_limit),
 resets_at INTEGER NOT NULL CHECK(resets_at>observed_at),
 source TEXT NOT NULL CHECK(source='authenticated_groq_rpd_response_headers')
);
