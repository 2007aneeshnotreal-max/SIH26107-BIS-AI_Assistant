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

The supplied `data/sources/BIS_Prototype_and_Reference_521_Records.jsonl` uses a
nested schema. The importer recognizes its `record_type`, uses `record_id` as
the document identifier, and splits standards, certification, consumer and
provenance fields into bounded passages. Original JSON is retained in the source
document. Each passage repeats its product, standard and provenance label and
stores the original provenance and PDF location in chunk metadata. PDF locations
refer to the original combined PDF, not pages of the linked reference preview.

The 500 synthetic records use `source_type=demo`. The 21 earlier reference
summaries use `source_type=user`, since the import does not revalidate them.
Synthetic placeholder URLs are retained as data, not exposed as citation links.
The retriever reads the database directly, so a completed import is immediately
available to chat without a separate embedding job or provider fine-tuning job.

Reimporting identical content is a no-op for existing documents and chunks.
Changes to an existing document/version are rejected; increment the record's
`version` to preserve historical citation targets.
