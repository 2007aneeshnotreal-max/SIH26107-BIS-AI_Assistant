# Data ingestion guide

Only ingest sources that may legally be processed. Set `source_type` to `demo`,
`official`, or `user`, and provide an immutable `document_id` plus `version`.
Never overwrite an old source version that has citations.

Recommended JSON record:

```json
{"document_id":"PUBLIC-001","version":1,"title":"Document title","standard_number":"IS 0000:2026","language":"en","category":"ETD","source_type":"official","source_url":"https://example.gov.in/source","content":"..."}
```

Run `python backend/manage.py ingest_sources --path path/to/source`. Inspect the
`IngestionRun`, `SourceDocument`, and `DocumentChunk` records in Django admin.

