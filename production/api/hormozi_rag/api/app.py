"""
FastAPI for the Hormozi RAG system.

Follows ARCHITECTURE.md API Layer specification with proper health checks.
Implements DEVELOPMENT_RULES.md error handling hierarchy.
"""

import time
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    from fastapi import FastAPI, HTTPException, Query, Body, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
except ImportError:
    raise ImportError("fastapi not installed. Run: pip install fastapi uvicorn")

from ..config.settings import settings
from ..core.logger import get_logger
from ..storage.factory import StorageFactory
from ..generation.openai_provider import OpenAIProvider
from ..generation.interfaces import GenerationRequest, GenerationResponse

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

# Global components (initialized on startup)
vector_db = None
llm_provider = None
cache = None


# Pydantic models for API contracts
class QueryRequest(BaseModel):
    """Query request as per ARCHITECTURE.md contracts."""
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 5
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Query response as per ARCHITECTURE.md contracts."""
    answer: str
    sources: List[str]
    confidence: float
    metadata: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    dependencies: Dict[str, bool]


@app.on_event("startup")
async def startup_event():
    """
    Initialize system on startup.
    
    Follows ARCHITECTURE.md singleton services pattern.
    """
    global vector_db, llm_provider, cache
    
    try:
        logger.info("Initializing Hormozi RAG system...")
        
        # Initialize storage components
        vector_db = StorageFactory.create_vector_db()
        vector_db.initialize()
        
        cache = StorageFactory.create_cache()
        
        # Initialize generation component
        llm_provider = OpenAIProvider()
        
        logger.info("RAG system initialized successfully")
        
    except Exception as e:
        logger.critical(f"Failed to initialize RAG system: {e}")
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
    
    # Check LLM provider
    if llm_provider:
        dependencies["llm_provider"] = llm_provider.health_check()
    else:
        dependencies["llm_provider"] = False
    
    # Check cache
    if cache:
        dependencies["cache"] = cache.health_check()
    else:
        dependencies["cache"] = False
    
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


@app.post("/query", response_model=QueryResponse)
async def query_frameworks(request: QueryRequest):
    """
    Query the framework knowledge base.
    
    Follows ARCHITECTURE.md query processing pipeline.
    Implements DEVELOPMENT_RULES.md error handling hierarchy.
    """
    # Level 1: Input validation (fail fast)
    if not request.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty"
        )
    
    if not vector_db or not llm_provider:
        raise HTTPException(
            status_code=503,
            detail="System not ready - components not initialized"
        )
    
    start_time = time.time()
    
    try:
        # Step 1: Generate query embedding
        # (This would typically be done by a proper retrieval component)
        # For now, return a simple response
        
        # Step 2: Search vector database
        # query_embedding = await generate_embedding(request.query)
        # search_results = vector_db.search(query_embedding, top_k=request.limit)
        
        # Step 3: Generate response
        generation_request = GenerationRequest(
            query=request.query,
            context=[],  # Would be populated from search results
            history=[]
        )
        
        # For now, return a placeholder response
        response_time = time.time() - start_time
        
        return QueryResponse(
            answer="I'm a placeholder response. The manual framework extraction is needed to provide real answers.",
            sources=[],
            confidence=0.0,
            metadata={
                "response_time": response_time,
                "timestamp": datetime.now().isoformat(),
                "note": "Requires manual framework extraction to be completed"
            }
        )
        
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
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
            "health": "/health/live, /health/ready, /health/startup",
            "query": "/query",
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