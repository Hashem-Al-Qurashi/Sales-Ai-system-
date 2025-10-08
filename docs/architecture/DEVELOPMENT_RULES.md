# Development Rules - Senior Engineering Standards

## The Prime Directive
**Before writing ANY code, ask yourself:**
1. Does this align with ARCHITECTURE.md?
2. Am I fixing the root cause or adding a patch?
3. What will break when this fails?
4. How will the next developer understand this?

## Anti-Patterns That MUST Be Avoided

### ❌ The Patch Pattern
```python
# WRONG - Adding patches
def process_query(query):
    try:
        result = retrieve(query)
    except:
        # Quick fix for production issue
        result = retrieve_backup(query)  # Now we have 2 retrieval paths
```

```python
# RIGHT - Fix the root cause
def process_query(query):
    retriever = RetrieverWithFallback(primary, backup)
    result = retriever.retrieve(query)  # Single path, configurable behavior
```

### ❌ The Hidden State Pattern
```python
# WRONG - State scattered everywhere
class Processor:
    def __init__(self):
        self.cache = {}  # State here
        
def process():
    global shared_data  # State here too
    config = json.load('config.json')  # And here
```

```python
# RIGHT - Single source of truth
class Processor:
    def __init__(self, state_manager: StateManager):
        self.state = state_manager  # All state through one interface
```

### ❌ The "It Works" Pattern
```python
# WRONG - No error handling
def embed_text(text):
    return model.encode(text)  # What if model fails?
```

```python
# RIGHT - Defensive programming
def embed_text(text):
    if not text or len(text) > MAX_LENGTH:
        raise ValueError(f"Invalid text length: {len(text)}")
    
    try:
        embedding = model.encode(text)
        if not validate_embedding(embedding):
            raise EmbeddingError("Invalid embedding generated")
        return embedding
    except ModelError as e:
        logger.error(f"Embedding failed: {e}")
        return fallback_embedding(text)
```

## The Senior Engineer's Checklist

### Before Starting Any Task

1. **Understand the Full Context**
   ```bash
   # ALWAYS run these first:
   - Read ARCHITECTURE.md
   - Check SYSTEM_STATE.md
   - Review DECISION_LOG.md
   - Understand existing patterns in the codebase
   ```

2. **Plan Before Coding**
   - Draw the data flow
   - Identify failure points
   - List assumptions
   - Define success metrics

3. **Check for Existing Solutions**
   - Is this problem already solved elsewhere?
   - Can we reuse/refactor existing code?
   - Are we creating duplication?

### During Implementation

#### Code Quality Rules

1. **Function Complexity**
   - Max 50 lines per function
   - Max 3 levels of nesting
   - Single responsibility
   - Clear input/output contracts

2. **Error Handling Hierarchy**
   ```python
   # Level 1: Input validation (fail fast)
   if not isinstance(data, dict):
       raise TypeError("Data must be dict")
   
   # Level 2: Business logic errors (recover gracefully)
   try:
       result = process(data)
   except ProcessingError as e:
       result = fallback_process(data)
       monitor.record_fallback()
   
   # Level 3: System errors (circuit breaker)
   @circuit_breaker(failure_threshold=5)
   def external_api_call():
       pass
   ```

3. **Configuration Management**
   ```python
   # WRONG
   CHUNK_SIZE = 1000  # Hardcoded
   
   # RIGHT
   CHUNK_SIZE = config.get("chunk_size", 1000)  # Configurable with default
   ```

4. **Logging Strategy**
   ```python
   # Strategic logging, not console.log everywhere
   logger.debug("Processing chunk", extra={"chunk_id": id, "size": size})
   logger.info("Query processed", extra={"latency": latency, "user": user_id})
   logger.error("Retrieval failed", extra={"error": e, "query": query}, exc_info=True)
   logger.critical("Database connection lost", extra={"retry_count": retries})
   ```

### After Implementation

## 🚨 FILE LIFECYCLE MANAGEMENT (MANDATORY)
**Added**: 2025-10-08 - Prevent project file chaos

### Before Creating ANY File:
1. **Categorize** (REQUIRED):
   ```
   production/   - Live system files (NEVER delete without backup)
   development/  - Active work (cleanup weekly)
   experiments/  - POCs/testing (auto-delete after 30 days)  
   migrations/   - One-time scripts (archive after completion)
   ```

2. **Document Purpose** (REQUIRED):
   ```python
   """
   FILE LIFECYCLE: production/development/experiment/migration
   PURPOSE: [specific problem this solves]
   REPLACES: [what file this supersedes, if any]
   CLEANUP_DATE: [when to review/delete, if temporary]
   """
   ```

3. **Name Convention** (REQUIRED):
   ```
   production/: stable_functional_names.py
   development/: feature_purpose.py  
   experiments/: test_idea_YYYYMMDD.py
   migrations/: migrate_feature_YYYYMMDD.py
   ```

4. **AI Integration Protocol** (CRITICAL):
   ```markdown
   MANDATORY AI INSTRUCTION:
   Before creating ANY file, AI MUST:
   1. Check if similar file exists (avoid duplicates)
   2. Ask which directory category this belongs to
   3. Document what problem this solves specifically
   4. Plan cleanup/lifecycle if temporary
   5. Get explicit approval for production/ files
   
   AI must ask: "This creates a [category] file for [purpose]. 
   Should I proceed?" before any file creation.
   ```

### Directory Structure Enforcement
```
project_root/
├── production/              # 🔒 PROTECTED - production system
│   ├── api/                # FastAPI application
│   ├── data/               # Production chunks  
│   ├── config/             # .env, requirements.txt
│   └── run_api.py          # Production entry point
├── development/            # 🔧 ACTIVE WORK - weekly cleanup
│   ├── scripts/            # Development utilities
│   └── experiments/        # POCs and testing
├── migrations/             # 📦 ONE-TIME - archive after use
│   └── YYYYMMDD_purpose/   # Dated migration folders
├── archive/                # 📚 HISTORICAL - safe storage
└── docs/                   # 📖 ARCHITECTURE - version controlled
```

### Lifecycle Rules
- **production/**: Changes require system verification
- **development/**: Review and cleanup every Friday  
- **experiments/**: Auto-review after 30 days
- **migrations/**: Archive immediately after successful completion

## 🌐 **API SERVICE LAYER DEVELOPMENT RULES**
**Added**: 2025-10-08 - For FastAPI service implementation

### **API Development Standards**

#### **1. Endpoint Design Principles**
```python
# REQUIRED: Every endpoint follows this pattern
@app.post("/endpoint")
async def endpoint_name(request: RequestModel) -> ResponseModel:
    """
    DOCSTRING REQUIRED:
    Purpose: What this endpoint does
    Input: RequestModel schema  
    Output: ResponseModel schema
    Error Conditions: What can fail and why
    """
    try:
        # Input validation (fail fast)
        validate_request(request)
        
        # Business logic (single responsibility)
        result = orchestrator.process(request)
        
        # Response formatting (consistent structure)
        return format_response(result)
        
    except ValidationError:
        raise HTTPException(400, "Input validation failed")
    except DatabaseError:
        raise HTTPException(503, "Database temporarily unavailable")
    except Exception as e:
        logger.error("Unexpected error", exc_info=True)
        raise HTTPException(500, "Internal service error")
```

#### **2. Database Integration Rules**
```python
# REQUIRED: PostgreSQL connection through environment
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST'),
        database=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'), 
        password=os.getenv('POSTGRES_PASSWORD')
    )

# REQUIRED: All queries use parameterized statements (no SQL injection)
cursor.execute(
    "SELECT * FROM framework_documents WHERE content ILIKE %s",
    (f"%{search_term}%",)  # Parameterized - REQUIRED
)

# FORBIDDEN: String concatenation in SQL
sql = f"SELECT * FROM table WHERE value = '{user_input}'"  # NEVER DO THIS
```

#### **3. Vector Search Implementation**
```python
# REQUIRED: Use native pgvector operations
def semantic_search(query_embedding: List[float], limit: int = 5):
    cursor.execute("""
        SELECT fd.chunk_id, fd.content, 
               ce.embedding <-> %s as distance
        FROM framework_documents fd
        JOIN chunk_embeddings ce ON fd.id = ce.document_id  
        ORDER BY distance
        LIMIT %s
    """, (query_embedding, limit))
    
    return cursor.fetchall()
```

#### **4. Error Response Standards**
```python
# REQUIRED: Consistent error response format
{
    "error": {
        "type": "ValidationError",
        "message": "Query parameter cannot be empty", 
        "details": {"field": "query", "received": ""},
        "request_id": "req_123456789",
        "timestamp": "2025-10-08T16:00:00Z"
    }
}
```

### **API Production Requirements**

#### **MANDATORY Features for API Service:**
1. **Request Validation**: Pydantic models for all input/output
2. **Error Handling**: Try/except with specific HTTP status codes  
3. **Logging**: Structured logging with request IDs
4. **Health Checks**: Database connectivity validation
5. **Rate Limiting**: IP-based throttling to prevent abuse
6. **Monitoring**: Response time and success rate tracking

#### **FORBIDDEN in API Layer:**
- Direct database connection strings (use environment variables)
- Unvalidated user input reaching database
- Generic exception handling (catch specific errors)
- Blocking I/O operations (use async/await)
- State storage in API handlers (stateless required)

## 🔌 **MCP SERVER INTEGRATION RULES**
**Added**: 2025-10-08 - For Claude Desktop integration

### **MCP Development Standards**

#### **1. Tool Definition Requirements**
```python
# REQUIRED: Every MCP tool follows this schema
{
    "name": "search_hormozi_frameworks",
    "description": "Find relevant Hormozi frameworks for business questions",
    "inputSchema": {
        "type": "object", 
        "properties": {
            "query": {"type": "string", "minLength": 1, "maxLength": 1000}
        },
        "required": ["query"]
    }
}

# Implementation MUST match schema exactly:
async def search_hormozi_frameworks(query: str) -> List[FrameworkResult]:
    if not query or len(query.strip()) == 0:
        raise ValueError("Query cannot be empty")
    
    # Call FastAPI service (not direct database)
    response = await http_client.post("/query", json={"query": query})
    return response.json()
```

#### **2. HTTP Bridge Pattern (REQUIRED)**
```python
# MCP Server MUST call FastAPI, not database directly
class MCPServer:
    def __init__(self, fastapi_url: str):
        self.api_client = HTTPClient(fastapi_url)  # Dependency injection
    
    async def search_frameworks(self, query: str):
        # Bridge to FastAPI - maintains single data flow
        return await self.api_client.post("/query", {"query": query})
```

#### **3. Error Handling for Claude Desktop**
```python
# REQUIRED: Convert API errors to user-friendly messages
try:
    result = await self.api_client.query(request)
    return format_for_claude(result)
    
except HTTPError as e:
    if e.status == 503:
        return "The Hormozi framework system is temporarily unavailable. Please try again in a moment."
    elif e.status == 429:
        return "Too many requests. Please wait a moment before asking again."
    else:
        return "I encountered an issue accessing the Hormozi frameworks. Let me try a different approach."
```

### **MCP Integration Requirements**

#### **MANDATORY for MCP Server:**
1. **Service Isolation**: MCP server separate process from FastAPI
2. **HTTP Communication**: All database access through FastAPI endpoints
3. **Error Translation**: Technical errors → User-friendly Claude messages
4. **Timeout Handling**: Graceful handling of slow API responses
5. **Tool Documentation**: Clear descriptions for Claude understanding

#### **FORBIDDEN in MCP Layer:**
- Direct database connections (must go through FastAPI)
- Exposing technical error messages to Claude Desktop
- Blocking operations without timeouts
- State management (delegate to FastAPI/database)
- Complex business logic (belongs in API layer)

## 🧪 **MANDATORY TESTING DISCIPLINE** (CRITICAL)
**Added**: 2025-10-08 - Ensure maximum efficiency with system reliability

### **HYBRID TESTING APPROACH:**
1. **Critical Path Testing**: Test 20% that breaks 80% of functionality (IMMEDIATE)
2. **TDD for New Features**: All future implementations use Test-Driven Development (ONGOING)
3. **Integration Validation**: Verify component boundaries and system integration (EVERY CHANGE)

### **CRITICAL PATH TESTING (MUST HAVE - MANDATORY)**
**The 20% that breaks 80% of functionality:**

#### **Test 1: PostgreSQL Connection and Queries**
```python
def test_postgresql_critical_path():
    """Test database operations that everything depends on"""
    # 1. Connection pool initialization
    # 2. Vector search query execution  
    # 3. Health check query performance (<50ms)
    # 4. Data integrity validation (20 docs, 20 embeddings, 3072 dims)
    # RESULT: Database foundation works or system is broken
```

#### **Test 2: FastAPI Endpoints (/query, /health)**
```python 
def test_fastapi_critical_endpoints():
    """Test API endpoints that Dan's team will use"""
    # 1. /health returns healthy status with database checks
    # 2. /api/v1/query accepts valid requests and returns frameworks
    # 3. Error handling for invalid requests (empty query, bad top_k)
    # 4. Performance within DATABASE_ENGINEERING_SPEC.md targets
    # RESULT: API service works or Dan cannot use system
```

#### **Test 3: OpenAI Embedding Generation**  
```python
def test_openai_embedding_integration():
    """Test OpenAI API integration critical to all queries"""
    # 1. API key validation and connectivity
    # 2. text-embedding-3-large model response
    # 3. 3072-dimensional embedding generation
    # 4. Error handling for API failures
    # RESULT: Embeddings work or semantic search fails
```

#### **Test 4: End-to-End Query Validation**
```python
def test_end_to_end_critical_queries():
    """Test complete workflow with Dan's actual use cases"""
    # 1. "value equation" → returns value_equation_complete_framework_010
    # 2. "pricing strategy" → returns premium_pricing_philosophy_008  
    # 3. "compelling offers" → returns problems_solutions_framework_012
    # 4. Response format matches QueryResponse contract
    # RESULT: Dan gets right frameworks or system provides no value
```

### **TEST-DRIVEN DEVELOPMENT (TDD) FOR NEW FEATURES**
**MANDATORY for all future implementations:**

#### **Red-Green-Refactor Process:**
```python
# STEP 1: RED - Write failing test first
def test_new_feature():
    """Test what the new feature should do"""
    result = new_feature_function("input")
    assert result == "expected_output"
    # This test FAILS initially

# STEP 2: GREEN - Implement minimum code to pass
def new_feature_function(input):
    return "expected_output"  # Simplest implementation
    # Now test PASSES

# STEP 3: REFACTOR - Optimize while keeping test passing  
def new_feature_function(input):
    # Production-quality implementation
    # Test still PASSES
```

### **INTEGRATION TESTING (EVERY COMPONENT BOUNDARY)**
**MANDATORY for component interaction:**

#### **Component Integration Matrix:**
```python
# Test 1: Storage ↔ Database
def test_storage_database_integration():
    """Verify storage interface works with actual PostgreSQL"""

# Test 2: API ↔ Storage  
def test_api_storage_integration():
    """Verify FastAPI uses storage interface correctly"""

# Test 3: MCP ↔ API (Day 2)
def test_mcp_api_integration():
    """Verify MCP server calls FastAPI correctly"""

# Test 4: Claude ↔ MCP (Day 3)
def test_claude_mcp_integration():
    """Verify Claude Desktop tool calling works"""
```

### **TESTING DOCUMENTATION (MANDATORY)**
**Every test execution must be documented:**

#### **Test Execution Report Template:**
```markdown
## Test Execution Report - [COMPONENT/FEATURE]
**Date**: [DATE]
**Component**: [What was tested]
**Test Type**: Critical Path / Integration / Performance
**Status**: PASS / FAIL / DEGRADED

### Test Scenarios:
1. [Scenario]: [Expected] → [Actual] → [PASS/FAIL]
2. [Scenario]: [Expected] → [Actual] → [PASS/FAIL]

### Performance Results:
- [Metric]: [Result] (target: [Target]) → [PASS/FAIL]

### Integration Validation:
- [Component A] ↔ [Component B]: [PASS/FAIL]

### Issues Found:
- [Issue]: [Description] → [Resolution/Status]

### Regression Validation:
- [Existing functionality]: [CONFIRMED WORKING/BROKEN]
```

### **AI IMPLEMENTATION PROTOCOL (ENHANCED)**
**MANDATORY for all AI implementations:**

```markdown
## AI TESTING PROTOCOL (MANDATORY)
Before saying "implementation complete", AI MUST:

### Phase 1: Implementation
1. Build feature following ARCHITECTURE.md contracts
2. Follow DEVELOPMENT_RULES.md patterns exactly

### Phase 2: Critical Path Testing  
1. Create test suite covering 20% that breaks 80% of functionality
2. Execute tests and validate all pass
3. Document test results with metrics

### Phase 3: Integration Validation
1. Test component boundaries with existing system
2. Verify no regressions in existing functionality  
3. Validate performance against DATABASE_ENGINEERING_SPEC.md

### Phase 4: Documentation
1. Create test execution report with results
2. Document any issues found and resolutions
3. Update system integration status

### AI Must Ask:
"Implementation complete. Testing shows [RESULTS]. 
 Integration with [COMPONENTS] validated. 
 Performance: [METRICS]. 
 Any regressions: [YES/NO]. 
 Errors found and documented: [COUNT]. 
 Ready to proceed?"

NO EXCEPTIONS. NO SHORTCUTS. NO "WORKS ON MY MACHINE."

## 🚨 **ERROR DOCUMENTATION DISCIPLINE** (MANDATORY)
**Added**: 2025-10-08 - Every error must be tracked and documented

### **MANDATORY ERROR TRACKING:**
**Every error encountered during implementation MUST be documented with:**

#### **Error Discovery Template:**
```markdown
### Error [NUMBER]: [ERROR_TYPE] - [BRIEF_DESCRIPTION]
**Date Found**: [TIMESTAMP]
**Discovered During**: [Testing Phase / Implementation Step]
**Discovery Method**: [How was this found? Manual testing / Automated test / User report]

**Error Details**:
- **Symptoms**: What behavior was observed?
- **Root Cause**: What actually caused this error?
- **Impact Scope**: What functionality was affected?
- **Severity**: CRITICAL / HIGH / MEDIUM / LOW

**Resolution**:
- **Fix Applied**: What changes were made?
- **Verification**: How was fix validated?
- **Prevention**: How to prevent similar errors?
- **Status**: FIXED / IN PROGRESS / DEFERRED

**Learning**:
- **Detection Method**: How can we catch this type of error earlier?
- **Process Improvement**: What process changes prevent recurrence?
```

#### **Error Severity Classification:**
```
CRITICAL: System cannot function (database connection failure)
HIGH: Core functionality broken (query endpoint returns 500)  
MEDIUM: Degraded functionality (slow performance, validation errors)
LOW: Minor issues (logging warnings, cosmetic problems)
```

### **ERROR REPORTING INTEGRATION:**

#### **In Test Execution Reports:**
```markdown
## Error Analysis Section (MANDATORY)

### Errors Discovered During Testing:
1. **Error**: [Description]
   **Found**: [How/When] → **Fixed**: [Resolution] → **Status**: [VERIFIED/PENDING]

### Error Pattern Analysis:
- **Most Common**: [Error type] ([count] occurrences)  
- **Highest Impact**: [Error description] ([impact])
- **Detection Rate**: [errors found in testing] / [errors found in production]

### Process Improvements:
- **Enhanced Detection**: [What tests/checks were added]
- **Prevention Measures**: [What process changes prevent recurrence]
```

#### **In Architecture Documentation:**
```markdown
## Known Issues Register (Live Document)

| Error ID | Description | Status | Impact | Detection Method | Resolution |
|----------|-------------|--------|--------|------------------|------------|
| ERR-001 | Pydantic validation failure | FIXED | Query blocking | Manual testing | Allow negative similarity |
| ERR-002 | Configuration path issues | FIXED | Startup failure | Import errors | Fixed PROJECT_ROOT path |
```

### **AUTOMATED ERROR COLLECTION:**
```python
# Add to every component following DEVELOPMENT_RULES.md:

class ErrorTracker:
    """Systematic error tracking and documentation"""
    
    def __init__(self, component_name: str):
        self.component = component_name
        self.errors_found = []
    
    def log_error(self, error_type: str, description: str, 
                  severity: str, discovery_method: str):
        """Log error with full context for documentation"""
        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "component": self.component,
            "error_type": error_type,
            "description": description,
            "severity": severity,
            "discovery_method": discovery_method,
            "resolved": False
        }
        self.errors_found.append(error_entry)
        
    def mark_resolved(self, error_index: int, resolution: str):
        """Mark error as resolved with resolution details"""
        if error_index < len(self.errors_found):
            self.errors_found[error_index]["resolved"] = True
            self.errors_found[error_index]["resolution"] = resolution
            self.errors_found[error_index]["resolved_at"] = datetime.utcnow().isoformat()
```
```

## 🚨 **CRITICAL ENFORCEMENT MECHANISM:**

### **Updated File Lifecycle Management:**
```markdown
## ENHANCED FILE LIFECYCLE RULES
Before creating ANY file, AI MUST ask:

1. **Category**: production/development/experiments/migrations?
2. **Purpose**: What specific problem does this solve?
3. **Testing Plan**: How will this be validated?
4. **Integration Impact**: What existing components are affected?
5. **Performance Impact**: How does this affect system performance?

After creating ANY file, AI MUST:
1. Create corresponding test file in same directory structure
2. Execute test suite and document results
3. Verify integration with existing system
4. Document any performance impact or regressions
```

## 🎯 **IMMEDIATE ACTION PLAN:**

### **Step 1: Document Testing Rules (Now)**
Add comprehensive testing requirements to DEVELOPMENT_RULES.md

### **Step 2: Retrofit Day 1 with Critical Path Tests (Today)**
Create focused test suite covering the 20% that matters most

### **Step 3: Establish TDD Process (Going Forward)**
All new implementations use Test-First approach

### **Step 4: Integration Matrix (This Week)**
Test all component boundaries as we add MCP layer

## **🤔 SENIOR ENGINEER ASSESSMENT:**

**Your hybrid approach is sound, but I recommend:**

### **80/20 Focus for Efficiency:**
- **80% effort** on critical path testing (what Dan actually uses)
- **20% effort** on comprehensive coverage (background reliability)

### **Immediate vs. Comprehensive:**
- **Test Day 1 critical paths today** (2-3 hours)
- **Build comprehensive coverage incrementally** (avoid analysis paralysis)
- **Focus on Dan's workflow first** (value delivery)

## **❓ DO YOU AGREE WITH THIS REFINEMENT?**

**Hybrid approach with 80/20 focus:**
1. **Critical path testing today** (essential functionality)
2. **TDD for all new features going forward** (systematic quality)
3. **Comprehensive testing built incrementally** (sustainable)

**Or do you want full comprehensive testing of everything before proceeding?**

**I can implement either approach - what's your preference for balancing quality with delivery speed?**
- Minimal data (1 document)
- Normal load (100 documents)  
- Stress test (10,000 documents)
- Edge cases (empty, malformed, huge)
```

## Testing Philosophy

### Test Pyramid
```
        /\
       /  \       5% - End-to-end tests
      /    \
     /──────\     20% - Integration tests  
    /        \
   /──────────\   75% - Unit tests
```

### What to Test
```python
# RIGHT - Test behavior
def test_retriever_returns_relevant_chunks():
    chunks = retriever.retrieve("sales techniques")
    assert all(c.score > 0.7 for c in chunks)
    assert len(chunks) <= MAX_CHUNKS

# WRONG - Test implementation
def test_retriever_uses_cosine_similarity():
    assert retriever.similarity_fn == cosine  # Who cares?
```

## Refactoring Triggers

### Immediate Refactoring Required
1. Duplicate code appears 3rd time
2. Function exceeds 50 lines
3. Class has more than 7 methods
4. More than 3 levels of nesting
5. "Temporary" fix exists for >1 week

### Refactoring Process
```python
# 1. Write tests for current behavior
# 2. Refactor in small steps
# 3. Verify tests still pass
# 4. Update documentation
# 5. Record in DECISION_LOG.md
```

## Production Readiness Checklist

### Before Marking Feature Complete

- [ ] **Error Handling**
  - All exceptions caught and handled
  - Graceful degradation implemented
  - Circuit breakers for external services

- [ ] **Performance**
  - Load tested with 10x expected volume
  - Memory leaks verified absent
  - Database queries optimized (N+1 checked)

- [ ] **Observability**
  - Metrics exposed for monitoring
  - Structured logging implemented
  - Tracing spans added for debugging

- [ ] **Security**
  - Input validation on all endpoints
  - SQL injection impossible
  - Secrets in environment, not code
  - Rate limiting implemented

- [ ] **Documentation**
  - ARCHITECTURE.md updated if needed
  - SYSTEM_STATE.md updated
  - API docs generated
  - Runbook for operations team

## Code Review Rules

### What We Check For

1. **Architecture Alignment**
   - Does this follow ARCHITECTURE.md?
   - Are contracts maintained?
   - Is data flow unidirectional?

2. **Production Concerns**
   - What happens at scale?
   - How do we monitor this?
   - Can we roll back?

3. **Maintainability**
   - Will a new developer understand this?
   - Is it testable?
   - Is it configurable?

### Automatic Rejection Criteria
- No error handling
- No tests
- Breaks existing contracts
- Hardcoded configuration
- Console.log debugging left in
- Commented-out code
- TODO without ticket number

## The 10 Commandments of Senior Engineering

1. **Thou shalt not patch** - Fix root causes
2. **Thou shalt handle errors** - Every operation can fail
3. **Thou shalt test behavior** - Not implementation
4. **Thou shalt make it configurable** - Hard-coding is sin
5. **Thou shalt document decisions** - Future you will thank you
6. **Thou shalt refactor regularly** - Technical debt compounds
7. **Thou shalt monitor everything** - If you can't measure it, you can't improve it
8. **Thou shalt think about scale** - 10x growth should not require rewrite
9. **Thou shalt keep it simple** - Complexity is the enemy
10. **Thou shalt leave it better** - Every commit improves the codebase

## Continuous Learning

### After Each Feature
1. What went wrong?
2. What could be better?
3. What pattern emerged?
4. Update these rules

### Weekly Architecture Review
- Is ARCHITECTURE.md still accurate?
- Any technical debt accumulating?
- Any patterns that need abstracting?
- Any bottlenecks emerging?

## Emergency Protocol

### When Things Break in Production
1. **Stabilize** - Stop the bleeding
2. **Diagnose** - Find root cause
3. **Fix** - Implement proper solution
4. **Document** - Update runbook
5. **Postmortem** - What can we learn?

### When You're Stuck
1. Re-read ARCHITECTURE.md
2. Check if you're solving the right problem
3. Look for similar patterns in codebase
4. Consider if this complexity is necessary
5. Ask: "What would a 10x engineer do?"

## Remember
- **Every line of code is a liability**
- **The best code is no code**
- **Make it work, make it right, make it fast** (in that order)
- **You're not done when it works, you're done when it's right**