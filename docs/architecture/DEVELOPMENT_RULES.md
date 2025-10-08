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

#### Integration Verification
```python
# Run these checks:
1. Does it work with existing code?
2. Does it break any contracts in ARCHITECTURE.md?
3. Are all edge cases handled?
4. Is it observable in production?
```

#### Performance Validation
```python
# Test with:
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