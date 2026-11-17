# ADR 002: Modular Monolith vs. Microservices Architecture

## Status
Accepted

## Context
Engineering teams often face premature decomposition into microservices before domain boundaries stabilize. Microservices introduce network overhead, serialization latency, distributed transaction complexities, and independent deployment pipelines.

## Decision
We chose a **Modular Monolith** architecture for MedRAG.

## Consequences
### Positive
- **Clear Domain Boundaries**: Code is cleanly isolated into `api`, `services`, `repositories`, `models`, and `rag`.
- **Fast Local Development**: Single Python environment, single debugger, instant hot-reloading.
- **Easy Testing**: Integration tests run against the entire stack in milliseconds without spinning up multiple network services or docker containers.
- **Atomic Operations**: Database transactions can span multiple domain operations safely without distributed sagas.

### Future Evolution
If a specific subsystem (such as heavy document OCR or batched embedding generation) requires horizontal autoscaling independently from the API, it can be extracted into a dedicated worker consuming from a queue with minimal refactoring.
