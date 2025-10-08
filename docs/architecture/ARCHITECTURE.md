# System Architecture - Hormozi RAG System

## Overview
This document is the **single source of truth** for system architecture. Any code that violates these principles should be rejected.

## Core Principles
1. **Single Responsibility**: Each module does ONE thing well
2. **Data Flows One Way**: Input → Process → Output (no circular dependencies)
3. **Fail Fast, Recover Gracefully**: Every operation can fail, plan for it
4. **Configuration Over Code**: Behavior changes through config, not code changes

## Three-Pillar System Architecture

### **Architecture Overview: Local → API → MCP Evolution**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PILLAR 3: MCP SERVER LAYER                           │
│  Claude Desktop Integration (future_mcp_server/)                            │
│  - Tools: search_hormozi_frameworks(), analyze_offer_structure()            │
│  - Protocol: Anthropic MCP standard                                        │
│  - Integration: Direct Claude Desktop connection                            │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ HTTP calls
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                        PILLAR 2: API SERVICE LAYER                          │
│  FastAPI Production Server (production/api/)                                │
│  - Endpoints: /query, /analyze-offer, /health, /metrics                     │
│  - Features: Rate limiting, auth, validation, monitoring                    │
│  - Purpose: HTTP interface for all external access                          │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ Native calls
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                       PILLAR 1: DATA FOUNDATION                             │
│  PostgreSQL + pgvector (IMPLEMENTED ✅)                                     │
│  - Database: hormozi_rag with 20 chunks + embeddings                        │
│  - Search: Native vector similarity + full-text                             │
│  - Performance: Sub-millisecond queries                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### **Current State vs Future State:**

**✅ IMPLEMENTED (Pillar 1):**
- PostgreSQL 14.19 + pgvector 0.5.1
- 20 chunks with 3072-dimensional embeddings  
- Native vector similarity search working
- Production database with complete schema

**🔧 NEXT (Pillar 2 - API Service Layer):**
- FastAPI HTTP endpoints
- Request validation and error handling
- Production monitoring and logging
- Claude Desktop → HTTP API bridge

**🚀 FUTURE (Pillar 3 - MCP Integration):**
- MCP server process for Claude Desktop
- Tool definitions for framework search and analysis
- Direct Claude integration without browser switching

## Implementation Roadmap

### **Phase 1: Data Foundation (✅ COMPLETED)**
```
✅ PostgreSQL + pgvector database operational
✅ 20 chunks with real OpenAI embeddings  
✅ Native vector similarity search working
✅ Production-ready schema and data integrity
```

### **Phase 2: API Service Layer (🔧 NEXT - 6-8 hours)**
```
FastAPI Server Development:
├── Core Endpoints:
│   ├── POST /query - Framework search endpoint
│   ├── POST /analyze-offer - Offer analysis against frameworks  
│   ├── GET /health - Service health monitoring
│   └── GET /metrics - Performance and usage metrics
│
├── Production Features:
│   ├── Request validation (prevent injection/malformed requests)
│   ├── Error handling (graceful failures, no crashes)
│   ├── Rate limiting (prevent abuse)
│   ├── Logging (query tracking)  
│   └── Monitoring (response times, success rates)
│
└── PostgreSQL Integration:
    ├── Embedding generation via OpenAI
    ├── Vector similarity queries  
    ├── Result ranking and formatting
    └── Structured JSON responses
```

**Implementation Priority Order:**
1. `/query` endpoint (core functionality)  
2. `/health` endpoint (monitoring)
3. Error handling and validation
4. `/analyze-offer` endpoint (business logic)
5. Rate limiting and production features

### **Phase 3: MCP Server Integration (🚀 FUTURE - 4-6 hours)**
```
MCP Server for Claude Desktop:
├── MCP Tools Exposed:
│   ├── search_hormozi_frameworks(query: str) -> framework_results[]
│   ├── analyze_offer_structure(offer: dict) -> analysis_report
│   ├── get_framework_by_topic(topic: str) -> specific_framework
│   └── compare_offer_strategies(offers: list) -> comparison_matrix
│
├── Claude Desktop Integration:
│   ├── Direct tool calling (no browser needed)
│   ├── Context preservation across queries
│   ├── Automatic framework retrieval
│   └── Real-time offer analysis feedback
│
└── Service Architecture:
    ├── MCP Server Process (long-running Python process)
    ├── HTTP calls to FastAPI endpoints  
    ├── Error handling and timeouts
    └── Usage logging and debugging
```

## Data Flow Evolution

### **Current State (Pillar 1): Direct Database Access**
```
Local Scripts → PostgreSQL + pgvector → Results
```

### **Next State (Pillar 2): HTTP API Service**  
```
HTTP Request → FastAPI → QueryOrchestrator → PostgreSQL → Formatted Response
                 ↓            ↓                 ↓             ↓
              Validation   Embedding       Vector Search   JSON Response
```

### **Future State (Pillar 3): Claude Desktop Integration**
```
Claude Desktop → MCP Server → FastAPI → PostgreSQL → Claude Interface
     ↓                ↓           ↓           ↓             ↓
 Tool Calling    HTTP Bridge   Validation   Vector Search  Tool Response
```

## API Endpoint Specifications

### **Core Endpoints (Pillar 2):**

#### **POST /query**
```json
{
  "input": {"query": "How do I increase perceived value?"},
  "output": {
    "answer": "Use the Value Equation framework...",
    "sources": [
      {
        "chunk_id": "value_equation_complete_framework_010",
        "framework": "the_value_equation", 
        "relevance_score": 0.95,
        "content_snippet": "Value = (Dream Outcome × Likelihood)..."
      }
    ],
    "confidence": 0.92,
    "query_time_ms": 45
  }
}
```

#### **POST /analyze-offer**
```json
{
  "input": {
    "offer": {
      "price": "$2000",
      "deliverables": ["Course", "Templates", "Support"],
      "guarantee": "30-day money back"
    }
  },
  "output": {
    "analysis": {
      "pricing_assessment": "Consider premium positioning per Chapter 5",
      "value_equation_score": 7.2,
      "enhancement_opportunities": [
        "Add scarcity elements (Chapter 12)",
        "Strengthen guarantee (Chapter 15)"
      ],
      "relevant_frameworks": ["premium_pricing", "guarantees", "scarcity"]
    }
  }
}
```

### **MCP Tools (Pillar 3):**

#### **Tool: search_hormozi_frameworks**
```python
def search_hormozi_frameworks(query: str) -> List[FrameworkResult]:
    """
    Find relevant Hormozi frameworks for any business question
    
    Args:
        query: User's business question ("How do I price higher?")
        
    Returns:
        List of framework chunks with relevance scores
    """
```

#### **Tool: analyze_offer_structure** 
```python
def analyze_offer_structure(offer: OfferDetails) -> OfferAnalysis:
    """
    Analyze an offer against Hormozi principles
    
    Args:
        offer: Structured offer details (price, deliverables, guarantee, etc.)
        
    Returns:
        Framework-based analysis with improvement recommendations
    """
```

## Module Responsibilities

### **Pillar 1: Data Foundation (PostgreSQL + pgvector) ✅**

#### `PostgreSQL Database: hormozi_rag`
- **Single Responsibility**: Store and retrieve framework data with vector similarity
- **Implementation**: 6 tables per DATABASE_ENGINEERING_SPEC.md
- **State**: Persistent, ACID compliant
- **Performance**: <1ms queries, 20 chunks + embeddings operational

### **Pillar 2: API Service Layer (FastAPI) 🔧**

#### `production/api/app.py` (FastAPI Application)
- **Single Responsibility**: HTTP interface for all external access
- **Dependencies**: PostgreSQL, OpenAI, logging
- **State**: Stateless HTTP service
- **Endpoints**:
  - `POST /query`: Framework search with semantic similarity
  - `POST /analyze-offer`: Business offer analysis against frameworks
  - `GET /health`: Service health and database connectivity
  - `GET /metrics`: Performance monitoring and usage statistics

#### `production/api/hormozi_rag/core/orchestrator.py`
- **Single Responsibility**: Coordinate database queries and response formatting
- **Dependencies**: PostgreSQL connector, OpenAI embedder  
- **State**: Stateless (no session storage)
- **Functions**:
  - Query embedding generation
  - Vector similarity search execution  
  - Result ranking and confidence scoring
  - Response formatting for API consumption

#### `production/api/hormozi_rag/retrieval/retriever.py`
- **Single Responsibility**: Execute PostgreSQL vector and text queries
- **Dependencies**: psycopg2, pgvector operations
- **State**: Connection pooling only
- **Operations**:
  - Vector similarity search using pgvector <-> operator
  - Full-text search using PostgreSQL GIN indexes
  - Hybrid search combining vector + text relevance
  - Result metadata enrichment

### **Pillar 3: MCP Server Integration (Future) 🚀**

#### `future_mcp_server/mcp_server.py`
- **Single Responsibility**: Bridge Claude Desktop to FastAPI service
- **Dependencies**: MCP protocol, HTTP client
- **State**: Long-running process with connection management
- **Tools Exposed**:
  - `search_hormozi_frameworks()`: Framework discovery
  - `analyze_offer_structure()`: Offer evaluation
  - `get_framework_by_topic()`: Specific framework retrieval
  - `compare_offer_strategies()`: Multi-offer analysis

#### Integration Architecture:
```python
# MCP Server calls FastAPI endpoints:
search_frameworks() -> POST /query -> PostgreSQL -> JSON -> MCP Tool Response
analyze_offer() -> POST /analyze-offer -> Framework Analysis -> Claude Desktop
```

## Production Service Requirements

### **API Service Layer Specifications:**

#### **Performance Requirements:**
- **Query Response**: <500ms p95 (including OpenAI embedding)
- **Health Check**: <50ms response time
- **Concurrent Requests**: 10+ simultaneous users
- **Uptime**: 99.9% availability target

#### **Error Handling:**
- **Database Connection Failures**: Graceful retry with exponential backoff
- **OpenAI API Failures**: Fallback to cached embeddings or error response  
- **Malformed Requests**: Validation errors with helpful messages
- **Rate Limit Exceeded**: 429 status with retry-after header

#### **Monitoring and Logging:**
- **Request Logging**: Query content, response times, user identification
- **Error Tracking**: Exception details, stack traces, error frequency
- **Performance Metrics**: Query latency, database response times, throughput
- **Business Metrics**: Most requested frameworks, query patterns, user behavior

#### **Security Requirements:**
- **Input Validation**: SQL injection prevention, schema validation  
- **Rate Limiting**: Per-IP request throttling
- **Authentication**: API key based access control (future)
- **CORS**: Proper cross-origin request handling
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