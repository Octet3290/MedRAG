# ADR 001: PostgreSQL with pgvector for Relational and Vector Storage

## Status
Accepted

## Context
A Retrieval-Augmented Generation (RAG) system requires two kinds of data storage:
1. **Relational metadata**: Users, permissions, knowledge bases, documents, conversation sessions, and messages.
2. **Vector embeddings**: High-dimensional numerical vectors representing chunks of text for similarity retrieval.

We evaluated two architectural options:
- **Option A**: Dedicated vector database (e.g., Pinecone, Qdrant) alongside a relational database (PostgreSQL).
- **Option B**: Unified PostgreSQL database with the `pgvector` extension (hosted on Neon Serverless Postgres).

## Decision
We chose **Option B: PostgreSQL + pgvector**.

## Consequences
### Positive
- **No Dual-Write Problem**: A document chunk, its text, page number, and vector embedding are written in a single ACID transaction.
- **Strict Authorization at Query Time**: We can filter chunks by `knowledge_base_id` and document ownership in the exact same SQL query that performs vector similarity search (`ORDER BY embedding <=> query_vector`).
- **Simpler Infrastructure**: One database backup, one connection string, zero synchronization latency between relational records and vector indices.
- **Portability**: Standard SQL and open-source PostgreSQL.

### Trade-offs / Mitigations
- Dedicated vector databases can index tens of millions of vectors with specialized distributed clustering.
- *Mitigation*: For hundreds of thousands of document chunks, `pgvector` with HNSW (`hierarchical navigable small world`) or IVFFlat indexes provides sub-10ms retrieval latency with minimal operational complexity.
