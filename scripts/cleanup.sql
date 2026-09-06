-- Phase 1: Clean bloated execution data safely
-- Mark orphaned/stale executions (from crashed/restarted workers) as crashed
UPDATE execution_entity
SET status = 'crashed', "stoppedAt" = NOW()
WHERE status IN ('running', 'waiting', 'new')
  AND "startedAt" < NOW() - INTERVAL '24 hours';

-- Delete old execution_data rows (the 577 MB bloat)
DELETE FROM execution_data WHERE "executionId" IN (
  SELECT id FROM execution_entity WHERE "startedAt" < NOW() - INTERVAL '3 days'
);

-- Delete old execution_entity rows
DELETE FROM execution_entity WHERE "startedAt" < NOW() - INTERVAL '3 days';

-- Reclaim disk space
VACUUM FULL execution_data;
VACUUM FULL execution_entity;

-- Report final sizes
SELECT pg_size_pretty(pg_database_size('n8n')) AS db_size;
SELECT relname, pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND relname IN ('execution_data', 'execution_entity', 'n8n_chat_histories')
ORDER BY pg_total_relation_size(c.oid) DESC;
