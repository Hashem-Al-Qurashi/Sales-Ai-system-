# API Integration Plan with PostgreSQL System
## Senior Engineer Integration Architecture

**Date**: 2025-10-08  
**Current State**: PostgreSQL + pgvector operational  
**Target**: FastAPI service layer + MCP server integration  
**Integration Approach**: Leverage existing database foundation  

---

## 🎯 **INTEGRATION STRATEGY**

### **Pillar 1: PostgreSQL Foundation (✅ COMPLETE)**
**What we have:**
- PostgreSQL database `hormozi_rag` operational
- 6 tables with complete schema per DATABASE_ENGINEERING_SPEC.md
- 20 chunks + 20 real OpenAI 3072-dimensional embeddings
- Native pgvector cosine similarity working
- Sub-millisecond query performance validated

**Integration Points for API Layer:**
```python
# Database connection from production/config/.env:
POSTGRES_HOST=localhost
POSTGRES_DB=hormozi_rag  
POSTGRES_USER=rag_app_user
POSTGRES_PASSWORD=rag_secure_password_123

# Query patterns to implement in FastAPI:
semantic_search_query = """
    SELECT fd.chunk_id, fd.content, fm.framework_name,
           ce.embedding <-> %s as distance
    FROM framework_documents fd
    JOIN framework_metadata fm ON fd.id = fm.document_id
    JOIN chunk_embeddings ce ON fd.id = ce.document_id
    ORDER BY distance
    LIMIT %s
"""

text_search_query = """
    SELECT fd.chunk_id, fd.title, fd.content,
           ts_rank(to_tsvector('english', fd.content), query) as rank
    FROM framework_documents fd,
         plainto_tsquery('english', %s) query
    WHERE to_tsvector('english', fd.content) @@ query
    ORDER BY rank DESC
    LIMIT %s
"""
```

### **Pillar 2: FastAPI Service Layer (🔧 IMPLEMENT NEXT)**

#### **Core Service Architecture:**
```python
# production/api/main.py (NEW FILE)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import openai
import os

app = FastAPI(title="Hormozi RAG API", version="1.0.0")

class QueryRequest(BaseModel):
    query: str
    limit: int = 5
    
class FrameworkResult(BaseModel):
    chunk_id: str
    framework_name: str
    content_snippet: str
    relevance_score: float
    
@app.post("/query", response_model=List[FrameworkResult])
async def search_frameworks(request: QueryRequest):
    """Search Hormozi frameworks using semantic similarity"""
    
    # Generate embedding for query
    embedding = await generate_embedding(request.query)
    
    # Execute vector similarity search on PostgreSQL  
    results = await execute_vector_search(embedding, request.limit)
    
    # Format for API response
    return format_framework_results(results)
```

#### **Database Integration Layer:**
```python
# production/api/database.py (NEW FILE) 
import psycopg2
from contextlib import asynccontextmanager

class PostgreSQLClient:
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('POSTGRES_HOST'),
            'database': os.getenv('POSTGRES_DB'),
            'user': os.getenv('POSTGRES_USER'),
            'password': os.getenv('POSTGRES_PASSWORD')
        }
    
    @asynccontextmanager
    async def get_connection(self):
        conn = psycopg2.connect(**self.connection_params)
        try:
            yield conn
        finally:
            conn.close()
    
    async def semantic_search(self, query_embedding: List[float], limit: int):
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fd.chunk_id, fd.content, fm.framework_name,
                       ce.embedding <-> %s as distance
                FROM framework_documents fd
                JOIN framework_metadata fm ON fd.id = fm.document_id
                JOIN chunk_embeddings ce ON fd.id = ce.document_id
                ORDER BY distance
                LIMIT %s
            """, (query_embedding, limit))
            
            return cursor.fetchall()
```

### **Pillar 3: MCP Server Layer (🚀 FUTURE)**

#### **MCP Tools Implementation:**
```python
# future_mcp_server/hormozi_mcp.py (FUTURE FILE)
import mcp
import httpx

class HormoziMCPServer:
    def __init__(self, fastapi_url: str = "http://localhost:8000"):
        self.api_client = httpx.AsyncClient(base_url=fastapi_url)
    
    @mcp.tool()
    async def search_hormozi_frameworks(self, query: str) -> str:
        """
        Find relevant Hormozi frameworks for any business question
        
        Args:
            query: Business question like "How do I price higher?"
            
        Returns:
            Formatted framework recommendations with specific guidance
        """
        try:
            response = await self.api_client.post("/query", json={"query": query})
            results = response.json()
            
            # Format for Claude consumption
            formatted_response = "Based on Hormozi's frameworks:\n\n"
            for result in results[:3]:
                formatted_response += f"**{result['framework_name']}**:\n"
                formatted_response += f"{result['content_snippet']}\n\n"
            
            return formatted_response
            
        except Exception as e:
            return f"I encountered an issue accessing the Hormozi frameworks: {e}"
    
    @mcp.tool()
    async def analyze_offer_structure(self, 
                                    price: str,
                                    deliverables: List[str], 
                                    guarantee: str) -> str:
        """
        Analyze an offer against Hormozi's Grand Slam Offer principles
        
        Args:
            price: Offer price ("$2000")
            deliverables: List of what's included ["Course", "Templates"] 
            guarantee: Type of guarantee offered
            
        Returns:
            Framework-based analysis with improvement recommendations
        """
        offer_data = {
            "price": price,
            "deliverables": deliverables,
            "guarantee": guarantee
        }
        
        try:
            response = await self.api_client.post("/analyze-offer", json=offer_data)
            analysis = response.json()
            
            # Format analysis for Claude
            return format_offer_analysis_for_claude(analysis)
            
        except Exception as e:
            return f"Offer analysis unavailable: {e}"
```

---

## 🔄 **INTEGRATION FLOW**

### **User Journey: Claude Desktop → Results**

#### **Current State (Local Testing):**
```bash
User → Local Python Script → PostgreSQL → Results
```

#### **Phase 2 (API Service):**
```bash
User → HTTP Client → FastAPI → PostgreSQL → JSON Response
curl -X POST localhost:8000/query -d '{"query": "value equation"}'
```

#### **Phase 3 (MCP Integration):**
```bash
Claude Desktop → MCP Server → FastAPI → PostgreSQL → Claude Interface
"What's the value equation?" → search_hormozi_frameworks() → Formatted Response
```

---

## 🔧 **IMPLEMENTATION SEQUENCE**

### **Week 1: API Service Layer**

**Day 1-2: Core API Implementation**
- Create `production/api/main.py` with FastAPI app
- Implement `/query` endpoint with PostgreSQL integration
- Add basic error handling and validation

**Day 3-4: Production Features**  
- Add `/health` endpoint with database connectivity check
- Implement request logging and monitoring
- Add rate limiting and input validation

**Day 5: Integration Testing**
- Test API endpoints against existing PostgreSQL system
- Validate performance meets requirements (<500ms)
- Verify error handling for all failure scenarios

### **Week 2: MCP Server Layer**

**Day 1-2: MCP Server Setup**
- Create MCP server process structure
- Define tool schemas per Anthropic specification
- Implement HTTP bridge to FastAPI endpoints

**Day 3-4: Claude Desktop Integration**
- Configure Claude Desktop to connect to MCP server
- Test tool calling from Claude interface
- Validate error handling and timeout scenarios

**Day 5: End-to-End Validation**
- Test complete flow: Claude Desktop → MCP → FastAPI → PostgreSQL
- Performance validation under realistic usage
- Documentation and deployment preparation

---

## 📊 **SUCCESS METRICS**

### **API Service Layer Success:**
- ✅ `/query` endpoint responds in <500ms
- ✅ Health checks validate database connectivity
- ✅ Error handling prevents service crashes
- ✅ Request validation blocks malformed input
- ✅ Logging captures all query activity

### **MCP Integration Success:**
- ✅ Claude Desktop can call Hormozi framework tools
- ✅ Tools respond with formatted framework guidance  
- ✅ Error messages are user-friendly for Claude
- ✅ No browser switching required for Dan's workflow
- ✅ Context preserved across tool calls

---

## 🎯 **DEVELOPMENT APPROACH**

### **File Organization for Implementation:**
```
development/
├── api_implementation/           # Phase 2 development
│   ├── fastapi_endpoints.py    # API endpoint development
│   ├── database_integration.py # PostgreSQL query patterns
│   └── api_testing.py         # Endpoint validation
│
├── mcp_implementation/          # Phase 3 development  
│   ├── mcp_server_setup.py    # MCP server process
│   ├── tool_definitions.py    # Claude Desktop tool schemas
│   └── claude_integration.py  # End-to-end testing
│
└── experiments/                # POCs and testing
    ├── api_prototypes/         # FastAPI experiments
    └── mcp_prototypes/         # MCP integration tests
```

This approach ensures clean development without affecting the production PostgreSQL system.