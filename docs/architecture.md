# Architecture

EduIntel is a monorepo with a FastAPI backend, a React/TypeScript frontend, and
a PostgreSQL + pgvector database. The backend is layered so business logic (ML,
NLP, RAG, analytics) is independent of the API and the ORM.

## System overview

```mermaid
flowchart TB
    subgraph Client
      UI[React + TS + Tailwind SPA<br/>12 analytics views]
    end
    subgraph API[FastAPI backend]
      R[REST routes<br/>validation · logging · auth-ready]
      SVC[Services / analytics]
      ML[ML pipeline<br/>features · train · serve · SHAP]
      NLP[NLP engine<br/>rule · transformer · LLM]
      RAG[RAG<br/>chunk · embed · retrieve]
      AN[AI Analyst<br/>grounded generation]
      LLMA[LLM abstraction<br/>Gemini · OpenAI · offline]
    end
    subgraph Data
      PG[(PostgreSQL 16<br/>+ pgvector HNSW)]
      MODELS[(Model registry<br/>joblib artifacts)]
    end
    UI -->|/api| R
    R --> SVC --> PG
    R --> ML --> PG
    ML --> MODELS
    R --> NLP --> PG
    R --> RAG --> PG
    R --> AN
    AN --> SVC
    AN --> RAG
    AN --> LLMA
    NLP --> LLMA
```

## Request lifecycle (AI Analyst example)

```mermaid
sequenceDiagram
    participant U as Instructor
    participant API as FastAPI
    participant CTX as Context assembler
    participant DB as Analytics/DB
    participant RAG as RAG (pgvector)
    participant LLM as LLM / extractive
    U->>API: POST /analyst/query {question}
    API->>CTX: gather_context(question)
    CTX->>DB: topic/course/student statistics (real numbers)
    CTX->>RAG: semantic_search(question) → cited chunks
    CTX-->>API: typed evidence + citations + recommendations
    API->>LLM: phrase evidence (numbers fixed) OR extractive compose
    LLM-->>U: grounded, cited answer (or "insufficient evidence")
```

## Backend layering

| Layer | Package | Responsibility |
|------|---------|----------------|
| API | `app/api` | Routing, request/response schemas, validation, error handling |
| Core | `app/core` | Config (env), structured logging, security primitives |
| Models | `app/models` | SQLAlchemy ORM (20 tables) |
| Analytics | `app/analytics` | Course health, topics, anomalies, data quality, dashboard, insights, trajectory |
| ML | `app/ml` | Feature engineering, training, evaluation, registry, serving, SHAP |
| NLP | `app/nlp` | Feedback sentiment/issue extraction (3 methods) |
| RAG | `app/rag` | Embeddings, chunking, ingestion, retrieval |
| Analyst | `app/analyst` | Evidence assembly, grounded generation, reports |
| LLM | `app/llm` | Provider-agnostic LLM abstraction |
| Services | `app/services` | Intervention recommendation/tracking |

## Design principles

- **Separation of concerns** — routes never contain business logic; ML/NLP/RAG
  code has no FastAPI dependency and is unit-testable in isolation.
- **Provider independence** — the app depends on an `LLMProvider` interface and
  an `EmbeddingModel` abstraction, never on a specific vendor SDK.
- **Graceful degradation** — every external dependency (LLM API, transformer
  weights) has an offline fallback, so the platform runs end-to-end with no keys.
- **Traceability** — predictions link to a `model_version`; analyst numbers link
  to their analytics source; RAG answers link to document chunks.
