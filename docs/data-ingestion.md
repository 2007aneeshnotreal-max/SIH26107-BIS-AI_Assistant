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

## BIS RAG Dataset ZIP

The supplied BIS India RAG Dataset v2 archive is a retrieval corpus, not a
neural-model training file. Load it with:

```bash
python backend/manage.py ingest_bis_dataset --path path/to/data.zip
```

This imports the 1,088 product regulatory records and the supplied source
chunks into labelled `SourceDocument` and `DocumentChunk` records. Product
records also populate `StandardRecord` where an IS number is available. The
archive is treated as user-provided demo evidence; current QCO status, fees,
certification schemes, licence state, and laboratory scope remain claims that
must be verified against current official sources.

## Citation document ZIP

The supplied citation archive contains BIS PDFs and DOCX files for fees,
certification, applications, hallmarking, laboratories, and related guidance.
Import it with:

```bash
python backend/manage.py ingest_citation_dataset --path path/to/citation-data.zip
```

PDF page numbers are retained in `DocumentChunk.page`, so assistant citations
can identify the source file and page. Documents remain labelled as
user-provided evidence and are not treated as automatic legal authority.

