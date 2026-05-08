# BizQuery

An AI-powered business assistant that answers questions over your structured data (CSVs) and unstructured documents (PDFs) in plain English.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy + SQLite |
| LLM | Groq `llama-3.3-70b-versatile` (any OpenAI-compatible provider works) |
| Embeddings | local ONNX `all-MiniLM-L6-v2` via ChromaDB |
| Vector store | ChromaDB (persistent, on-disk) |
| Frontend | React + Vite + Tailwind CSS |
| HTTP client | Axios |

## Project structure

```
BizQuery/
├── backend/
│   ├── main.py                       # FastAPI app entry point
│   ├── config.py                     # Settings loaded from .env
│   ├── database.py                   # SQLAlchemy engine and session
│   ├── schemas.py                    # Pydantic request/response models
│   ├── models/
│   │   ├── conversation.py
│   │   ├── message.py
│   │   └── document.py               # tracks ingested PDFs/files
│   ├── routers/
│   │   ├── chat.py                   # /chat/* — conversational endpoint
│   │   ├── analytics.py              # /analytics/* — one-shot Q&A + source listing
│   │   └── documents.py              # /documents/* — file upload + delete
│   ├── services/
│   │   ├── ai.py                     # LLM wrapper (Groq/OpenAI-compatible)
│   │   ├── data_proxy.py             # loads CSVs from database/data_sources/
│   │   └── rag/
│   │       ├── pipeline.py           # ingest_file / retrieve_context orchestrator
│   │       ├── ingestion.py          # extractors (PDF, CSV, txt/md, image)
│   │       ├── chunker.py            # text → overlapping chunks
│   │       ├── embedder.py           # ONNX embeddings
│   │       └── vector_store.py       # ChromaDB upsert/query
│   ├── migrations/                   # Alembic migrations
│   ├── requirements.txt
│   └── .env.example
├── database/
│   ├── data_sources/
│   │   ├── *.csv                     # structured tables
│   │   └── documents/*.pdf           # narrative docs for RAG
│   ├── seed_data.py                  # regenerate the relational CSVs
│   └── ingest_docs.py                # bulk-ingest PDFs into the vector store
└── frontend/
    ├── src/
    │   ├── components/ChatWindow.jsx
    │   ├── services/api.js
    │   └── main.jsx
    └── vite.config.js
```

## API endpoints

| Method | URL | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/chat/message` | Send a message; returns AI reply with conversation persisted |
| GET | `/chat/conversations` | List all conversations |
| GET | `/chat/conversations/{id}` | Get conversation with messages |
| DELETE | `/chat/conversations/{id}` | Delete a conversation |
| GET | `/analytics/sources` | List CSV data sources available to the dropdown |
| POST | `/analytics/query` | One-shot Q&A (no conversation history) |
| POST | `/documents/ingest` | Upload + embed a single file (PDF/CSV/txt/md/image) |
| GET | `/documents/` | List ingested documents |
| DELETE | `/documents/{doc_id}` | Remove a document and its embeddings |

## Setup

### 1. Environment variables

```cmd
copy backend\.env.example backend\.env
```

Open `backend\.env` and fill in your LLM API key — everything else has a sensible default:

```
LLM_API_KEY=gsk_...
```

Get a free Groq key at [console.groq.com/keys](https://console.groq.com/keys). To use OpenAI or another provider, also override `LLM_BASE_URL` and `LLM_MODEL`.

> The server exits immediately with a clear error if the key is missing.

### 2. Run the backend

```cmd
cd backend
.venv\Scripts\pip.exe install -r requirements.txt
.venv\Scripts\uvicorn.exe main:app --reload
```

API running at `http://localhost:8000`  
Interactive docs at `http://localhost:8000/docs`

### 3. Run the frontend

```cmd
cd frontend
npm install
npm run dev
```

Frontend running at `http://localhost:5173`

> The Vite dev server proxies all `/api` requests to the backend automatically — no CORS configuration needed during development.

## Data sources

The app draws on two kinds of data, kept under `database/`:

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

Loaded on demand by `services/data_proxy.py` when the user picks a source in the UI dropdown. The LLM receives schema + summary stats + a row sample — it does *not* embed CSVs into the vector store, because semantic search on rows is poor for aggregations.

To regenerate the synthetic relational dataset:

```cmd
backend\.venv\Scripts\python.exe database\seed_data.py
```

### PDFs (RAG)

PDFs in `database/data_sources/documents/` are chunked, embedded with a local ONNX `all-MiniLM-L6-v2` model, and stored in ChromaDB. Retrieval runs on every chat turn regardless of the dropdown selection.

**To ingest newly added PDFs**, drop the files into `database/data_sources/documents/` and run:

```cmd
backend\.venv\Scripts\python.exe database\ingest_docs.py
```

The script is idempotent:

| Existing record status | Action |
|---|---|
| `ingested` | skip |
| `failed` or `pending` | delete stale row, retry from scratch |
| not in DB | ingest |

Supported extensions: `.pdf`, `.txt`, `.md`. Image files (`.png`, `.jpg`, ...) are supported via the HTTP `POST /documents/ingest` endpoint, which describes the image with the LLM before embedding.
