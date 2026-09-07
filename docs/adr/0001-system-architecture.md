# ADR 0001: Modular grounded-assistant architecture

## Status

Accepted for the MVP.

## Decision

ManakSetu AI uses a React/Vite client and a Django REST API. PostgreSQL is the
system of record and Qdrant is the production vector index. Development can use
SQLite and deterministic lexical retrieval, so contributors can run and test
the complete product without cloud credentials.

AI and verification providers sit behind service interfaces. Views validate
transport data only; orchestration lives in `core/services`. Every generated
claim must be traceable to retrieved `DocumentChunk` records. Failed generation
returns a cited deterministic summary or an explicit abstention—never an
uncited model answer.

Demo fixtures are labelled at the record and response level. A future official
BIS connector can replace the verification adapter without changing API or UI.

## Consequences

- Local demos are reproducible and do not need Gemini or Qdrant.
- Live Gemini and Qdrant remain configuration-only upgrades.
- Citation validation and immutable document versions add a little storage, but
  make answers auditable.

