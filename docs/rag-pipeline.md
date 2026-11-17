# MedRAG — Retrieval-Augmented Generation (RAG) Pipeline

This document details the mathematical concepts, architectural stages, and implementation standards of the MedRAG chunking, embedding, and vector retrieval pipeline.

---

## 1. What Are Vector Embeddings? (Intuition & Math)

Large Language Models do not understand raw words—they understand numbers.
An **embedding model** converts a piece of unstructured text $T$ into a dense vector of real numbers $\vec{v} \in \mathbb{R}^{d}$ (e.g. $d = 1536$ dimensions):

$$T \xrightarrow{\text{Embedding Model}} \vec{v} = [v_1, v_2, \dots, v_{1536}]$$

### Semantic Closeness in High-Dimensional Space:
Texts sharing semantic meaning point in nearly identical geometric directions. For example:
- *"Hypertension protocol"*
- *"High blood pressure management"*

Even though these two phrases share zero words in common, their vectors have a very small angle $\theta$ between them.

### Cosine Similarity vs. Cosine Distance:
- **Cosine Similarity**:
  $$\text{Cosine Similarity}(\vec{u}, \vec{v}) = \frac{\vec{u} \cdot \vec{v}}{\|\vec{u}\| \|\vec{v}\|} = \cos(\theta)$$
  Range: $[-1.0, 1.0]$. A score of $1.0$ means identical direction.
- **Cosine Distance (in pgvector `<=>`)**:
  $$\text{Cosine Distance}(\vec{u}, \vec{v}) = 1 - \cos(\theta)$$
  Range: $[0.0, 2.0]$. A distance close to $0.0$ means high semantic similarity!

---

## 2. Chunking Strategy & Trade-offs

A naive approach of chunking by fixed characters (e.g., `text[:500]`) frequently splits words in half and breaks mid-sentence.

In MedRAG, we implement **Structure-Aware Per-Page Chunking**:

```
[Document Page]
       │
       ▼
Split by Paragraphs ("\n\n")
       │
       ├──► If Paragraph < 500 tokens ──► Accumulate
       │
       └──► If Paragraph > 500 tokens ──► Split by Sentences ("(?<=[.!?])\s+")
                 │
                 ▼
       Accumulate up to 500 tokens
                 │
                 ▼
       Emit Chunk with Page Number
                 │
                 ▼
       Carry forward 50 tokens overlap to next chunk
```

### Why Per-Page Boundary Preservation?
- If chunks bridge arbitrary page boundaries, an AI citation cannot point to an exact physical page.
- In MedRAG, chunking is scoped per-page: every chunk knows its originating `page_number` with 100% certainty.

---

## 3. Storage in PostgreSQL with pgvector

In MedRAG, chunks and embeddings live directly inside the `document_chunks` table:

```sql
SELECT 
    id,
    page_number,
    text_content,
    embedding <=> :query_vector AS cosine_distance
FROM document_chunks
WHERE document_id = :doc_id
ORDER BY embedding <=> :query_vector ASC
LIMIT 4;
```

### Key Advantages:
1. **Single ACID Transaction**: Adding or deleting chunks and vectors requires no synchronization with a secondary vector database.
2. **Cascading Deletes**: When a user or document is deleted, all associated vectors are instantly cleaned up by PostgreSQL.
3. **Idempotency**: The `/documents/{id}/reindex` endpoint purges existing chunks and regenerates new embeddings in a single atomic transaction.

---

## 4. Grounded Generation & Citation Verification (Milestone 6)

The generation phase connects vector search to LLM completion:

```
User Question
      │
      ▼
Embed Query (1536-dim vector)
      │
      ▼
pgvector Cosine Search (<=>)
      │
      ├──► Top-k Chunks with Document Title & Page Number
      │
      ▼
Context & Prompt Construction (with Prompt Injection Boundaries)
      │
      ▼
LLM Generation (MockLLMProvider or OpenAILLMProvider)
      │
      ▼
Citation Validation & Hallucination Guard
      │
      ▼
Structured Response (Answer + Verified Citations + Latency Debug)
```

### Prompt Injection Defense:
- Context is wrapped in `<context>...</context>` XML tags.
- Explicit instructions enforce that all content inside `<context>` is treated as untrusted reference data, never as system instructions.

### Post-Generation Citation Validation:
- Citations in the format `[Source: <doc>, Page: <page>]` are extracted using regular expressions.
- The validator cross-references each cited document and page against the chunks actually retrieved from pgvector.
- Only verified citations with exact chunk UUIDs and text excerpts are returned to the client.

---

## 5. Multi-Turn Conversation & Contextual Query Reformulation (Milestone 7)

In conversational medical research, users rarely ask standalone questions in isolation. Instead, dialogues evolve with follow-up questions:
- *Turn 1*: "What is the recommended dosage for metformin in type 2 diabetes?"
- *Turn 2*: "What are its main contraindications?"

### The Anaphora Problem in Vector Retrieval:
If a vector database searches directly for the raw embedding of *"What are its main contraindications?"*, the vector points towards generic contraindications across all medical treatments, losing the context of *Metformin*.

### The Solution: Contextual Reformulation
Before performing vector search on follow-up turns:
1. The system prompt instructs the reformulation engine to examine the last $N$ turns of dialogue.
2. Anaphoric pronouns (*it*, *its*, *this medication*) are resolved to the concrete medical subject.
3. A standalone vector query is generated: *"What are the contraindications for metformin?"*
4. pgvector executes the similarity search using this standalone query.
5. The LLM receives both the conversational `<chat_history>` and the fresh `<context>` chunks to generate a coherent, grounded answer.

```
User Follow-up ("What are its contraindications?") + Chat History
                               │
                               ▼
            Query Reformulation Engine (LLM / Mock)
                               │
                               ▼
       Standalone Query ("What are the contraindications for metformin?")
                               │
                               ▼
                 pgvector Cosine Search (<=>)
                               │
                               ▼
        Retrieved Chunks + Chat History + Current Question
                               │
                               ▼
              Grounded Response + Verified Citations
```

---

## 6. Background Workers & Durable Ingestion Queue (Milestone 8)

Synchronous ingestion of 50+ page PDFs in HTTP request handlers is an anti-pattern in production AI systems. Network timeouts (HTTP 504), rate limits on embedding APIs, and connection drops leave orphaned database records and lock server worker threads.

### Asynchronous Ingestion Lifecycle:
1. **HTTP Upload Phase (Fast & Lightweight)**:
   - File magic bytes and size limits are verified.
   - The file is saved to persistent server storage with a secure UUID key.
   - A database record is created with initial status `status="processing"`.
   - The API immediately responds with `HTTP 201 Created` containing the document metadata.
   - An asynchronous task is dispatched to the background queue (`BackgroundTasks.add_task(process_document_task, doc.id)`).

2. **Durable Worker Phase (`process_document_task`)**:
   - Executes with an isolated, dedicated database session (`AsyncSessionLocal()`).
   - Reads the physical content from server disk.
   - Performs page extraction, structure-aware chunking, and batch embedding.
   - Executes an atomic transaction: purges any stale chunks and bulk-inserts new chunks and vector embeddings.
   - Transitions document status to `ready` upon success.
   - On unhandled failure (e.g. corrupted PDF, missing file, embedding provider error): catches the exception, updates document status to `failed`, and persists `error_summary` for auditability and debugging.

3. **Client Polling & Self-Healing**:
   - The web frontend detects any documents in `processing` or `uploaded` states.
   - Background polling queries `/api/v1/knowledge-bases/{kb_id}/documents` every 2.5 seconds until all documents reach a terminal state (`ready` or `failed`).
   - Failed or ready documents can be reindexed on demand via `POST /api/v1/documents/{doc_id}/reindex?background=true`.

---

## 7. RAG Evaluation & Precision/Recall Metrics (Milestone 9)

In clinical RAG systems, model changes, prompt tweaks, and chunking modifications cannot be evaluated qualitatively. MedRAG incorporates an automated evaluation harness measuring both retrieval and generation quality.

### 7.1 Quantitative Retrieval Metrics:
1. **Hit Rate @ K (Recall @ K)**:
   Measures whether at least one ground-truth document chunk is retrieved within the top $K$ results:
   $$\text{Hit Rate @ } K = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \mathbb{I}\left( \text{relevant chunk} \in \text{Top-}K(q_i) \right)$$

2. **Mean Reciprocal Rank (MRR)**:
   Penalizes systems when the relevant chunk is buried deep in the context window:
   $$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$
   (A relevant chunk at rank 1 contributes $1.0$, rank 2 contributes $0.5$, rank 4 contributes $0.25$, and missing contributes $0.0$).

### 7.2 Quantitative Generation Metrics:
1. **Faithfulness / Groundedness**:
   Measures the proportion of factual claims in the generated response that are directly entailed by the retrieved context chunks (detects hallucinations):
   $$\text{Faithfulness} = \frac{|\text{Claims supported by retrieved context}|}{|\text{Total generated claims}|}$$
   Refusal responses to out-of-domain questions are scored as $1.0$ (100% faithful).

2. **Answer Relevance**:
   Measures whether the generated answer directly addresses the query and contains expected clinical entities.

3. **Citation Accuracy**:
   Validates whether citations match the actual originating source file and page number.


