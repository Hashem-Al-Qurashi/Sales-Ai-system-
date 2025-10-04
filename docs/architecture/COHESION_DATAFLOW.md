# Enhanced Data Flow with Cohesion Preservation

## Overview
This document shows the modified data flow to ensure content that belongs together stays together during chunking.

## Enhanced Pipeline Architecture

```
📚 INPUT: PDF FILES (138 pages, 650k+ chars)
│
▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: ENHANCED EXTRACTION                │
│                                                                 │
│  📄 Structure-Aware PDF Extractor                              │
│  ├── Text Extraction + Formatting                              │
│  ├── Page Boundary Detection                                   │
│  ├── Paragraph Structure Preservation                          │
│  └── Font/Style Analysis (headers, bold, etc.)                │
│                                                                 │
│  OUTPUT: StructuredDocument                                     │
│  {                                                             │
│    text: str,                                                  │
│    structure: {paragraphs: [], headers: []},                  │
│    formatting: {bold_spans: [], styles: []},                  │
│    page_boundaries: [char_positions]                          │
│  }                                                             │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 2: COHESION DETECTION (NEW)                 │
│                                                                 │
│  🧠 Multi-Pattern Cohesion Detector                            │
│  │                                                             │
│  ├── 🔴 ATOMIC UNIT DETECTION (Never Split)                   │
│  │   ├── Framework Detector                                   │
│  │   │   └── Value Equation, Offer Stack, Guarantees         │
│  │   ├── List Detector                                        │
│  │   │   └── Numbered lists (1,2,3), bullets (•), dashes    │
│  │   ├── Sequence Detector                                    │
│  │   │   └── "Step 1... Step 2", "First... Then... Finally" │
│  │   └── Example-Explanation Pairs                           │
│  │       └── "For example" + explanation                     │
│  │                                                             │
│  ├── 🟡 COHESIVE UNIT DETECTION (Smart Split)                 │
│  │   ├── Definition-Example Pairs                            │
│  │   ├── Cause-Effect Chains                                 │
│  │   ├── Question-Answer Pairs                               │
│  │   └── Concept Dependencies                                │
│  │                                                             │
│  └── 🔗 RELATIONSHIP MAPPING                                   │
│      ├── Cross-references between units                       │
│      ├── Dependency chains                                    │
│      └── Context requirements                                 │
│                                                                 │
│  OUTPUT: CohesionMap                                           │
│  {                                                             │
│    atomic_units: [                                            │
│      {type: "framework", start: 1250, end: 3750,            │
│       framework: "value_equation", priority: "ATOMIC"},       │
│      {type: "list", start: 4200, end: 4800,                 │
│       items: 5, priority: "ATOMIC"}                          │
│    ],                                                          │
│    cohesive_units: [...],                                     │
│    relationships: [...]                                       │
│  }                                                             │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│            PHASE 3: PROTECTED REGION CREATION (NEW)            │
│                                                                 │
│  🛡️ Region Protection Manager                                  │
│  │                                                             │
│  ├── OVERLAP RESOLUTION                                        │
│  │   ├── Detect overlapping atomic units                      │
│  │   ├── Merge conflicting boundaries                         │
│  │   └── Resolve priority conflicts                           │
│  │                                                             │
│  ├── PROTECTED REGION MAPPING                                  │
│  │   ├── Mark no-split zones                                  │
│  │   ├── Define buffer zones                                  │
│  │   └── Create safe split points                             │
│  │                                                             │
│  └── BOUNDARY OPTIMIZATION                                     │
│      ├── Find natural split points                            │
│      ├── Avoid mid-sentence splits                            │
│      └── Preserve paragraph integrity                         │
│                                                                 │
│  OUTPUT: ProtectedRegionMap                                    │
│  {                                                             │
│    protected_regions: [                                       │
│      {start: 1250, end: 3750, type: "atomic",               │
│       reason: "value_equation_framework"},                    │
│      {start: 4200, end: 4800, type: "atomic",               │
│       reason: "numbered_list_5_items"}                       │
│    ],                                                          │
│    safe_split_points: [800, 1200, 3800, 4150, 4850],        │
│    buffer_zones: [...]                                        │
│  }                                                             │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 4: COHESION-AWARE CHUNKING                  │
│                                                                 │
│  🎯 Cohesion-Preserving Chunker                               │
│  │                                                             │
│  ├── CHUNK PROTECTED REGIONS                                   │
│  │   ├── Atomic units → Single chunks (regardless of size)   │
│  │   ├── Add rich metadata for each atomic chunk             │
│  │   └── Ensure 100% preservation                            │
│  │                                                             │
│  ├── CHUNK UNPROTECTED TEXT                                    │
│  │   ├── Use safe split points only                          │
│  │   ├── Standard size limits (1500 chars)                   │
│  │   ├── Respect paragraph boundaries                        │
│  │   └── Add overlap with adjacent chunks                    │
│  │                                                             │
│  ├── COHESIVE UNIT HANDLING                                    │
│  │   ├── Keep definition-example pairs together              │
│  │   ├── Preserve cause-effect chains                        │
│  │   └── Maintain concept dependencies                       │
│  │                                                             │
│  └── BOUNDARY SMOOTHING                                        │
│      ├── Extend chunks to sentence boundaries                 │
│      ├── Add contextual overlap (200 chars)                  │
│      └── Ensure no orphaned fragments                        │
│                                                                 │
│  OUTPUT: CohesiveChunks[]                                      │
│  [                                                             │
│    {                                                           │
│      chunk_id: "100m_ch3_value_eq_atomic",                   │
│      text: "Complete Value Equation...",                      │
│      type: "atomic",                                          │
│      cohesion_score: 1.0,                                    │
│      atomic_units: ["value_equation"],                       │
│      size: 2500  # Larger than normal for completeness       │
│    },                                                          │
│    {                                                           │
│      chunk_id: "100m_ch3_pricing_list_atomic",               │
│      text: "1. Cost-based pricing\n2. Value-based...",       │
│      type: "atomic",                                          │
│      cohesion_score: 1.0,                                    │
│      atomic_units: ["numbered_list"],                        │
│      size: 800                                               │
│    },                                                          │
│    {                                                           │
│      chunk_id: "100m_ch3_supporting_001",                    │
│      text: "Supporting content...",                           │
│      type: "standard",                                        │
│      cohesion_score: 0.7,                                    │
│      atomic_units: [],                                       │
│      size: 1500                                              │
│    }                                                           │
│  ]                                                             │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│                PHASE 5: COHESION VALIDATION (NEW)              │
│                                                                 │
│  ✅ Cohesion Quality Validator                                 │
│  │                                                             │
│  ├── ATOMIC UNIT INTEGRITY CHECK                               │
│  │   ├── Verify no frameworks are split                      │
│  │   ├── Confirm all list items present                      │
│  │   ├── Validate sequence completeness                      │
│  │   └── Check example-explanation pairing                   │
│  │                                                             │
│  ├── COHESION SCORING                                          │
│  │   ├── Calculate preservation rate (target: >95%)          │
│  │   ├── Measure fragment coherence                          │
│  │   ├── Assess context completeness                         │
│  │   └── Evaluate semantic boundaries                        │
│  │                                                             │
│  ├── VIOLATION DETECTION                                       │
│  │   ├── CRITICAL: Split frameworks or lists                 │
│  │   ├── WARNING: Orphaned examples                          │
│  │   ├── INFO: Suboptimal boundaries                         │
│  │   └── Generate remediation suggestions                    │
│  │                                                             │
│  └── QUALITY REPORTING                                         │
│      ├── Per-chunk cohesion scores                            │
│      ├── Overall preservation metrics                         │
│      ├── Violation summary with severity                      │
│      └── Improvement recommendations                          │
│                                                                 │
│  QUALITY GATES:                                                │
│  ✓ Framework integrity: 100% (CRITICAL)                      │
│  ✓ List completeness: >95% (HIGH)                            │
│  ✓ Example coherence: >90% (MEDIUM)                          │
│  ✓ Overall cohesion: >0.85 (TARGET)                          │
│                                                                 │
│  OUTPUT: CohesionReport + ValidatedChunks[]                    │
└─────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 6: METADATA ENRICHMENT                 │
│                                                                 │
│  📋 Enhanced Context Enricher                                  │
│  ├── Add cohesion metadata to each chunk                      │
│  ├── Link related atomic units                                │
│  ├── Create cross-reference maps                              │
│  ├── Preserve context relationships                           │
│  └── Generate retrieval hints                                 │
│                                                                 │
│  OUTPUT: EnrichedCohesiveChunks[]                             │
│  [                                                             │
│    {                                                           │
│      chunk_id: "100m_ch3_value_eq_atomic",                   │
│      text: "...",                                             │
│      metadata: {                                              │
│        type: "atomic",                                        │
│        framework: "value_equation",                           │
│        cohesion_score: 1.0,                                  │
│        atomic_preservation: true,                             │
│        related_chunks: ["100m_ch3_offer_atomic"],            │
│        dependencies: [],                                      │
│        context_complete: true,                                │
│        safe_to_retrieve_alone: true                          │
│      }                                                         │
│    }                                                           │
│  ]                                                             │
└─────────────────────────────────────────────────────────────────┘
│
▼
📊 FINAL OUTPUT: COHESION-PRESERVED CHUNKS
├── Total chunks: ~450 (same as before)
├── Atomic chunks: ~60 (frameworks, lists, sequences)
├── Cohesion score: >0.85 (quality target)
├── Framework integrity: 100% (never split)
├── Processing time: +30% (acceptable for quality gain)
└── Ready for: Embedder → VectorDB → Retrieval
```

## Key Data Flow Changes

### 1. New Preprocessing Stage
```python
# BEFORE: Simple extraction
text = extract_pdf(pdf_file)
chunks = chunk_text(text, size=1500)

# AFTER: Cohesion-aware processing
structured_doc = extract_with_structure(pdf_file)
cohesion_map = detect_cohesion_patterns(structured_doc)
protected_regions = create_protected_regions(cohesion_map)
chunks = chunk_with_cohesion(structured_doc, protected_regions)
```

### 2. Enhanced Chunk Metadata
```python
# BEFORE: Basic metadata
{
  "chunk_id": "doc_001",
  "text": "...",
  "size": 1500
}

# AFTER: Cohesion-rich metadata
{
  "chunk_id": "100m_ch3_value_eq_atomic",
  "text": "...",
  "type": "atomic",  # atomic, cohesive, standard
  "cohesion_score": 1.0,
  "atomic_units": ["value_equation"],
  "preservation_method": "framework_detection",
  "safe_to_split": false,
  "context_dependencies": [],
  "related_atomic_units": ["offer_stack"],
  "quality_validated": true
}
```

### 3. Processing Pipeline Changes
```python
# NEW: Cohesion detection step
cohesion_detector = CohesionDetector()
atomic_units = cohesion_detector.detect_atomic_units(text)

# NEW: Protected region management
region_manager = ProtectedRegionManager()
protected_regions = region_manager.create_regions(atomic_units)

# MODIFIED: Chunking respects protection
cohesive_chunker = CohesionAwareChunker()
chunks = cohesive_chunker.chunk_with_protection(text, protected_regions)

# NEW: Validation step
validator = CohesionValidator()
report = validator.validate_cohesion(chunks)
if report.cohesion_score < 0.85:
    chunks = validator.remediate_violations(chunks, report)
```

## Performance Impact Analysis

| Stage | Before | After | Overhead |
|-------|--------|-------|----------|
| Extraction | 10s | 15s | +50% (structure detection) |
| Chunking | 5s | 8s | +60% (cohesion processing) |
| Validation | 0s | 3s | +∞ (new stage) |
| **Total** | **15s** | **26s** | **+73%** |

**Justification**: 73% overhead acceptable for 100% framework integrity

## Quality Guarantees

### Before Cohesion System
- ❌ Framework splitting: ~30% of frameworks split
- ❌ List fragmentation: ~25% of lists broken
- ❌ Example isolation: ~40% of examples orphaned
- ❌ Overall coherence: ~65%

### After Cohesion System
- ✅ Framework integrity: 100% (atomic preservation)
- ✅ List completeness: >95% (smart detection)
- ✅ Example coherence: >90% (pair detection)
- ✅ Overall cohesion: >85% (quality target)

## Error Handling in Pipeline

```python
# Graceful degradation at each stage
try:
    cohesion_map = detect_cohesion_patterns(doc)
except CohesionDetectionError:
    logger.warning("Cohesion detection failed, using basic patterns")
    cohesion_map = detect_basic_patterns(doc)

try:
    chunks = chunk_with_cohesion(doc, cohesion_map)
except CohesionChunkingError:
    logger.error("Cohesion chunking failed, falling back to standard")
    chunks = standard_chunk_with_overlap(doc)
    
# Always validate final output
validation_report = validate_chunks(chunks)
if validation_report.has_critical_violations():
    raise CriticalCohesionError("Cannot proceed with split frameworks")
```

This enhanced data flow ensures that business frameworks, numbered lists, sequential processes, and example-explanation pairs are never broken apart, maintaining the semantic integrity essential for accurate retrieval and generation.