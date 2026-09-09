# BIS ManakSathi AI — Team & AI Assistant Handoff

This document is the continuation guide for a teammate, Claude, Codex, or any
other coding assistant. Read this file before changing the project.

## Product summary

BIS ManakSathi AI is an independent SIH-oriented prototype for Indian Standards
discovery, certification guidance, product-to-standard matching, product image
analysis, testing guidance, laboratory discovery, and consumer help. It is not
an official BIS service. Never present demo data or an inferred result as an
official certification decision.

## Repository structure

```text
backend/   Django 5 + Django REST Framework API
frontend/  React 19 + TypeScript + Vite interface
data/      Demo standards and evaluation questions
docs/      ADR, API, ingestion and evaluation documentation
infra/     Infrastructure notes
```

Local development currently uses SQLite and the deterministic local retriever.
PostgreSQL and Qdrant configuration is available for later production work.

## Required software

- Python 3.11 or newer (the current machine uses the `.venv` in this repo)
- Node.js 20 or newer and npm
- Optional: Docker Desktop for PostgreSQL and Qdrant
- A Gemini API key for grounded generation and product-image recognition
- A Google OAuth Web Client ID for Google sign-in and saved chat history
- Chrome or Edge is recommended for browser speech recognition

### Exact installation checklist

For the default SQLite development setup, install only:

1. Python 3.11+ with `venv` and `pip`.
2. Node.js 20+ (npm is included with Node.js).
3. Git.
4. Chrome or Edge for the complete microphone/camera experience.

On macOS with Homebrew, a new developer can use:

```bash
brew install python node git
```

Confirm the tools before setup:

```bash
python3 --version
node --version
npm --version
git --version
```

Project packages are installed from the committed dependency manifests; do not
install Django, React, Gemini, or other libraries one-by-one:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
npm install --prefix frontend
```

Python dependencies include Django, Django REST Framework, CORS/OpenAPI support,
PostgreSQL and Qdrant clients, Gemini, PDF/HTML extraction, Gunicorn and pytest.
Frontend dependencies include React, TypeScript, Vite, React Router, Framer
Motion, Lucide icons, Vitest and Testing Library.

Optional production-like infrastructure requires Docker Desktop:

```bash
docker --version
docker compose version
docker compose up -d postgres qdrant
```

Docker/PostgreSQL/Qdrant are not required for the default SQLite + local-retriever
demo. Redis and Celery are not currently required.

### External accounts and browser permissions

- Gemini API key: required for live Gemini answers and actual image recognition.
  The mock provider works without it but cannot understand arbitrary photos.
- Google Cloud OAuth Web Client: required for Google login and account-backed
  history. Use the same public client ID in backend and frontend environment
  variables. Do not put the client secret in this project.
- Browser location permission: required only for the nearby-laboratory action.
- Browser microphone permission: required for voice questions.
- Browser camera permission: required only when Open camera is selected.

## Environment configuration

Copy the template if `.env` does not exist:

```bash
cp .env.example .env
```

Important values:

```dotenv
DJANGO_SECRET_KEY=<long-random-server-secret>
DJANGO_DEBUG=true
DATABASE_URL=sqlite:///db.sqlite3
AI_PROVIDER=gemini
GEMINI_API_KEY=<server-side-key>
GEMINI_MODEL=gemini-2.5-flash
GOOGLE_CLIENT_ID=<google-oauth-web-client-id>
VITE_GOOGLE_CLIENT_ID=<same-google-oauth-web-client-id>
VITE_API_BASE_URL=http://localhost:8000/api
```

Never commit `.env`, Gemini keys, OAuth client secrets, tokens, or user data.
The Google client secret is not used by the current GIS ID-token flow. In Google
Cloud Console, configure these authorized JavaScript origins during local work:

```text
http://localhost:5173
http://127.0.0.1:5173
```

## First-time setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
npm install --prefix frontend
.venv/bin/python backend/manage.py migrate
.venv/bin/python backend/manage.py seed_demo_data
.venv/bin/python backend/manage.py ingest_sources --path data/samples
```

The migration `core.0002_chatsession_is_pinned` must be applied for persistent
history pinning.

## Start the project

Terminal 1, from the repository root:

```bash
.venv/bin/python backend/manage.py runserver 127.0.0.1:8000
```

Terminal 2:

```bash
npm run dev --prefix frontend -- --host 127.0.0.1
```

Open:

- App: `http://127.0.0.1:5173`
- Assistant: `http://127.0.0.1:5173/assistant`
- API docs: `http://127.0.0.1:8000/api/docs/`
- Django admin: `http://127.0.0.1:8000/admin/`

## Test and validate before handoff

```bash
cd backend && ../.venv/bin/pytest core/tests -q
cd ../frontend && npm test -- --run
npm run lint
npm run build
```

Last verified state before this handoff:

- Backend: 11 tests passed
- Frontend: 5 tests passed
- ESLint passed
- TypeScript and Vite production build passed

## Implemented user flows

- English/Hindi grounded chat with citations and safe abstention
- Typo-tolerant retrieval (`microwace` can match `microwave`)
- Six free guest questions, followed by Google sign-in
- Google-authenticated database-backed history, delete and pin/unpin
- Separate Pinned and Recent history sections
- Collapsible and drag-resizable chat-history panel
- Product/manufacturing intent detection and a seven-stage visual roadmap
- Selected roadmap-stage detail with deterministic numbered progression
- Terminal roadmap completion state (Stage 07 does not loop to Stage 01)
- Current-location laboratory action after roadmap completion
- Testing guidance and official BIS LIMS scope-verification notice
- Multiple visual lab candidate cards for the Maharashtra demo path
- Product image upload with Gemini vision and brand clarification
- `+` attachment menu, camera capture, and image/text drag-and-drop
- English/Hindi microphone input and text-to-speech answers
- Send button changes into a Stop button while a request is active
- Mock certification lookup and product-to-standard finder

## Important implementation locations

- `backend/core/services/rag.py`: intent routing, grounding and roadmap/lab data
- `backend/core/services/retrieval.py`: local hybrid and fuzzy retrieval
- `backend/core/services/gemini.py`: Gemini and deterministic mock providers
- `backend/core/services/vision.py`: Gemini product-image detection
- `backend/core/views.py`: chat, image, history, auth and API orchestration
- `backend/core/serializers.py`: API response contracts and hidden messages
- `frontend/src/pages/Assistant.tsx`: chat, roadmap, history, voice, files and labs
- `frontend/src/components/AppShell.tsx`: global navigation/header
- `frontend/src/lib/api.ts`: frontend API client
- `frontend/src/styles.css`: current visual system and responsive behavior

## Behavioral rules that must be preserved

1. Never invent an IS number, test value, fee, deadline, certification status,
   mandatory applicability, or laboratory recognition.
2. Citations must refer only to retrieved chunks.
3. Exact laboratory scope must be verified in the official BIS LIMS directory:
   `https://lims.bis.gov.in/home/search_labs/`.
4. Location lookup prompts use `silent=true`; they must not appear as user chat
   bubbles or reappear when history is loaded.
5. If image vision identifies a product but cannot read the manufacturer/brand,
   ask the user instead of guessing. Preserve that product context in follow-up.
6. Stage 07 is terminal. It shows Roadmap complete and the location-based lab
   action; it must never fall back to Stage 01.
7. On the roadmap, clicking a stage sends it immediately with original product
   context. Normal Recommended next steps also send immediately.
8. Only the chat thread scrolls in the assistant workspace. Headers and sidebars
   stay fixed.
9. Demo verification and demo/candidate laboratory data must remain labelled.
10. Do not expose `GEMINI_API_KEY` or a Google client secret to Vite/frontend code.

## Current limitations and recommended next work

- Laboratory cards are location-oriented candidates from official LIMS listings,
  but exact IS-wise scope is not fetched live yet. Add an official/provider-backed
  lab adapter before calling results verified recommendations.
- Reverse geocoding currently uses the public OpenStreetMap Nominatim endpoint in
  the browser. A production deployment needs an approved provider, privacy review,
  caching and usage-policy compliance.
- Aborting a browser request stops the UI wait, but it cannot guarantee that an
  already-running Django/Gemini operation stops server-side. Add cancellable job
  orchestration for production.
- True token streaming/SSE is not implemented.
- Image uploads are validated and processed in memory; production should add
  malware scanning, storage policy, retention/deletion controls and EXIF removal.
- The demo corpus contains summaries supplied for the prototype, not a complete
  authorized BIS standards corpus.
- Consolidate `frontend/src/styles.css`; iterative UI work has created several
  intentional late overrides. Preserve final cascade behavior while refactoring.

## Safe workflow for the next AI assistant

1. Read this file, `README.md`, and `docs/adr/0001-system-architecture.md`.
2. Inspect `git status` and preserve existing user changes.
3. Never print or overwrite `.env` values.
4. Make focused edits with migrations for model changes.
5. Test backend and frontend after every functional change.
6. Keep all results grounded and clearly distinguish demo, candidate and official
   data.

## Shutdown

Stop both development servers with `Ctrl+C` in their terminals. If their owning
terminal is unavailable, identify exact listeners first and stop only those PIDs:

```bash
lsof -nP -iTCP:5173 -sTCP:LISTEN
lsof -nP -iTCP:8000 -sTCP:LISTEN
kill <frontend-pid> <backend-pid>
```
