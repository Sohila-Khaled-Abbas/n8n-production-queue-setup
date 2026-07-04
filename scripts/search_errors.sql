SELECT elem FROM json_array_elements((SELECT data::json FROM execution_data WHERE "executionId" = 2308)) elem WHERE elem->>'message' IS NOT NULL OR elem->>'error' IS NOT NULL;
