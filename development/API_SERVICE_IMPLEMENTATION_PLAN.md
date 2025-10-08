# API Service Implementation Plan
## FastAPI Integration with PostgreSQL + pgvector System

**Phase**: Pillar 2 Implementation  
**Duration**: 6-8 hours development time  
**Objective**: HTTP API service layer for Hormozi RAG system  
**Database**: Integrate with existing PostgreSQL hormozi_rag database  

---

## 🎯 **IMPLEMENTATION ROADMAP**

### **Day 1: Core API Foundation (2-3 hours)**

#### **Step 1.1: FastAPI Application Setup**
```python
# File: production/api/main.py (CREATE)
FILE LIFECYCLE: production
PURPOSE: HTTP API server for Hormozi framework queries
REPLACES: Direct database access scripts
CLEANUP_DATE: permanent (production system)

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import psycopg2
import openai
import os
from typing import List, Optional
import logging

# Configure logging per DEVELOPMENT_RULES.md
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hormozi RAG API",
    description="Semantic search API for Hormozi's $100M Offers framework",
    version="1.0.0"
)

# Request/Response models
class QueryRequest(BaseModel):
    query: str
    limit: Optional[int] = 5

class FrameworkChunk(BaseModel):
    chunk_id: str
    framework_name: str  
    content_snippet: str
    similarity_score: float
    section: str

class QueryResponse(BaseModel):
    query: str
    results: List[FrameworkChunk]
    total_results: int
    query_time_ms: float
```

#### **Step 1.2: PostgreSQL Integration**
```python
# File: production/api/database.py (CREATE)
FILE LIFECYCLE: production
PURPOSE: PostgreSQL connection and query management for API
REPLACES: Direct psycopg2 usage in scripts
CLEANUP_DATE: permanent

import psycopg2
import psycopg2.extras
from contextlib import contextmanager
import os
from typing import List, Tuple
import json

class PostgreSQLService:
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'database': os.getenv('POSTGRES_DB', 'hormozi_rag'),
            'user': os.getenv('POSTGRES_USER', 'rag_app_user'),
            'password': os.getenv('POSTGRES_PASSWORD'),
            'port': int(os.getenv('POSTGRES_PORT', 5432))
        }
    
    @contextmanager
    def get_connection(self):
        """Get PostgreSQL connection with proper cleanup"""
        conn = None
        try:
            conn = psycopg2.connect(**self.connection_params)
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def semantic_search(self, query_embedding: List[float], limit: int = 5) -> List[Tuple]:
        """Execute vector similarity search using pgvector"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Use existing PostgreSQL schema with pgvector operator
            cursor.execute("""
                SELECT 
                    fd.chunk_id,
                    fd.section,
                    fd.content,
                    fm.framework_name,
                    ce.embedding <-> %s as distance
                FROM framework_documents fd
                JOIN framework_metadata fm ON fd.id = fm.document_id
                JOIN chunk_embeddings ce ON fd.id = ce.document_id
                ORDER BY distance
                LIMIT %s
            """, (json.dumps(query_embedding), limit))
            
            return cursor.fetchall()
```

#### **Step 1.3: Core /query Endpoint**
```python
# Add to production/api/main.py

@app.post("/query", response_model=QueryResponse)
async def query_frameworks(request: QueryRequest):
    """
    Search Hormozi frameworks using semantic similarity
    
    Input: User query string
    Output: Relevant framework chunks with similarity scores
    """
    import time
    start_time = time.time()
    
    try:
        # Input validation
        if not request.query or not request.query.strip():
            raise HTTPException(400, "Query cannot be empty")
        
        # Generate embedding using OpenAI (existing .env config)
        openai.api_key = os.getenv('OPENAI_API_KEY')
        embedding_response = openai.embeddings.create(
            model="text-embedding-3-large",
            input=request.query
        )
        query_embedding = embedding_response.data[0].embedding
        
        # Execute vector search on PostgreSQL
        db_service = PostgreSQLService()
        results = db_service.semantic_search(query_embedding, request.limit)
        
        # Format response
        framework_chunks = []
        for row in results:
            chunk = FrameworkChunk(
                chunk_id=row['chunk_id'],
                framework_name=row['framework_name'], 
                content_snippet=row['content'][:500] + "..." if len(row['content']) > 500 else row['content'],
                similarity_score=1.0 - row['distance'],  # Convert distance to similarity
                section=row['section']
            )
            framework_chunks.append(chunk)
        
        query_time = (time.time() - start_time) * 1000  # ms
        
        return QueryResponse(
            query=request.query,
            results=framework_chunks,
            total_results=len(framework_chunks),
            query_time_ms=query_time
        )
        
    except Exception as e:
        logger.error(f"Query processing failed: {e}", exc_info=True)
        raise HTTPException(500, f"Query processing failed: {str(e)}")
```

### **Day 2: Health and Monitoring (2-3 hours)**

#### **Step 2.1: Health Check Endpoint**
```python
# Add to production/api/main.py

@app.get("/health")
async def health_check():
    """
    Service health validation including PostgreSQL connectivity
    """
    health_status = {
        "service": "hormozi_rag_api",
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {}
    }
    
    # Test PostgreSQL connection
    try:
        db_service = PostgreSQLService()
        with db_service.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM framework_documents")
            doc_count = cursor.fetchone()[0]
            
        health_status["checks"]["database"] = {
            "status": "healthy",
            "document_count": doc_count,
            "expected_count": 20
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "failed", 
            "error": str(e)
        }
    
    # Test OpenAI API access
    try:
        openai.api_key = os.getenv('OPENAI_API_KEY')
        # Quick test embedding
        test_response = openai.embeddings.create(
            model="text-embedding-3-large",
            input="test"
        )
        
        health_status["checks"]["openai"] = {
            "status": "healthy",
            "model": "text-embedding-3-large"
        }
    except Exception as e:
        health_status["checks"]["openai"] = {
            "status": "failed",
            "error": str(e)
        }
    
    return health_status
```

#### **Step 2.2: Request Logging and Monitoring**
```python
# File: production/api/middleware.py (CREATE)
FILE LIFECYCLE: production
PURPOSE: Request logging and monitoring for FastAPI
CLEANUP_DATE: permanent

import time
import uuid
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            "Request completed", 
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "process_time": process_time
            }
        )
        
        return response

# Add to main.py:
app.add_middleware(LoggingMiddleware)
```

---

## 🔧 **POSTGRESQL INTEGRATION PATTERNS**

### **Query Patterns to Implement:**

#### **Pattern 1: Semantic Search (Vector Similarity)**
```sql
-- Use in /query endpoint
SELECT 
    fd.chunk_id,
    fd.section,
    fd.content,
    fm.framework_name,
    ce.embedding <-> %s::vector as distance,
    1.0 - (ce.embedding <-> %s::vector) as similarity_score
FROM framework_documents fd
JOIN framework_metadata fm ON fd.id = fm.document_id
JOIN chunk_embeddings ce ON fd.id = ce.document_id
ORDER BY distance
LIMIT %s;
```

#### **Pattern 2: Hybrid Search (Text + Vector)**
```sql
-- Use in enhanced /query endpoint
SELECT 
    fd.chunk_id,
    fd.content,
    fm.framework_name,
    ce.embedding <-> %s::vector as vector_distance,
    ts_rank(to_tsvector('english', fd.content), plainto_tsquery('english', %s)) as text_rank,
    -- Combined relevance score (70% vector, 30% text)
    (0.7 * (1.0 - (ce.embedding <-> %s::vector))) + (0.3 * ts_rank(to_tsvector('english', fd.content), plainto_tsquery('english', %s))) as combined_score
FROM framework_documents fd
JOIN framework_metadata fm ON fd.id = fm.document_id  
JOIN chunk_embeddings ce ON fd.id = ce.document_id
WHERE to_tsvector('english', fd.content) @@ plainto_tsquery('english', %s)
ORDER BY combined_score DESC
LIMIT %s;
```

#### **Pattern 3: Framework-Specific Retrieval**
```sql
-- Use in /analyze-offer endpoint
SELECT 
    fd.chunk_id,
    fd.content, 
    fm.framework_name,
    fm.chunk_type
FROM framework_documents fd
JOIN framework_metadata fm ON fd.id = fm.document_id
WHERE fm.framework_name IN ('premium_pricing_philosophy', 'the_value_equation', 'scarcity_urgency_fomo_creation')
ORDER BY fm.character_count DESC;
```

---

## 📊 **SUCCESS VALIDATION**

### **API Service Layer Validation:**
```bash
# Test core functionality
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I increase perceived value?"}'

# Expected Response:
{
  "query": "How do I increase perceived value?",
  "results": [
    {
      "chunk_id": "value_equation_complete_framework_010",
      "framework_name": "the_value_equation",
      "content_snippet": "Value = (Dream Outcome × Likelihood)...",
      "similarity_score": 0.95,
      "section": "Section III: Value Creation"
    }
  ],
  "total_results": 5,
  "query_time_ms": 245
}

# Test health endpoint
curl http://localhost:8000/health
# Expected: {"service": "healthy", "checks": {"database": "healthy"}}
```

---

## 🚀 **READY FOR IMPLEMENTATION**

### **Current State Integration Points:**
- ✅ **PostgreSQL Database**: hormozi_rag operational with 20 chunks
- ✅ **Vector Embeddings**: 20 real OpenAI 3072-dimensional embeddings
- ✅ **Search Queries**: Semantic similarity patterns validated
- ✅ **Configuration**: production/config/.env ready for API usage
- ✅ **Directory Structure**: production/ organized for API development

### **Next Action:**
**Create the FastAPI application in `production/api/main.py` using the patterns above.**

This plan integrates directly with our validated PostgreSQL + pgvector foundation, ensuring the API layer leverages our existing data infrastructure optimally.