# BizQuery
A secure AI-powered internal analytics assistant that can answer business questions using multiple private data sources.

## Setup

### 1. Environment variables
```bash
cp backend/.env.example backend/.env
```
Open `backend/.env` and set your values — **`OPENAI_API_KEY` is required**:
```
OPENAI_API_KEY=sk-proj-...   # get from platform.openai.com/api-keys
SECRET_KEY=any-long-random-string
```

### 2. Install & run backend
```cmd
cd backend
.venv\Scripts\pip.exe install -r requirements.txt
.venv\Scripts\uvicorn.exe main:app --reload
```
API docs: http://localhost:8000/docs

> The app will exit immediately with a clear error if `.env` is missing or `OPENAI_API_KEY` is not set.
