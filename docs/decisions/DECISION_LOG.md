# Architectural Decision Log

This log records all significant architectural decisions made during development. Each entry explains what was decided, why, and what alternatives were considered.

---

## Decision Template
```markdown
### [DATE] - [DECISION TITLE]
**Status**: [Proposed | Accepted | Deprecated | Superseded]
**Context**: What problem are we solving?
**Decision**: What did we decide?
**Consequences**: What are the implications?
**Alternatives Considered**: What else did we evaluate?
**Review Date**: When should we revisit this?
```

---

## Decisions

### 2025-10-04 - Documentation-First Development Approach
**Status**: Accepted
**Context**: AI-assisted development tends to accumulate technical debt through patches and quick fixes without maintaining system understanding.

**Decision**: Establish four core documentation files that must be maintained:
- ARCHITECTURE.md - System design source of truth
- DEVELOPMENT_RULES.md - Senior engineering standards
- SYSTEM_STATE.md - Current implementation status
- DECISION_LOG.md - This file

**Consequences**: 
- Every change must align with documented architecture
- Increased upfront documentation overhead
- Reduced technical debt accumulation
- Better system understanding maintained over time

**Alternatives Considered**:
1. Code-first with documentation later - Rejected: Leads to drift
2. Inline documentation only - Rejected: No bird's eye view
3. External wiki - Rejected: Gets out of sync

**Review Date**: 2025-11-04

---

### 2025-10-04 - Modular RAG Architecture
**Status**: Accepted
**Context**: Need a scalable, maintainable architecture for the Hormozi RAG system that can evolve without major rewrites.

**Decision**: Implement a layered architecture with clear boundaries:
- API Layer (FastAPI)
- Orchestration Layer (Coordinates retrieval + generation)
- Retrieval Engine (Vector search + reranking)
- Generation Engine (LLM integration)
- Storage Layer (Vector DB + Document store + Cache)

**Consequences**:
- Clear separation of concerns
- Easy to swap components (e.g., different vector DB)
- Potential performance overhead from abstraction
- More initial setup complexity

**Alternatives Considered**:
1. Monolithic single-file implementation - Rejected: Not scalable
2. Microservices architecture - Rejected: Over-engineering for current scale
3. Direct LangChain implementation - Rejected: Too opaque, hard to debug

**Review Date**: 2025-11-04

---

### PENDING - Vector Database Selection
**Status**: Proposed
**Context**: Need to choose between Chroma, Pinecone, and Weaviate for vector storage.

**Decision**: [To be made]

**Evaluation Criteria**:
1. **Chroma**
   - Pros: Local development, no API costs, fast iteration
   - Cons: Not production-scale, limited features
   
2. **Pinecone**
   - Pros: Production-ready, managed service, good performance
   - Cons: Costs, vendor lock-in, network latency
   
3. **Weaviate**
   - Pros: Self-hosted option, rich features, good performance
   - Cons: Operational overhead, complexity

**Recommendation**: Start with Chroma for development, abstract interface to allow Pinecone for production

**Review Date**: After POC completion

---

### 2025-10-04 - Embedding Model Selection
**Status**: Accepted
**Context**: Choose between OpenAI, Cohere, and open-source embedding models for the Hormozi RAG system.

**Decision**: Use OpenAI text-embedding-3-large for MVP implementation

**Reasoning**:
1. **Quality**: Best-in-class embedding quality for semantic search
2. **Integration**: Seamless integration with existing OpenAI infrastructure
3. **Dimensions**: 3072 dimensions provide excellent semantic representation
4. **Proven**: Battle-tested in production RAG systems

**Consequences**:
- API dependency on OpenAI (acceptable for MVP)
- Cost per embedding call (~$0.00013/1K tokens)
- Requires internet connectivity
- Need API key management

**Alternatives Considered**:
1. **OpenAI text-embedding-ada-002** - Rejected: Lower quality than 3-large
2. **Cohere Embed** - Rejected: Additional vendor complexity
3. **Sentence Transformers** - Rejected: Insufficient quality for Hormozi content

**Implementation**:
- API key configured in environment variables
- Model: text-embedding-3-large
- Batch size: 100 for efficiency
- Caching enabled for cost optimization

**Review Date**: 2025-11-04 (evaluate cost optimization options)

---

### 2025-10-04 - Chunking Strategy for 100+ Page Books
**Status**: Accepted
**Context**: Design optimal chunking strategy for Hormozi's books (138+ pages, 650k+ characters) while preserving business frameworks.

**Decision**: Implement Multi-Tier Adaptive Chunking with Framework Preservation

**Strategy Overview**:
1. **Framework-First Approach**: Detect and preserve complete business frameworks
2. **Hierarchical Chunking**: Chapter → Section → Paragraph levels
3. **Adaptive Sizing**: Different chunk sizes for different content types
4. **Context Enrichment**: Rich metadata and overlap management

**Technical Implementation**:
- **Tier 1**: Framework chunks (2000-3500 chars, never split)
- **Tier 2**: Chapter chunks (1500-2500 chars)
- **Tier 3**: Section chunks (1200-1800 chars)
- **Tier 4**: Paragraph chunks (500-1500 chars, fallback)

**Framework Preservation Rules**:
- **GOLD Frameworks** (never split): Value Equation, Offer Stack, Guarantee Framework
- **SILVER Frameworks** (smart split): Pricing Psychology, Scarcity/Urgency
- **Context Windows**: 200 char overlap + before/after context

**Data Pipeline**:
```
PDF → Enhanced Extractor → Framework Detector → Multi-Tier Chunker → Context Enricher → Quality Validator → Storage
```

**Expected Output**:
- ~450 total chunks from both books
- ~60 high-priority framework chunks
- 100% framework integrity preservation
- >95% context preservation quality

**Consequences**:
- **Pros**: Perfect framework preservation, optimal retrieval quality, rich context
- **Cons**: Complex implementation, higher processing time (~3min vs 30sec)
- **Trade-off**: Processing complexity for retrieval quality

**Alternatives Considered**:
1. **Simple fixed-size chunking** - Rejected: Would split frameworks
2. **Sentence-based chunking** - Rejected: Too granular, context loss
3. **Page-based chunking** - Rejected: Arbitrary boundaries, framework splits
4. **Token-based chunking** - Rejected: Doesn't respect semantic boundaries

**Quality Targets**:
- Framework completeness: 100%
- Context preservation: >95%
- Retrieval precision: >90%
- Processing time: <3 minutes

**Implementation Plan**:
1. **Phase 1**: Enhanced extraction (2 days)
2. **Phase 2**: Framework detection (2 days)
3. **Phase 3**: Multi-tier chunking (3 days)
4. **Phase 4**: Quality validation (1 day)

**Monitoring**:
- Chunk size distribution
- Framework detection accuracy
- Context overlap quality
- Processing performance metrics

**Review Date**: 2025-11-04 (after processing first book and measuring quality)

---

## Deprecated Decisions

### [DATE] - [DEPRECATED DECISION]
**Original Decision**: What was decided
**Deprecation Reason**: Why it didn't work
**Replacement**: What we're doing instead
**Lessons Learned**: What we learned

---

## Review Schedule

### Monthly Review Topics
- Performance bottlenecks
- Cost optimization opportunities
- New technology evaluations
- Technical debt assessment

### Quarterly Review Topics
- Architecture alignment
- Scalability assessment
- Security review
- Vendor evaluation

---

## Decision Principles

When making architectural decisions, consider:

1. **Simplicity First**: Can we solve this with less complexity?
2. **Future Flexibility**: Will this decision limit us later?
3. **Operational Cost**: What's the total cost of ownership?
4. **Team Capability**: Can the team maintain this?
5. **Production Readiness**: How does this affect reliability?
6. **Performance Impact**: Will this meet our SLAs?
7. **Security Implications**: Does this introduce vulnerabilities?
8. **Reversibility**: How hard is it to change this decision?

---

## Quick Decision Framework

For rapid decisions, ask:
1. Is this a one-way door? (Hard to reverse)
2. What's the blast radius if wrong?
3. Can we prototype quickly?
4. What would we regret not trying?

**Type 1 Decisions** (One-way doors, high impact):
- Require thorough analysis
- Document thoroughly
- Get team consensus

**Type 2 Decisions** (Reversible, low impact):
- Make quickly
- Document briefly
- Iterate based on results

---

## Technical Debt Register

Track decisions that intentionally create debt:

| Date | Decision | Debt Created | Payback Plan | Due Date |
|------|----------|--------------|--------------|----------|
| TBD | Use SQLite for MVP | No production DB | Migrate to PostgreSQL | Before launch |
| TBD | Skip authentication | No user management | Add auth layer | Before beta |
| TBD | Hardcode prompts | No prompt versioning | Create prompt management | Month 2 |

---

## Decision Anti-Patterns to Avoid

### ❌ "We'll Fix It Later"
- Without a concrete plan and date, it never gets fixed

### ❌ "Good Enough For Now"
- Define what "good enough" means and when to revisit

### ❌ "Everyone Does It This Way"
- Our context might be different

### ❌ "The Framework Handles It"
- Understand what the framework is actually doing

### ❌ "It's Temporary"
- Nothing is more permanent than a temporary solution

---

## How to Use This Log

### Before Making a Decision
1. Check if similar decision exists
2. Review principles and framework
3. Consider alternatives

### After Making a Decision
1. Document immediately
2. Set review date
3. Update SYSTEM_STATE.md if needed
4. Communicate to team

### During Reviews
1. Check decisions due for review
2. Assess if context has changed
3. Update or deprecate as needed
4. Document lessons learned