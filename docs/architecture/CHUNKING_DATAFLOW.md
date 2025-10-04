# Chunking Pipeline Data Flow

## Overview
This document details the data flow for processing 100+ page Hormozi books through our multi-tier chunking system.

## Complete Data Flow Diagram

```
📚 INPUT: PDF FILES (138 pages × 2 books = 650k+ characters)
│
▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: EXTRACTION                         │
│                                                                 │
│  📄 Enhanced PDF Extractor                                     │
│  ├── Text Extraction (pdfplumber)                             │
│  ├── Structure Detection (chapters, sections)                  │
│  ├── Formatting Preservation (bold, headers)                   │
│  └── Page Mapping (char → page number)                        │
│                                                                 │
│  OUTPUT: StructuredDocument                                     │
│  {                                                             │
│    text: str (650k chars),                                    │
│    structure: {chapters: [], sections: []},                   │
│    formatting: {bold_spans: [], headers: []},                 │
│    page_map: {char_offset: page_num}                          │
│  }                                                             │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│                 PHASE 2: FRAMEWORK DETECTION                   │
│                                                                 │
│  🧠 Framework Pattern Matcher                                  │
│  ├── Value Equation Detection                                  │
│  │   └── Patterns: ["Value =", "Dream Outcome", etc.]        │
│  ├── Offer Stack Detection                                     │
│  │   └── Patterns: ["identify dream outcome", "5 steps"]     │
│  ├── Guarantee Framework Detection                             │
│  │   └── Patterns: ["unconditional", "anti-guarantee"]       │
│  └── Pricing Psychology Detection                              │
│      └── Patterns: ["divergent pricing", "price anchor"]      │
│                                                                 │
│  OUTPUT: FrameworkMap                                           │
│  {                                                             │
│    "value_equation": [(start_char, end_char, priority)],      │
│    "offer_stack": [(start_char, end_char, priority)],         │
│    "guarantees": [(start_char, end_char, priority)]           │
│  }                                                             │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 3: SMART CHUNKING                      │
│                                                                 │
│  🎯 Multi-Tier Chunker                                         │
│  │                                                             │
│  ├── TIER 1: Framework Chunks (Priority)                      │
│  │   ├── Value Equation → Complete chunk (2000-2500 chars)   │
│  │   ├── Offer Stack → Complete chunk (2500-3500 chars)      │
│  │   └── Guarantees → Complete chunk (2000-3000 chars)       │
│  │                                                             │
│  ├── TIER 2: Chapter Chunks                                   │
│  │   ├── Introduction → Standard chunks (1500 chars)         │
│  │   ├── Implementation → Process chunks (2000 chars)        │
│  │   └── Examples → Example chunks (1000-1500 chars)         │
│  │                                                             │
│  ├── TIER 3: Section Chunks                                   │
│  │   ├── Concepts → Semantic chunks (1200-1800 chars)        │
│  │   ├── Tactics → Tactical chunks (800-1500 chars)          │
│  │   └── Stories → Narrative chunks (1000-2000 chars)        │
│  │                                                             │
│  └── TIER 4: Paragraph Chunks (Fallback)                     │
│      └── Remaining text → Standard chunks (1500 chars)        │
│                                                                 │
│  OUTPUT: RawChunks[]                                           │
│  [                                                             │
│    {id, text, start_char, end_char, tier, type},             │
│    ...400-500 chunks                                          │
│  ]                                                             │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│                 PHASE 4: CONTEXT ENRICHMENT                    │
│                                                                 │
│  📋 Context Enricher                                           │
│  ├── Add Chunk Metadata                                        │
│  │   ├── Book/Chapter/Section identification                  │
│  │   ├── Framework classification                             │
│  │   ├── Content type (definition/example/process)           │
│  │   └── Priority level (GOLD/SILVER/BRONZE)                 │
│  │                                                             │
│  ├── Create Context Overlaps                                   │
│  │   ├── Previous context (100 chars before)                 │
│  │   ├── Next context (100 chars after)                      │
│  │   └── Overlap tracking (which chunks overlap)             │
│  │                                                             │
│  ├── Add Cross-References                                      │
│  │   ├── Related frameworks                                   │
│  │   ├── Supporting examples                                  │
│  │   └── Implementation steps                                 │
│  │                                                             │
│  └── Generate Unique IDs                                       │
│      └── Format: "book_chapter_framework_sequence"            │
│                                                                 │
│  OUTPUT: EnrichedChunks[]                                      │
│  [                                                             │
│    {                                                           │
│      chunk_id: "100m_ch3_value_eq_001",                      │
│      text: "Value equation text...",                          │
│      metadata: {                                              │
│        book: "$100M Offers",                                  │
│        chapter: "Chapter 3",                                  │
│        framework: "value_equation",                           │
│        priority: "GOLD",                                      │
│        content_type: "definition",                            │
│        page_range: [45, 47],                                  │
│        char_count: 2340,                                      │
│        overlap_with: ["100m_ch3_value_eq_002"],              │
│        concepts: ["dream_outcome", "likelihood"],             │
│        context_before: "Previous context...",                 │
│        context_after: "Next context..."                       │
│      },                                                        │
│      embedding: null                                          │
│    }                                                           │
│  ]                                                             │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 5: QUALITY VALIDATION                  │
│                                                                 │
│  ✅ Quality Validator                                          │
│  ├── Framework Integrity Check                                 │
│  │   └── Ensure frameworks are never split                    │
│  ├── Completeness Validation                                   │
│  │   └── Check for orphaned content                           │
│  ├── Coherence Testing                                         │
│  │   └── Verify chunks make sense in isolation                │
│  ├── Overlap Validation                                        │
│  │   └── Ensure proper context preservation                   │
│  └── Metadata Consistency                                      │
│      └── Verify all required metadata present                 │
│                                                                 │
│  QUALITY GATES:                                                │
│  ✓ Framework completeness: 100%                               │
│  ✓ Context preservation: >95%                                 │
│  ✓ Metadata completeness: 100%                                │
│  ✓ Chunk coherence: >90%                                      │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 6: STORAGE PREP                       │
│                                                                 │
│  💾 Storage Formatter                                          │
│  ├── Generate Final IDs                                        │
│  ├── Serialize Metadata                                        │
│  ├── Prepare for Embedding                                     │
│  └── Create Database Records                                   │
│                                                                 │
│  OUTPUT: FinalChunks[]                                         │
│  Ready for: Embedder → VectorDB                               │
└─────────────────────────────────────────────────────────────────┘
│
▼
📊 METRICS & MONITORING
├── Total chunks created: ~450 chunks
├── Framework chunks: ~60 (high-priority)
├── Processing time: <3 minutes
├── Quality score: >95%
└── Ready for embedding pipeline
```

## Data Structures

### StructuredDocument
```python
@dataclass
class StructuredDocument:
    text: str
    structure: Dict[str, List[TextSpan]]
    formatting: Dict[str, List[FormatSpan]]
    page_map: Dict[int, int]  # char_offset → page_number
    metadata: Dict[str, Any]
```

### FrameworkSpan
```python
@dataclass
class FrameworkSpan:
    framework_type: str  # "value_equation", "offer_stack", etc.
    start_char: int
    end_char: int
    priority: str  # "GOLD", "SILVER", "BRONZE"
    completeness: float  # 0.0 to 1.0
    components: List[str]  # Framework sub-components
```

### EnrichedChunk
```python
@dataclass
class EnrichedChunk:
    chunk_id: str
    text: str
    metadata: ChunkMetadata
    embedding: Optional[List[float]] = None
    
@dataclass
class ChunkMetadata:
    book: str
    chapter: str
    section: Optional[str]
    framework: Optional[str]
    priority: str
    content_type: str
    page_range: Tuple[int, int]
    char_count: int
    overlap_with: List[str]
    concepts: List[str]
    context_before: str
    context_after: str
    quality_score: float
```

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Processing Speed | <3 min total | Both books processed |
| Framework Integrity | 100% | No split frameworks |
| Context Preservation | >95% | Overlap quality score |
| Chunk Coherence | >90% | Readability score |
| Metadata Completeness | 100% | All fields populated |

## Error Handling

```python
# At each phase, implement circuit breakers
try:
    structured_doc = extract_with_structure(pdf_path)
except PDFExtractionError:
    # Fallback to basic extraction
    structured_doc = basic_extract(pdf_path)
    
try:
    frameworks = detect_frameworks(structured_doc)
except FrameworkDetectionError:
    # Proceed with standard chunking
    frameworks = {}
    
# Continue with graceful degradation at each step
```

## Monitoring Points

1. **Extraction Phase**: Text quality, structure detection accuracy
2. **Framework Detection**: Pattern match confidence, coverage
3. **Chunking Phase**: Chunk size distribution, overlap quality
4. **Enrichment Phase**: Metadata completeness, context quality
5. **Validation Phase**: Quality scores, error rates

This ensures we maintain visibility into the entire pipeline and can optimize each phase independently.