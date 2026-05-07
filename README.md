# BizQuery

An AI-powered business assistant that answers questions in plain English. Built with FastAPI, React, SQLite, and OpenAI.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy + SQLite |
| AI | OpenAI gpt-4o-mini |
| Frontend | React + Vite + Tailwind CSS |
| HTTP client | Axios |

## Project structure

```
BizQuery/
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # Settings loaded from .env
│   ├── database.py           # SQLAlchemy engine and session
│   ├── schemas.py            # Pydantic request/response models
│   ├── models/               # ORM table definitions
│   │   ├── conversation.py
│   │   └── message.py
│   ├── routers/
│   │   └── chat.py           # Chat endpoints
│   ├── services/
│   │   └── ai.py             # OpenAI wrapper
│   ├── migrations/           # Alembic migrations
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── components/
    │   │   └── ChatWindow.jsx
    │   ├── services/
    │   │   └── api.js        # Axios API client
    │   └── main.jsx
    └── vite.config.js
```

## API endpoints

| Method | URL | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/chat/message` | Send a message, get AI reply |
| GET | `/chat/conversations` | List all conversations |
| GET | `/chat/conversations/{id}` | Get conversation with messages |
| DELETE | `/chat/conversations/{id}` | Delete a conversation |

## Setup

### 1. Environment variables

```cmd
copy backend\.env.example backend\.env
```

Open `backend\.env` and fill in your OpenAI key — everything else has a default:

```
OPENAI_API_KEY=sk-proj-...
```

Get a key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys).

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
