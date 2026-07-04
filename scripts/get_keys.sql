SELECT json_object_keys(((data::json)->0)->'resultData') FROM execution_data WHERE "executionId" = 2354;
