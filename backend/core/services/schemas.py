"""Provider-neutral structured-output contracts used by AI adapters."""
INTENT_SCHEMA={"type":"object","properties":{"intent":{"type":"string"},"confidence":{"type":"number"}},"required":["intent","confidence"]}
QUERY_REWRITE_SCHEMA={"type":"object","properties":{"query":{"type":"string"},"filters":{"type":"object"}},"required":["query","filters"]}
ANSWER_SCHEMA={"type":"object","properties":{"answer":{"type":"string"},"confidence":{"type":"number"},"citations":{"type":"array","items":{"type":"string"}},"next_steps":{"type":"array","items":{"type":"string"}},"abstain":{"type":"boolean"}},"required":["answer","confidence","citations","next_steps","abstain"]}
RECOMMENDATION_SCHEMA={"type":"object","properties":{"candidates":{"type":"array","items":{"type":"object","properties":{"standard_number":{"type":"string"},"reason":{"type":"string"},"confidence":{"type":"number"},"citation_ids":{"type":"array","items":{"type":"string"}}},"required":["standard_number","reason","confidence","citation_ids"]}}},"required":["candidates"]}
GUIDE_SCHEMA={"type":"object","properties":{"steps":{"type":"array","items":{"type":"object","properties":{"title":{"type":"string"},"description":{"type":"string"},"checklist":{"type":"array","items":{"type":"string"}}},"required":["title","description","checklist"]}}},"required":["steps"]}
TRANSLATION_SCHEMA={"type":"object","properties":{"translated_text":{"type":"string"},"preserved_identifiers":{"type":"array","items":{"type":"string"}}},"required":["translated_text","preserved_identifiers"]}
GROUNDING_SCHEMA={"type":"object","properties":{"grounded":{"type":"boolean"},"unsupported_claims":{"type":"array","items":{"type":"string"}},"safe":{"type":"boolean"}},"required":["grounded","unsupported_claims","safe"]}

