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

## Features

- **Three-panel workspace** — sources / visualizations / chat, all driven by the same selection state.
- **Auto-charts** — focusing a CSV builds KPI cards + line/bar charts from the schema, no config needed.
- **RAG over docs** — drop in PDFs, text, markdown, or images; they're chunked, embedded locally, and queryable from chat.
- **Admin mode** — a toggle that reveals fields and documents marked `internal` / `pii` (everyone else only sees `public`).
- **Field-level redaction** — column- and chunk-level classification enforced both in chart aggregations and RAG retrieval.
- **Conversation memory** — chat threads persist in SQLite; follow-ups stay in the same context.
- **Friendly failure modes** — LLM timeouts, broken CSV columns, and bad PDF pages degrade gracefully instead of 500ing.

## Project structure

```
BizQuery/
├── backend/
│   ├── main.py                       # FastAPI app + global exception handler
│   ├── config.py                     # Settings (pydantic-settings, .env-driven)
│   ├── database.py                   # SQLAlchemy engine + get_db dependency
│   ├── logger.py                     # central stdout logger (Docker-friendly)
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
│   │   ├── App.jsx                   # 3-panel layout + view switcher
│   │   ├── components/
│   │   │   ├── SourcePanel.jsx       # left: dataset/doc list + admin toggle + upload
│   │   │   ├── VisualizationPanel.jsx# center: KPI cards + recharts
│   │   │   ├── ChatPanel.jsx         # right: conversation + citation chips
│   │   │   └── DocsPage.jsx          # standalone docs management view
│   │   ├── services/api.js           # Axios + response interceptor
│   │   └── utils/format.js           # number/filename helpers
│   ├── Dockerfile                    # multi-stage build → nginx
│   └── nginx.conf                    # /api/ → backend:8000
└── docker-compose.yml                # backend + frontend + named volumes
```

## API endpoints

| Method | URL | Description |
|---|---|---|
| GET | `/health` | Health check |
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

### 1. Configure the LLM key

```cmd
copy backend\.env.docker.example backend\.env.docker
```

If `.env.docker.example` doesn't exist, copy `.env.example` instead and adjust the paths to match the container layout (`/app/data/bizquery.db`, `/app/chroma_db`, `/app/uploads`). Then set your key:

```
LLM_API_KEY=gsk_...
```

Get a free Groq key at [console.groq.com/keys](https://console.groq.com/keys).

### 2. Build & run

```cmd
docker compose up --build
```

- Frontend: `http://localhost` (nginx on port 80)
- Backend: internal only, reached via `/api/*` proxy
- Logs: `docker compose logs -f backend`

Volumes (`sqlite_data`, `chroma_data`, `upload_data`) persist across rebuilds. To wipe state: `docker compose down -v`.

## Setup — local dev

### 1. Environment variables

```cmd
copy backend\.env.example backend\.env
```

Open `backend\.env` and fill in your LLM key — everything else has a sensible default:

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

API at `http://localhost:8000` · Interactive docs at `http://localhost:8000/docs`.

### 3. Run the frontend

```cmd
cd frontend
npm install
npm run dev
```

Frontend at `http://localhost:5173`. The Vite dev server proxies `/api` to the backend automatically — no CORS config needed during development.

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

### CSVs (structured analytics)

Loaded on demand by `services/data_proxy.py` when the user focuses a source. The LLM receives schema + summary stats + a row sample — CSVs are *not* embedded into the vector store, because semantic search on rows is poor for aggregations.

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

Supported extensions: `.pdf`, `.txt`, `.md`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`. Images are described by the LLM before being embedded.

## Admin mode & sensitivity

Each CSV column and each document carries a sensitivity tag (`public`, `internal`, `pii`, `identifier`). By default the assistant only sees `public` data. Flip the **Admin mode** toggle (left panel footer) to also reveal `internal` charts and confidential documents in the same session. The "Mark next upload confidential" toggle stamps the next upload as `internal`.

This is enforced server-side in `services/policy.py` — the toggle isn't just a UI filter.

## Logging & error handling

- All backend modules log through `backend/logger.py` to **stdout** (so `docker logs <container>` captures everything). Tune verbosity with `LOG_LEVEL` (`DEBUG` / `INFO` / `WARNING` / `ERROR`).
- LLM, DB, and embedding calls are wrapped in targeted `try/except` blocks with friendly fallbacks — the API never returns a raw traceback.
- The frontend's Axios interceptor logs every non-2xx response to the browser console, and chat errors surface the backend `detail` field inline.
