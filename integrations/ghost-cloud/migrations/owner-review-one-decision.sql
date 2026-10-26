-- Forward-only upgrade for an EXISTING private D1 Site whose review table lacks
-- the attempt uniqueness constraint. First inspect duplicate attempt IDs and
-- halt for explicit owner reconciliation if any exist; this fails closed.
-- Append as a NEW journaled migration. Do not edit applied SQL files.
CREATE UNIQUE INDEX IF NOT EXISTS ghost_cloud_reviews_one_decision_per_attempt
ON ghost_cloud_reviews(attempt_id);
