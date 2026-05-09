# BizQuery

An AI-powered business analytics workspace that answers questions over your structured data (CSVs) and unstructured documents (PDFs, text, images) in plain English. Three-panel UI: pick your sources on the left, see auto-generated charts in the middle, chat on the right.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy + SQLite |
| LLM | Groq `llama-3.3-70b-versatile` (any OpenAI-compatible provider works) |
| Embeddings | local ONNX `all-MiniLM-L6-v2` (no API calls, runs in-process) |
| Vector store | ChromaDB (persistent, on-disk) |
| Frontend | React + Vite + Tailwind CSS + recharts |
| HTTP client | Axios (with interceptor logging + 60–120 s timeouts) |
| Container | Docker Compose (backend + nginx-fronted frontend) |

**Why these picks.** The product is a single-user demo, so the stack is biased towards *zero infrastructure to run, easy to swap later*: SQLite avoids a database container; ChromaDB is persistent and embedded so there's no separate vector service; ONNX MiniLM runs on CPU with no API key or per-request cost (so embeddings stay on the box and free); FastAPI is async end-to-end, which keeps long LLM calls from blocking unrelated requests; Groq is the default LLM because the free tier is generous, but `LLM_BASE_URL`/`LLM_MODEL` make any OpenAI-compatible provider a drop-in. nginx fronts the frontend and reverse-proxies `/api/*` to the backend, so the whole app ships on one port. Logging is centralised in [backend/logger.py](backend/logger.py) (stdout for `docker logs` plus an in-memory ring buffer that powers the Logs page), and field-level access policy is enforced **server-side** in [services/policy.py](backend/services/policy.py) — not just hidden in the UI.

## Architecture

### System overview

```mermaid
flowchart LR
    User((User<br/>browser))

    subgraph FE[Frontend container]
        NG[nginx :80<br/>static + /api proxy]
        UI[React SPA<br/>Workspace / Docs / Logs]
    end

    subgraph BE[Backend container — FastAPI]
        R[Routers<br/>chat · analytics · documents · /logs]
        subgraph SVC[Services]
            AI[ai.py<br/>LLM wrapper]
            CTX[context.py<br/>source resolver]
            CH[charts.py]
            DP[data_proxy.py<br/>CSV loader]
            SR[source_router.py<br/>auto picker]
            POL[policy.py<br/>field-level ACL]
        end
        subgraph RP[RAG pipeline]
            ING[ingestion]
            CHK[chunker]
            EMB[embedder<br/>ONNX MiniLM]
            VS[vector_store]
        end
        L[logger.py<br/>stdout + ring buffer]
    end

    subgraph V[Docker volumes]
        DB[(SQLite<br/>conversations<br/>messages<br/>documents)]
        CDB[(ChromaDB<br/>embeddings)]
        UP[(uploads/)]
    end

    SEED[CSVs + PDFs<br/>database/data_sources/]
    LLM((Groq /<br/>OpenAI-compatible))

    User -->|HTTPS| NG
    UI -->|axios /api/*| NG
    NG --> R
    R --> SVC
    R --> RP
    R <--> DB
    AI --> LLM
    DP --> SEED
    ING --> SEED
    ING --> CHK --> EMB --> VS
    VS <--> CDB
    R --> UP
    POL -.gate.-> CTX
    POL -.gate.-> CH
    POL -.gate.-> VS
    L -.tail.-> R
```

### Chat request flow

How a single `/chat/message` turn pulls from multiple sources before answering:

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as Backend<br/>/chat/message
    participant POL as policy
    participant DP as data_proxy<br/>(CSV)
    participant RAG as RAG retrieve<br/>(Chroma)
    participant LLM as Groq LLM
    participant DB as SQLite

    U->>FE: ask question
    FE->>API: POST {message, source_ids, admin}
    API->>POL: filter sources by sensitivity
    par parallel context build
        API->>DP: schema + stats + sample
    and
        API->>RAG: top-k chunks (filtered)
    end
    API->>LLM: prompt with grounded context
    LLM-->>API: answer
    API->>DB: persist user + assistant messages
    API-->>FE: {message, sources}
    FE-->>U: render bubble + citation chips
```

## Features

- **Three-panel workspace** — sources / visualizations / chat, all driven by the same selection state.
- **Auto-charts** — focusing a CSV builds KPI cards + line/bar charts from the schema, no config needed.
- **RAG over docs** — drop in PDFs, text, markdown, or images; they're chunked, embedded locally, and queryable from chat.
- **Admin mode** — a toggle that reveals fields and documents marked `internal` / `pii` (everyone else only sees `public`).
- **Field-level redaction** — column- and chunk-level classification enforced both in chart aggregations and RAG retrieval.
- **Conversation memory** — chat threads persist in SQLite; follow-ups stay in the same context.
- **Live Logs page** — built-in viewer that tails the backend's in-memory log ring (level filter, auto-refresh, traceback-aware).
- **Friendly failure modes** — LLM timeouts, broken CSV columns, and bad PDF pages degrade gracefully instead of 500ing.

## Project structure

```
BizQuery/
├── backend/
│   ├── main.py                       # FastAPI app + global exception handler + /logs
│   ├── config.py                     # Settings (pydantic-settings, .env-driven)
│   ├── database.py                   # SQLAlchemy engine + get_db dependency
│   ├── logger.py                     # central stdout logger + in-memory ring buffer
│   ├── schemas.py                    # Pydantic request/response models
│   ├── models/                       # Conversation, Message, Document
│   ├── routers/
│   │   ├── chat.py                   # /chat/* — conversational endpoint
│   │   ├── analytics.py              # /analytics/* — sources, charts, one-shot Q&A
│   │   └── documents.py              # /documents/* — upload, list, delete (50 MB cap)
│   ├── services/
│   │   ├── ai.py                     # async LLM wrapper with timeout/error fallbacks
│   │   ├── openai_client.py          # AsyncOpenAI client factory
│   │   ├── charts.py                 # KPI + chart bundle builder
│   │   ├── data_proxy.py             # CSV loader + per-column stats
│   │   ├── source_router.py          # LLM-based "auto" CSV picker
│   │   ├── policy.py                 # field-level access policy
│   │   ├── context.py                # shared source-resolution + RAG filtering
│   │   └── rag/
│   │       ├── pipeline.py           # ingest_file / retrieve_context
│   │       ├── ingestion.py          # PDF/CSV/text/image extractors
│   │       ├── chunker.py            # text → overlapping chunks
│   │       ├── embedder.py           # ONNX MiniLM embeddings
│   │       └── vector_store.py       # ChromaDB upsert/query/delete
│   ├── migrations/                   # Alembic migrations
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── database/
│   ├── data_sources/
│   │   ├── *.csv                     # structured tables (movies, viewers, ...)
│   │   └── documents/*.pdf           # narrative business docs for RAG
│   ├── seed_data.py                  # regenerate the relational CSVs
│   └── ingest_docs.py                # bulk-ingest PDFs into the vector store
├── frontend/
│   ├── src/
│   │   ├── App.jsx                   # 3-panel layout + view switcher (workspace/docs/logs)
│   │   ├── components/
│   │   │   ├── SourcePanel.jsx       # left: dataset/doc list + admin toggle + upload
│   │   │   ├── VisualizationPanel.jsx# center: KPI cards + recharts
│   │   │   ├── ChatPanel.jsx         # right: conversation + citation chips
│   │   │   ├── DocsPage.jsx          # standalone operation guide
│   │   │   └── LogsPage.jsx          # standalone backend log viewer
│   │   ├── services/api.js           # Axios + response interceptor
│   │   └── utils/format.js           # number/filename helpers
│   ├── Dockerfile                    # multi-stage build → nginx
│   └── nginx.conf                    # /api/ → backend:8000
└── docker-compose.yml                # backend + frontend + named volumes
```

## API endpoints

| Method | URL | Description |
|---|---|---|
| GET | `/health` | Health check (used by Docker healthchecks / load balancers) |
| GET | `/logs?limit=500` | Snapshot of the in-memory log ring (powers the Logs page) |
| POST | `/chat/message` | Send a message; returns AI reply with conversation persisted |
| GET | `/chat/conversations` | List all conversations |
| GET | `/chat/conversations/{id}` | Get conversation with messages |
| DELETE | `/chat/conversations/{id}` | Delete a conversation |
| GET | `/analytics/sources` | List CSV data sources |
| GET | `/analytics/charts/{source_id}?admin=` | KPI + chart bundle for the viz panel |
| POST | `/analytics/query` | One-shot Q&A (no conversation history) |
| POST | `/documents/ingest` | Upload + embed a single file (multipart, max 50 MB) |
| GET | `/documents/` | List ingested documents |
| DELETE | `/documents/{doc_id}` | Remove a document and its embeddings |

## Setup — Docker (recommended)

The fastest path. One command, isolated volumes, no Python/Node setup needed.

**Prerequisites:** Docker Desktop (or Docker Engine + the `compose` plugin) and a free Groq API key from [console.groq.com/keys](https://console.groq.com/keys).

### 1. Configure the LLM key

```cmd
copy backend\.env.example backend\.env.docker
```

Then edit `backend\.env.docker`:

```
LLM_API_KEY=gsk_...
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile

# in-container paths (don't change these for the default compose setup)
DATABASE_URL=sqlite:////app/data/bizquery.db
CHROMA_DIR=/app/chroma_db
UPLOAD_DIR=/app/uploads

# CORS — frontend talks to backend through nginx, so this can be permissive
CORS_ORIGINS=http://localhost,http://localhost:80

LOG_LEVEL=INFO
LOG_BUFFER_SIZE=1000
```

### 2. Build & run

```cmd
docker compose up --build
```

- Frontend: <http://localhost> (nginx on port 80)
- Backend: internal only, reached via the `/api/*` proxy
- Live logs: `docker compose logs -f backend` — or use the **Logs** tab in the UI

Volumes (`sqlite_data`, `chroma_data`, `upload_data`) persist across rebuilds. Useful one-liners:

```cmd
docker compose ps                     :: container status
docker compose logs -f backend        :: tail backend logs
docker compose restart backend        :: pick up an .env.docker change
docker compose down                   :: stop (state survives)
docker compose down -v                :: stop AND wipe all volumes (fresh DB + chroma + uploads)
```

### Troubleshooting

- **`I'm having trouble reaching the model right now…` in chat** — the LLM call failed. Open the **Logs** tab (or `docker compose logs backend`) and look for a `bizquery.ai` line. The most common cause on Groq's free tier is HTTP 429 (daily token cap of ~100k TPD) — wait for the window to reset, swap to a smaller model in `.env.docker`, or upgrade tier.
- **Backend exits immediately on first run** — the `LLM_API_KEY` is missing from `.env.docker`. The error message tells you exactly what's missing.
- **Chroma telemetry warnings** in the logs (`Failed to send telemetry event …`) are noise from ChromaDB's optional analytics — they don't affect functionality.

## Setup — local dev

**Prerequisites:** Python 3.10+, Node 18+, npm.

### 1. Environment variables

```cmd
copy backend\.env.example backend\.env
```

Open `backend\.env` and fill in your LLM key — everything else has a sensible default for local paths:

```
LLM_API_KEY=gsk_...
LOG_LEVEL=INFO
```

To use OpenAI or another provider, override `LLM_BASE_URL` and `LLM_MODEL`. The server exits immediately with a clear error if the key is missing.

### 2. Run the backend

```cmd
cd backend
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
.venv\Scripts\uvicorn.exe main:app --reload
```

API at <http://localhost:8000> · interactive docs at <http://localhost:8000/docs>.

### 3. Run the frontend

```cmd
cd frontend
npm install
npm run dev
```

Frontend at <http://localhost:5173>. The Vite dev server proxies `/api` to the backend automatically — no CORS config needed during development.

## Data sources

Two kinds of data, kept under `database/`:

```
database/
├── data_sources/
│   ├── *.csv                # structured tables (movies, viewers, ...)
│   └── documents/
│       └── *.pdf            # narrative business docs for RAG
├── chroma_db/               # generated vector store (gitignored)
├── seed_data.py             # regenerate the relational CSVs
└── ingest_docs.py           # bulk-ingest PDFs into the RAG store
```

The bundled CSVs and PDFs are **synthetic demo data** generated by `seed_data.py` — there's no real PII or business secrets baked in.

### CSVs (structured analytics)

Loaded on demand by [services/data_proxy.py](backend/services/data_proxy.py) when the user focuses a source. The LLM receives schema + summary stats + a row sample — CSVs are *not* embedded into the vector store, because semantic search on rows is a poor substitute for aggregations like sums and group-bys.

To regenerate the synthetic relational dataset:

```cmd
backend\.venv\Scripts\python.exe database\seed_data.py
```

### Documents (RAG)

PDFs, `.txt`, `.md`, and images in `database/data_sources/documents/` are chunked, embedded with a local ONNX `all-MiniLM-L6-v2` model, and stored in ChromaDB. Retrieval runs on every chat turn.

**To ingest newly added documents**, drop the files in and run:

```cmd
backend\.venv\Scripts\python.exe database\ingest_docs.py
```

Or upload one at a time through the UI (left panel → "+ Add document"). The script is idempotent:

| Existing record status | Action |
|---|---|
| `ingested` | skip |
| `failed` or `pending` | delete stale row, retry from scratch |
| not in DB | ingest |

Supported extensions: `.pdf`, `.txt`, `.md`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`. Images are described by the LLM before being embedded. Ingestion runs synchronously inside the request — fine for demo-sized PDFs (a few MB), so there's no background job queue.

## Admin mode & sensitivity

Each CSV column and each document carries a sensitivity tag (`public`, `internal`, `pii`, `identifier`). By default the assistant only sees `public` data. Flip the **Admin mode** toggle (left panel footer) to also reveal `internal` charts and confidential documents in the same session. The "Mark next upload confidential" toggle stamps the next upload as `internal`.

This is enforced server-side in [services/policy.py](backend/services/policy.py) — the toggle isn't just a UI filter. The model also assumes a **single trusted user** (the assignment scope): there's no login, no per-user audit log, and the admin checkbox is the only access control. For a multi-tenant deployment you'd swap the boolean for a real auth context (JWT, session cookie) and gate `/logs`, `/documents/*`, and the admin flag behind it.

## Logging & error handling

- All backend modules log through [backend/logger.py](backend/logger.py) to **stdout** (so `docker logs <container>` captures everything) *and* an in-memory ring buffer (last `LOG_BUFFER_SIZE` lines, default 1000) that powers the **Logs** tab in the UI. The buffer is per-process and ephemeral — restarting the backend wipes it; for long-term retention, ship `docker logs` to your host's log aggregator.
- Tune verbosity with `LOG_LEVEL` (`DEBUG` / `INFO` / `WARNING` / `ERROR`).
- LLM, DB, file, and embedding calls are wrapped in targeted `try/except` blocks with friendly fallbacks — the API never returns a raw traceback. A global handler in `main.py` turns any uncaught exception into a generic 500 JSON response.
- The frontend's Axios interceptor logs every non-2xx response to the browser console, and chat errors surface the backend `detail` field inline.
