# System Architecture - Hormozi RAG System

## Overview
This document is the **single source of truth** for system architecture. Any code that violates these principles should be rejected.

## Core Principles
1. **Single Responsibility**: Each module does ONE thing well
2. **Data Flows One Way**: Input → Process → Output (no circular dependencies)
3. **Fail Fast, Recover Gracefully**: Every operation can fail, plan for it
4. **Configuration Over Code**: Behavior changes through config, not code changes

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PUBLIC API LAYER                         │
│  FastAPI (hormozi_rag/api/app.py)                           │
│  - Endpoints: /query, /health, /metrics                     │
│  - Rate Limiting, Auth, Request Validation                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    ORCHESTRATOR LAYER                        │
│  QueryOrchestrator (hormozi_rag/core/orchestrator.py)      │
│  - Coordinates retrieval + generation                       │
│  - Manages conversation context                             │
│  - Handles retry logic and fallbacks                        │
└──────────────┬─────────────────────┬────────────────────────┘
               │                     │
┌──────────────▼─────────┐  ┌───────▼───────────────────────┐
│   RETRIEVAL ENGINE     │  │   GENERATION ENGINE           │
│  VectorRetriever       │  │   LLM Integration             │
│  - Semantic search     │  │   - Prompt engineering        │
│  - Reranking           │  │   - Response formatting       │
│  - Context window mgmt │  │   - Token management          │
└──────────────┬─────────┘  └───────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│                    STORAGE LAYER                             │
│  ├── PostgreSQL + pgvector (Vector + Document unified)      │
│  ├── Alternative: Chroma/Pinecone (Vector) + PostgreSQL     │
│  └── Cache Layer (Redis/In-Memory)                          │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Document Processing Pipeline
```
PDF Files → Extractor → Chunker → Embedder → VectorDB
                ↓           ↓         ↓
            Metadata    Statistics  Index
```

**Contracts:**
- Extractor Output: `{text: str, metadata: dict, page_map: dict}`
- Chunker Output: `[{id: str, text: str, metadata: dict, embedding: None}]`
- Embedder Output: `[{id: str, text: str, metadata: dict, embedding: float[]}]`

### 2. Query Processing Pipeline
```
User Query → Validation → Embedding → Retrieval → Reranking → Generation → Response
                 ↓            ↓           ↓           ↓           ↓
              Logging     Cache Check  Metrics   Analytics   Monitoring
```

**Contracts:**
- Query Input: `{query: str, filters: dict, limit: int, session_id: str}`
- Retrieval Output: `[{chunk_id: str, text: str, score: float, metadata: dict}]`
- Generation Input: `{query: str, context: list[str], history: list[dict]}`
- Response: `{answer: str, sources: list, confidence: float, metadata: dict}`

## Module Responsibilities

### Core Modules

#### `hormozi_rag/core/orchestrator.py`
- **Single Responsibility**: Coordinate retrieval and generation
- **Dependencies**: Retriever, Generator, Cache
- **State**: Stateless (context passed through)
- **Error Handling**: Circuit breaker for external services

#### `hormozi_rag/retrieval/retriever.py`
- **Single Responsibility**: Find relevant chunks
- **Dependencies**: VectorDB, Reranker
- **State**: Connection pool to VectorDB
- **Error Handling**: Fallback to keyword search

#### `hormozi_rag/embeddings/embedder.py`
- **Single Responsibility**: Convert text to vectors
- **Dependencies**: Embedding model
- **State**: Model cache
- **Error Handling**: Batch retry with exponential backoff

### Configuration Management

#### `hormozi_rag/config/settings.py`
```python
# Single source of configuration truth
class Settings:
    # Environment variables override defaults
    VECTOR_DB_TYPE: str = env("VECTOR_DB_TYPE", "postgresql")
    EMBEDDING_MODEL: str = env("EMBEDDING_MODEL", "openai")
    CHUNK_SIZE: int = env("CHUNK_SIZE", 1000)
    CHUNK_OVERLAP: int = env("CHUNK_OVERLAP", 200)
    
    # PostgreSQL Configuration
    POSTGRES_HOST: str = env("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = env("POSTGRES_PORT", 5432)
    POSTGRES_DB: str = env("POSTGRES_DB", "hormozi_rag")
    POSTGRES_USER: str = env("POSTGRES_USER", "rag_user")
    POSTGRES_PASSWORD: str = env("POSTGRES_PASSWORD", required=True)
    
    # Runtime validation
    def validate(self):
        assert self.CHUNK_OVERLAP < self.CHUNK_SIZE
        assert self.VECTOR_DB_TYPE in ["postgresql", "chroma", "pinecone", "weaviate"]
```

## State Management Rules

### 1. Singleton Services
- Database connections
- Model instances
- Cache clients

### 2. Request-Scoped
- User context
- Query parameters
- Temporary computations

### 3. Persistent State
- Vector embeddings
- Document metadata
- User preferences

## Error Handling Strategy

### Level 1: Validation Errors
- Return 400 with clear message
- Log as WARNING
- No retry

### Level 2: Retrieval Errors
- Fallback to keyword search
- Log as ERROR
- Retry with backoff

### Level 3: Generation Errors
- Return partial results if available
- Log as CRITICAL
- Circuit breaker activation

## Performance Boundaries

### Limits
- Max PDF size: 100MB
- Max chunks per query: 20
- Max concurrent requests: 100
- Max response time: 5 seconds

### Optimization Points
- Chunk cache: 1000 most recent
- Embedding cache: 10000 vectors
- Connection pool: 20 connections
- Batch processing: 100 chunks

## Monitoring Points

### Metrics to Track
- Query latency (p50, p95, p99)
- Retrieval accuracy (MRR, NDCG)
- Cache hit rate
- Error rates by type
- Token usage
- Memory usage

### Health Checks
```python
/health/live    # Service is running
/health/ready   # Dependencies are available
/health/startup # Initialization complete
```

## Extension Points

### Adding New Vector Database
**Primary**: PostgreSQL + pgvector (unified vector + document storage)
**Alternatives**: External vector databases for specialized use cases

1. Implement `VectorDBInterface` in `hormozi_rag/storage/interfaces.py`
2. Register in `hormozi_rag/storage/factory.py`
3. Add configuration in `settings.py`
4. Update validation in health checks

**PostgreSQL Implementation**: `hormozi_rag/storage/postgresql_storage.py`

### Adding New LLM Provider
1. Implement `LLMInterface` in `hormozi_rag/generation/interfaces.py`
2. Register in provider factory
3. Add API key configuration
4. Implement token counting

## Migration Strategy

### Database Migrations
```
migrations/
├── 001_initial_schema.sql
├── 002_add_metadata_fields.sql
└── 003_optimize_indexes.sql
```

### Breaking Changes
1. Version the API (`/v1/`, `/v2/`)
2. Deprecation warnings for 2 releases
3. Migration guide documentation
4. Backward compatibility layer

## Security Boundaries

### Input Validation
- SQL injection prevention
- Prompt injection detection
- Rate limiting per user
- Input size limits

### Data Protection
- Encrypt embeddings at rest
- API key rotation
- Audit logging
- PII detection and masking

## Development Workflow Integration

### Before Any Change
1. Check this architecture
2. Verify no violations
3. Update if architecture needs to evolve
4. Document the decision

### Code Review Checklist
- [ ] Follows single responsibility
- [ ] No circular dependencies
- [ ] Error handling implemented
- [ ] Performance within boundaries
- [ ] Monitoring points added
- [ ] Tests cover the contract