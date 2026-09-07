# ManakSetu AI

**Indian Standards, made understandable.** A production-oriented MVP for
grounded standards discovery, certification guidance and consumer assurance.

> ManakSetu AI is an independent demonstration and is not affiliated with or
> endorsed by the Bureau of Indian Standards. Seeded standards and verification
> records are labelled demo fixtures; always confirm current information through
> official BIS channels.

## What works

- Audience-aware Industry and Consumer onboarding
- Grounded English/Hindi chat with intent detection, abstention and citation drawer
- Product-to-standard recommendations with confidence and applicability disclaimer
- Mock licence/registration verification (`CM/L-1234567890`, `R-98765432`)
- Data-driven five-stage product-certification guide and persistent checklists
- Consumer mark, safety and complaint entry points with demo-alert labelling
- Django admin, OpenAPI UI, ingestion/evaluation commands and provider adapters
- Responsive, keyboard-friendly UI with reduced-motion support

## Architecture

```mermaid
flowchart LR
  U[React + TypeScript UI] -->|REST| A[Django REST API]
  A --> O[RAG orchestrator]
  O --> R[Hybrid retriever]
  R --> P[(PostgreSQL metadata)]
  R -. production .-> Q[(Qdrant vectors)]
  O --> G[Gemini adapter]
  G -. no key .-> M[Deterministic mock]
  O --> C[Citation validator]
  C --> A
  A --> U
```

The transport layer contains no provider calls. `GeminiProvider`, embedding,
retrieval, vector store and verification are replaceable service adapters.
See [ADR 0001](docs/adr/0001-system-architecture.md).

## Quick start (local, no cloud key)

Python 3.11–3.14 and Node 20+ are recommended.

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py seed_demo_data
python backend/manage.py runserver
```

In a second terminal:

```bash
npm install --prefix frontend
npm run dev --prefix frontend
```

Open `http://localhost:5173`. API docs are at
`http://localhost:8000/api/docs/`; Django admin is at `/admin/`.

## PostgreSQL and Qdrant

Docker Compose provisions PostgreSQL 16, Qdrant, the API and the built UI:

```bash
cp .env.example .env
docker compose up -d postgres qdrant
```

Set `DATABASE_URL=postgresql://manaksetu:manaksetu@localhost:5432/manaksetu`.
The local retriever remains the default (`VECTOR_PROVIDER=local`) for a zero-key
demo. The Qdrant adapter is available for production indexing; configure
`QDRANT_URL` and `QDRANT_COLLECTION` before enabling it.

## Gemini

The API key is server-only. Never use a `VITE_` variable for it.

```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=your-server-side-key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

Without a key, the deterministic mock provider produces a concise summary from
the strongest retrieved chunk. The live adapter requests structured JSON,
retries with exponential backoff, rejects citations outside the retrieval set,
and falls back to a grounded local summary or abstention—not an uncited answer.

## Ingestion

Controlled ingestion accepts PDF, HTML, Markdown, text, CSV, JSON and JSONL,
with a 10 MB default limit. Metadata fields include document/version identifiers,
title, standard number, language, category, source type and URL.

```bash
python backend/manage.py ingest_sources --path data/samples
```

Demo records are intentionally summaries; restricted BIS documents are neither
scraped nor redistributed. For real deployment, ingest only material for which
you have permission, preserve source URLs/publication metadata and version every
source immutably.

## Tests and evaluation

```bash
cd backend && ../.venv/bin/pytest -q
cd ../frontend && npm test && npm run lint && npm run build
cd ../backend && ../.venv/bin/python manage.py evaluate_rag --dataset ../data/evaluation/questions.jsonl
```

Evaluation reports retrieval hit rate, citation validity and abstention
correctness to `backend/evaluation-report.md`. The included dataset has English
and Hindi industry/consumer questions and runs without Gemini.

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/chat/sessions/` | Create guest or saved session |
| POST | `/api/chat/sessions/{id}/messages/` | Grounded answer |
| GET/DELETE | `/api/chat/sessions/{id}/` | Load or delete chat |
| POST | `/api/standards/search/` | Exact/text search |
| POST | `/api/standards/recommend/` | Product recommendation |
| POST | `/api/verification/check/` | Provider-neutral lookup |
| GET | `/api/guides/`, `/api/guides/{slug}/` | Application journey |
| POST | `/api/feedback/` | Answer feedback |
| GET | `/api/health/` | Dependency/config state |

Errors use a consistent `{error: {code, message}, request_id}` envelope. Chat has
a burst throttle and global anonymous/user rate limits. Production deployments
must set a strong secret, disable debug, restrict hosts/CORS, terminate TLS and
replace guest ownership rules with organization-level authorization.

## Demo walkthrough

1. Choose **Industry**, open **Ask the assistant**, and ask “Which standard
   applies to an electric kettle?”
2. Observe retrieval status, cited answer, evidence match and the source drawer.
3. Open **Standards finder**, submit the prefilled kettle description and review
   `IS 367:1993` with its scope and applicability disclaimer.
4. Open **Verify**, submit `CM/L-1234567890`, and inspect the green result plus
   prominent mock/not-official notice. Try `R-98765432` for an expired state.
5. Switch to हिन्दी from the header and ask a Hindi question.
6. Open **Application guide** and progress through its checklist.

## Repository map

```text
backend/   Django API, models, admin, adapters, commands and tests
frontend/  React/Vite experience, translation dictionary and tests
data/      Demo sources and evaluation questions
docs/      Architecture decisions and project documentation
infra/     Reserved for deployment-specific manifests
```

## Known limitations

- Supplied standard records are user-provided demo summaries, not a complete or
  current BIS corpus.
- Verification is seeded mock data; no official BIS verification API is connected.
- The browser shows a retrieval/typing state, while true token-by-token SSE is a
  documented next deployment enhancement.
- Local retrieval is deterministic lexical hybrid search. Qdrant and Gemini
  adapters are present, but production indexing requires a running service and key.
- Hindi UI coverage focuses on primary navigation and core actions; remaining
  explanatory content should be translated before public launch.

