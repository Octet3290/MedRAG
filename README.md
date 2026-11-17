# MedRAG — Production-Quality AI Knowledge Assistant

MedRAG is an enterprise-grade document knowledge assistant built with a **Modular Monolith** architecture. Users can upload documents (PDF, TXT), process them into structured semantic chunks, store vector embeddings in PostgreSQL using `pgvector`, and ask questions that receive grounded answers backed by verified source citations and page numbers.

---

## Tech Stack

- **Frontend**: Next.js 15+ (App Router), React, TypeScript (Strict Mode), Tailwind CSS.
- **Backend**: Python 3.14 / 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0.
- **Database**: PostgreSQL with `pgvector` extension (hosted on Neon Serverless).
- **Driver & Migrations**: `psycopg3` (async), Alembic.
- **Testing & Quality**: Pytest, HTTPX AsyncClient, Ruff (linter/formatter).

---

## Project Structure

```
medrag/
├── apps/
│   └── web/                   # Next.js frontend application
├── services/
│   └── api/                   # FastAPI backend service
├── docs/                      # Architecture, database schema, ADRs
├── .env.example               # Environment variable template
└── README.md
```

---

## Quickstart Guide

### 1. Prerequisites
- Python 3.11+
- Node.js 20+ & npm

### 2. Environment Configuration
Copy `.env.example` to `.env` in the root directory:
```bash
cp .env.example .env
```

### 3. Backend Setup & Run

Activate the Python virtual environment and run the FastAPI server:

**On Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
cd services/api
uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- **Interactive OpenAPI Docs**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### 4. Running Backend Tests & Linter

```powershell
# Run the test suite
.\.venv\Scripts\python.exe -m pytest services/api

# Run the linter
.\.venv\Scripts\ruff.exe check services/api

# Run the formatter
.\.venv\Scripts\ruff.exe format services/api
```

### 5. Frontend Setup & Run

```powershell
cd apps/web
npm run dev
```

The frontend will be available at: [http://localhost:3000](http://localhost:3000).

---

## Architecture Decision Records (ADRs)

- [ADR 001: PostgreSQL with pgvector for Relational and Vector Storage](docs/decisions/001-database-and-vector-storage.md)
- [ADR 002: Modular Monolith vs. Microservices Architecture](docs/decisions/002-modular-monolith-architecture.md)
