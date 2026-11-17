# MedRAG System Architecture

MedRAG is designed as a **Modular Monolith** prioritizing domain separation, high retrieval precision, verifiable citations, and operational simplicity.

---

## 1. Directory Structure & Boundaries

```
medrag/
├── apps/
│   └── web/                   # Next.js 15+ App Router, TypeScript, Tailwind CSS
│       ├── app/               # App Router pages and layouts
│       ├── components/        # Reusable accessible UI components
│       ├── features/          # Domain-specific UI features (chat, upload, documents)
│       ├── lib/               # Typed API client, utility functions
│       └── hooks/             # Custom React hooks
├── services/
│   └── api/                   # Python FastAPI Backend
│       ├── app/
│       │   ├── api/v1/        # HTTP presentation layer (thin route controllers)
│       │   ├── core/          # Central configuration, logging, database sessions
│       │   ├── models/        # SQLAlchemy 2.0 ORM domain entities
│       │   ├── schemas/       # Pydantic v2 request/response schemas
│       │   ├── repositories/  # Database access abstractions
│       │   ├── services/      # Core business logic
│       │   ├── rag/           # Chunking, embeddings, vector retrieval, citation validation
│       │   ├── workers/       # Asynchronous ingestion tasks
│       │   ├── security/      # Authentication, password hashing, token validation
│       │   └── tests/         # Pytest unit and integration test suite
│       ├── alembic/           # Database migration scripts
│       └── pyproject.toml     # Python dependencies and tool configurations
├── docs/                      # Architecture, database design, ADRs
├── scripts/                   # Local utility scripts
├── .env.example               # Central environment variable template
└── .gitignore                 # Version control exclusion rules
```

---

## 2. Core Architectural Layers

1. **Presentation Layer (`api/v1/endpoints`)**:
   - Thin route handlers.
   - Responsible only for HTTP parameters, status codes, and injecting services.
   - Does NOT contain business rules or direct SQL queries.

2. **Validation Layer (`schemas/`)**:
   - Pydantic models validate all incoming requests before business logic executes.
   - Pydantic response models sanitize outgoing data to prevent leaking internal database IDs, hashes, or infrastructure paths.

3. **Service Layer (`services/`)**:
   - Houses the pure business rules (e.g. document validation, knowledge base limits, orchestrating RAG queries).
   - Coordinates transactions across repositories.

4. **Persistence Layer (`repositories/` & `models/`)**:
   - SQLAlchemy 2.0 models mapped to PostgreSQL tables.
   - Uses `pgvector` for storing embeddings alongside relational foreign keys.

5. **RAG Core (`rag/`)**:
   - Provider-independent interfaces for LLMs and embedding models.
   - Token-aware chunking strategy with overlap.
   - Citation validation to guarantee that every claim links back to real indexed chunks.
