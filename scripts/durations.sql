SELECT id, status, mode, "workflowId", ("stoppedAt" - "startedAt") as duration FROM execution_entity ORDER BY "startedAt" DESC LIMIT 15;
