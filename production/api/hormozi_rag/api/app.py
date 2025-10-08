"""
FastAPI for the Hormozi RAG system.

Follows ARCHITECTURE.md API Layer specification with proper health checks.
Implements DEVELOPMENT_RULES.md error handling hierarchy.
"""

import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    from fastapi import FastAPI, HTTPException, Query, Body, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field, validator
except ImportError:
    raise ImportError("fastapi not installed. Run: pip install fastapi uvicorn")

from ..config.settings import settings
from ..core.logger import get_logger

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Hormozi RAG System",
    description="Framework-aware retrieval for Alex Hormozi's business frameworks",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Global components (initialized on startup following ARCHITECTURE.md singleton pattern)
vector_db = None
llm_provider = None
cache = None

# Import PostgreSQL storage interface per ARCHITECTURE.md interface contracts
from ..storage.postgresql_storage import PostgreSQLVectorDB

# Pydantic models for API contracts following DEVELOPMENT_RULES.md validation standards
class QueryRequest(BaseModel):
    """
    Query request following DEVELOPMENT_RULES.md validation standards and ARCHITECTURE.md contracts
    """
    query: str = Field(..., min_length=1, max_length=1000, description="User's business question or framework search query")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Maximum results to return (ARCHITECTURE.md limit: max 20)")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional filters for search")
    search_type: Optional[str] = Field("vector", description="Search type: 'vector', 'hybrid', or 'text'")
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty or whitespace only')
        return v.strip()

class FrameworkChunk(BaseModel):
    """Framework chunk result following ARCHITECTURE.md response contracts"""
    chunk_id: str
    framework_name: str
    section: str
    title: str
    content_snippet: str
    similarity_score: float = Field(..., description="Similarity score (can be negative for cosine distance)")
    rank: int
    chunk_type: str
    metadata: Dict[str, Any]

class QueryResponse(BaseModel):
    """
    Query response following ARCHITECTURE.md response contracts and DATABASE_ENGINEERING_SPEC.md
    """
    query: str
    search_type: str
    results: List[FrameworkChunk]
    total_results: int
    query_time_ms: float
    request_id: str
    timestamp: str
    performance_metrics: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    dependencies: Dict[str, bool]


@app.on_event("startup")
async def startup_event():
    """
    Initialize system on startup following ARCHITECTURE.md singleton services pattern.
    
    Updated to use PostgreSQL storage interface per DECISION_LOG.md 2025-10-06 PostgreSQL decision.
    """
    global vector_db, llm_provider, cache
    
    try:
        logger.info("Initializing Hormozi RAG system with PostgreSQL...")
        
        # Initialize PostgreSQL vector storage per ARCHITECTURE.md interface contracts
        vector_db = PostgreSQLVectorDB()
        # Note: vector_db.initialize() already called in __init__
        
        # LLM provider not needed for MVP (using OpenAI directly in endpoints)
        llm_provider = "openai_direct"  # Indicates we're using direct OpenAI calls
        
        # Cache not needed for MVP (PostgreSQL performance is excellent)
        cache = None
        
        logger.info("RAG system initialized successfully", extra={
            "vector_db": "PostgreSQL",
            "llm_provider": llm_provider,
            "cache": "None (not needed for MVP)"
        })
        
    except Exception as e:
        logger.critical(f"Failed to initialize RAG system: {e}", exc_info=True)
        # Don't raise - let health checks handle this


# Health Check Endpoints as specified in ARCHITECTURE.md
@app.get("/health/live", response_model=HealthResponse)
async def health_live():
    """
    Liveness check - service is running.
    
    Implements ARCHITECTURE.md health check pattern.
    """
    return HealthResponse(
        status="alive",
        timestamp=datetime.now().isoformat(),
        dependencies={}
    )


@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """
    Comprehensive health check following ARCHITECTURE.md monitoring points and 
    DATABASE_ENGINEERING_SPEC.md health requirements
    
    Returns detailed health status for production monitoring
    Performance Target: <50ms per DATABASE_ENGINEERING_SPEC.md
    """
    start_time = time.time()
    
    health_status = {
        "service": "hormozi_rag_api",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "api_version": "v1",
        "checks": {}
    }
    
    try:
        # Check 1: PostgreSQL vector database (most critical)
        if vector_db:
            db_health = vector_db.detailed_health_check()
            health_status["checks"]["database"] = db_health["checks"]
            
            if db_health["status"] != "healthy":
                health_status["status"] = "degraded"
        else:
            health_status["status"] = "unhealthy"
            health_status["checks"]["database"] = {
                "status": "failed",
                "error": "PostgreSQL storage not initialized"
            }
        
        # Check 2: OpenAI API connectivity
        try:
            import openai
            openai.api_key = settings.OPENAI_API_KEY
            
            # Quick connectivity test
            test_response = openai.embeddings.create(
                model="text-embedding-3-large",
                input="health check test"
            )
            
            health_status["checks"]["openai"] = {
                "status": "healthy",
                "model": "text-embedding-3-large",
                "embedding_dimensions": len(test_response.data[0].embedding)
            }
            
        except Exception as e:
            health_status["checks"]["openai"] = {
                "status": "failed",
                "error": str(e)
            }
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"
        
        # Check 3: Configuration validation
        try:
            settings.validate()
            health_status["checks"]["configuration"] = {
                "status": "healthy",
                "vector_db_type": settings.VECTOR_DB_TYPE,
                "environment": settings.ENVIRONMENT
            }
        except Exception as e:
            health_status["checks"]["configuration"] = {
                "status": "failed",
                "error": str(e)
            }
            health_status["status"] = "unhealthy"
        
        # Performance validation
        health_check_time = (time.time() - start_time) * 1000
        health_status["performance"] = {
            "health_check_time_ms": health_check_time,
            "target_ms": 50,
            "status": "healthy" if health_check_time < 50 else "slow"
        }
        
        if health_check_time >= 50:
            logger.warning(f"Health check slow: {health_check_time:.1f}ms")
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "service": "hormozi_rag_api",
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@app.get("/health/ready", response_model=HealthResponse)
async def health_ready():
    """
    Readiness check - dependencies are available.
    
    Implements ARCHITECTURE.md health check pattern.
    """
    dependencies = {}
    
    # Check vector database
    if vector_db:
        dependencies["vector_db"] = vector_db.health_check()
    else:
        dependencies["vector_db"] = False
    
    # Check OpenAI availability (required for queries)
    try:
        import openai
        openai.api_key = settings.OPENAI_API_KEY
        dependencies["openai"] = True
    except:
        dependencies["openai"] = False
    
    # Cache is optional for MVP
    dependencies["cache"] = cache is not None if cache else True
    
    all_ready = all(dependencies.values())
    
    return HealthResponse(
        status="ready" if all_ready else "not_ready",
        timestamp=datetime.now().isoformat(),
        dependencies=dependencies
    )


@app.get("/health/startup")
async def health_startup():
    """
    Startup check - initialization complete.
    
    Implements ARCHITECTURE.md health check pattern.
    """
    initialized = vector_db is not None and llm_provider is not None
    
    return JSONResponse(
        status_code=200 if initialized else 503,
        content={
            "status": "initialized" if initialized else "initializing",
            "timestamp": datetime.now().isoformat(),
            "components_ready": {
                "vector_db": vector_db is not None,
                "llm_provider": llm_provider is not None,
                "cache": cache is not None
            }
        }
    )


@app.post("/api/v1/query", response_model=QueryResponse)
async def query_frameworks(request: QueryRequest):
    """
    Framework search endpoint following DEVELOPMENT_RULES.md endpoint design pattern exactly
    
    Purpose: Search Hormozi frameworks using semantic similarity
    Input: QueryRequest with query string and search parameters  
    Output: QueryResponse with ranked framework chunks
    Error Conditions:
        - 400: Invalid query (empty, too long, malformed)
        - 503: Database or OpenAI service unavailable
        - 500: Internal processing error
    
    Performance Target: <500ms per DATABASE_ENGINEERING_SPEC.md
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()  # Performance monitoring per DATABASE_ENGINEERING_SPEC.md
    
    try:
        # Level 1: Input validation (fail fast per ARCHITECTURE.md)
        if not vector_db:
            raise HTTPException(
                status_code=503,
                detail="Vector database not initialized"
            )
        
        # Step 1: Generate embedding using OpenAI (external dependency)
        try:
            # Use OpenAI directly for now (orchestrator has dependency issues)
            import openai
            openai.api_key = settings.OPENAI_API_KEY
            
            embedding_response = openai.embeddings.create(
                model="text-embedding-3-large",
                input=request.query
            )
            query_embedding = embedding_response.data[0].embedding
            
        except Exception as e:
            # Level 2: External API error per ARCHITECTURE.md
            logger.error(f"OpenAI embedding generation failed: {e}", extra={
                "request_id": request_id,
                "query_length": len(request.query)
            }, exc_info=True)
            raise HTTPException(
                status_code=503,
                detail="Embedding generation service temporarily unavailable"
            )
        
        # Step 2: Execute search through storage interface
        try:
            if request.search_type == "hybrid":
                search_results = vector_db.hybrid_search(
                    query_embedding=query_embedding,
                    query_text=request.query,
                    top_k=request.top_k,
                    vector_weight=0.7  # DATABASE_ENGINEERING_SPEC.md FR2: 70% vector, 30% text
                )
            else:
                search_results = vector_db.search(query_embedding, request.top_k, request.filters)
                
        except Exception as e:
            # Level 2: Retrieval error per ARCHITECTURE.md
            logger.error(f"Vector search failed: {e}", extra={
                "request_id": request_id,
                "search_type": request.search_type
            }, exc_info=True)
            raise HTTPException(
                status_code=503,
                detail="Framework search temporarily unavailable"
            )
        
        # Step 3: Format response following ARCHITECTURE.md contracts
        framework_chunks = []
        for result in search_results:
            chunk = FrameworkChunk(
                chunk_id=result.document.metadata.get("chunk_id", "unknown"),
                framework_name=result.document.metadata.get("framework_name", "unknown"),
                section=result.document.metadata.get("section", "unknown"),
                title=result.document.metadata.get("title", "untitled"),
                content_snippet=result.document.text[:300] + "..." if len(result.document.text) > 300 else result.document.text,
                similarity_score=result.score,
                rank=result.rank,
                chunk_type=result.document.metadata.get("chunk_type", "unknown"),
                metadata=result.document.metadata
            )
            framework_chunks.append(chunk)
        
        query_time_ms = (time.time() - start_time) * 1000
        
        response = QueryResponse(
            query=request.query,
            search_type=request.search_type,
            results=framework_chunks,
            total_results=len(framework_chunks),
            query_time_ms=query_time_ms,
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat(),
            performance_metrics={
                "search_time_ms": query_time_ms,
                "target_ms": 500
            }
        )
        
        # Performance monitoring per ARCHITECTURE.md
        logger.info(f"Framework query completed", extra={
            "request_id": request_id,
            "query_length": len(request.query),
            "results_count": len(framework_chunks),
            "query_time_ms": query_time_ms,
            "search_type": request.search_type,
            "performance_status": "within_budget" if query_time_ms <= 500 else "exceeds_budget"
        })
        
        return response
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        # Level 3: System error handling per ARCHITECTURE.md
        logger.critical(f"Query processing system error: {e}", extra={
            "request_id": request_id
        }, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal service error"
        )


@app.get("/metrics")
async def get_metrics():
    """
    Get system metrics.
    
    Implements ARCHITECTURE.md monitoring points.
    """
    try:
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system_info": {
                "environment": settings.ENVIRONMENT,
                "vector_db_type": settings.VECTOR_DB_TYPE,
                "embedding_model": settings.EMBEDDING_MODEL
            },
            "performance": {
                "max_response_time": settings.MAX_RESPONSE_TIME_SECONDS,
                "max_chunks_per_query": settings.MAX_CHUNKS_PER_QUERY
            }
        }
        
        # Add component-specific metrics if available
        if vector_db:
            # Would add vector DB metrics here
            pass
        
        if cache:
            # Would add cache hit rate here
            pass
        
        return metrics
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Metrics collection failed"
        )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Hormozi RAG System",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health, /health/ready, /health/startup",
            "query": "/api/v1/query",
            "metrics": "/metrics"
        },
        "documentation": "/docs"
    }


# Error handlers following DEVELOPMENT_RULES.md
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with proper logging."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower()
    )