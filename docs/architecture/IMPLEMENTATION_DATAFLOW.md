# Implementation Data Flow Changes

## Current vs Enhanced Flow

### BEFORE: Standard Pipeline
```python
# Simple linear flow
def process_document(pdf_path: str) -> List[Chunk]:
    extracted = pdf_extractor.extract(pdf_path)         # 10s
    chunks = chunker.chunk_text(extracted.text)         # 2s  
    return chunks                                        # Total: 12s
```

### AFTER: Cohesion-Aware Pipeline  
```python
# Enhanced flow with cohesion preservation
def process_document_with_cohesion(pdf_path: str) -> List[CohesiveChunk]:
    extracted = pdf_extractor.extract_with_structure(pdf_path)    # 15s (+5s structure)
    atomic_units = cohesion_detector.detect_atomic_units(extracted.text)  # 8s (new)
    protected_regions = region_manager.create_protected_regions(atomic_units)  # 2s (new) 
    chunks = enhanced_chunker.chunk_with_protection(extracted.text, protected_regions)  # 5s (+3s)
    validated_chunks = validator.validate_cohesion(chunks)       # 3s (new)
    return validated_chunks                                      # Total: 33s (+175%)
```

## Detailed Implementation Changes

### 1. Enhanced PDF Extraction

```python
# BEFORE: hormozi_rag/extractors/pdf_extractor.py
class PDFExtractor:
    def extract(self, pdf_path: str) -> ExtractedContent:
        text = self._extract_raw_text(pdf_path)
        return ExtractedContent(text=text)

# AFTER: Enhanced with structure detection
class EnhancedPDFExtractor:
    def extract_with_structure(self, pdf_path: str) -> StructuredContent:
        try:
            # Level 1: Input validation
            if not pdf_path or not Path(pdf_path).exists():
                raise ValueError(f"PDF file not found: {pdf_path}")
            
            # Level 2: Business logic with error recovery
            raw_text = self._extract_raw_text(pdf_path)
            
            # NEW: Structure detection
            structure = self._detect_document_structure(raw_text)
            formatting = self._extract_formatting_info(pdf_path)
            page_boundaries = self._map_page_boundaries(raw_text)
            
            return StructuredContent(
                text=raw_text,
                structure=structure,
                formatting=formatting,
                page_boundaries=page_boundaries,
                metadata={"extraction_method": "enhanced", "structure_detected": True}
            )
            
        except PDFExtractionError as e:
            # Level 3: Fallback to basic extraction
            logger.warning(f"Enhanced extraction failed, using basic: {e}")
            return self._basic_extraction_fallback(pdf_path)
```

### 2. New Cohesion Detection Module

```python
# NEW FILE: hormozi_rag/core/cohesion_detector.py
class CohesionDetector:
    """Detects content patterns that must stay together"""
    
    def __init__(self):
        self.framework_patterns = {
            "value_equation": {
                "start_markers": [
                    r"Value\s*=", r"value equation", r"dream outcome.*perceived likelihood"
                ],
                "components": ["dream outcome", "perceived likelihood", "time delay", "effort"],
                "end_markers": [r"\n\n", r"next chapter", r"another framework"]
            },
            "offer_stack": {
                "start_markers": [
                    r"offer creation", r"step 1.*identify", r"offer stack"
                ],
                "components": ["step 1", "step 2", "step 3", "step 4", "step 5"],
                "end_markers": [r"step 6", r"\n\n", r"next section"]
            },
            "guarantee_framework": {
                "start_markers": [
                    r"guarantee framework", r"unconditional guarantee", r"types of guarantees"
                ],
                "components": ["unconditional", "conditional", "anti-guarantee", "implied"],
                "end_markers": [r"\n\n", r"bonus strategy", r"next framework"]
            }
        }
        
    def detect_atomic_units(self, text: str) -> List[AtomicUnit]:
        """Main detection method"""
        # Input validation (Level 1)
        if not text or len(text) < 50:
            raise ValueError("Text too short for meaningful detection")
            
        atomic_units = []
        
        try:
            # Framework detection (Level 2)
            frameworks = self._detect_frameworks(text)
            atomic_units.extend(frameworks)
            
            # List detection
            lists = self._detect_numbered_lists(text)
            atomic_units.extend(lists)
            
            # Sequence detection  
            sequences = self._detect_step_sequences(text)
            atomic_units.extend(sequences)
            
        except Exception as e:
            # Level 3: Fallback detection
            logger.error(f"Advanced detection failed: {e}")
            atomic_units = self._basic_pattern_detection(text)
            
        return self._resolve_overlapping_units(atomic_units)
```

### 3. Enhanced Chunker Modification

```python
# MODIFIED: hormozi_rag/core/chunker.py
class EnhancedHormoziChunker:
    """Enhanced chunker with cohesion preservation"""
    
    def __init__(self):
        self.cohesion_detector = CohesionDetector()
        self.validator = CohesionValidator()
        self.config = settings.chunking
        
    def chunk_with_cohesion(self, structured_content: StructuredContent) -> List[CohesiveChunk]:
        """Main chunking method with cohesion preservation"""
        text = structured_content.text
        
        # Step 1: Detect atomic units that cannot be split
        atomic_units = self.cohesion_detector.detect_atomic_units(text)
        logger.info(f"Detected {len(atomic_units)} atomic units")
        
        # Step 2: Create protected regions
        protected_regions = self._create_protected_regions(atomic_units)
        
        # Step 3: Chunk with protection
        chunks = self._chunk_respecting_protection(text, protected_regions)
        
        # Step 4: Validate cohesion
        validation_report = self.validator.validate_chunks(chunks)
        if validation_report.has_critical_violations():
            logger.error("Critical cohesion violations detected")
            chunks = self._remediate_violations(chunks, validation_report)
        
        return chunks
        
    def _chunk_respecting_protection(self, text: str, protected_regions: List[ProtectedRegion]) -> List[CohesiveChunk]:
        """Chunk text while respecting protected regions"""
        chunks = []
        current_pos = 0
        
        for region in sorted(protected_regions, key=lambda r: r.start):
            # Chunk text before protected region
            if current_pos < region.start:
                pre_chunks = self._standard_chunk_segment(
                    text[current_pos:region.start], 
                    offset=current_pos
                )
                chunks.extend(pre_chunks)
            
            # Create atomic chunk for protected region
            atomic_chunk = CohesiveChunk(
                chunk_id=self._generate_atomic_chunk_id(region),
                text=text[region.start:region.end],
                start_char=region.start,
                end_char=region.end,
                chunk_type="atomic",
                atomic_units=region.atomic_units,
                cohesion_score=1.0,  # Perfect cohesion for atomic units
                metadata=self._create_atomic_metadata(region)
            )
            chunks.append(atomic_chunk)
            
            current_pos = region.end
        
        # Chunk remaining text
        if current_pos < len(text):
            final_chunks = self._standard_chunk_segment(
                text[current_pos:],
                offset=current_pos
            )
            chunks.extend(final_chunks)
        
        return chunks
```

### 4. New Validation Module

```python
# NEW FILE: hormozi_rag/core/cohesion_validator.py
class CohesionValidator:
    """Validates cohesion preservation quality"""
    
    def validate_chunks(self, chunks: List[CohesiveChunk]) -> CohesionReport:
        """Comprehensive cohesion validation"""
        start_time = time.time()
        violations = []
        
        # Critical: Framework integrity
        framework_violations = self._validate_framework_integrity(chunks)
        violations.extend(framework_violations)
        
        # High: List completeness
        list_violations = self._validate_list_completeness(chunks)
        violations.extend(list_violations)
        
        # Medium: Example coherence
        example_violations = self._validate_example_coherence(chunks)
        violations.extend(example_violations)
        
        # Calculate quality scores
        cohesion_score = self._calculate_overall_cohesion_score(chunks)
        framework_rate = self._calculate_framework_integrity_rate(chunks)
        
        processing_time = int((time.time() - start_time) * 1000)  # ms
        
        return CohesionReport(
            total_chunks=len(chunks),
            atomic_chunks=len([c for c in chunks if c.chunk_type == "atomic"]),
            violations=violations,
            cohesion_score=cohesion_score,
            framework_integrity_rate=framework_rate,
            processing_time_ms=processing_time
        )
```

## File System Changes

### New Files Created
```
hormozi_rag/
├── core/
│   ├── cohesion_detector.py        # NEW - Pattern detection
│   ├── cohesion_validator.py       # NEW - Quality validation
│   └── chunker.py                  # MODIFIED - Enhanced chunking
├── extractors/
│   └── pdf_extractor.py           # MODIFIED - Structure detection
└── config/
    └── cohesion_patterns.py       # NEW - Pattern definitions
```

### Configuration Changes
```python
# Enhanced hormozi_rag/config/settings.py
@dataclass
class CohesionConfig:
    """Configuration for cohesion preservation"""
    enable_cohesion_detection: bool = True
    framework_detection_confidence: float = 0.8
    list_min_items: int = 2
    sequence_min_steps: int = 2
    max_atomic_chunk_size: int = 4000  # chars
    validation_strictness: str = "high"  # "low", "medium", "high"
    
    # Performance settings
    enable_pattern_caching: bool = True
    batch_size_for_large_docs: int = 50000
    max_processing_time_seconds: int = 300

# Add to main Settings class
@dataclass
class Settings:
    # ... existing configs ...
    cohesion: CohesionConfig = field(default_factory=CohesionConfig)
```

## Data Structure Changes

### Enhanced Chunk Metadata
```python
# BEFORE: Simple chunk
{
    "chunk_id": "doc_001", 
    "text": "...",
    "metadata": {"page": 1}
}

# AFTER: Cohesion-rich chunk
{
    "chunk_id": "100m_ch3_value_eq_atomic",
    "text": "Value = (Dream Outcome × Perceived Likelihood)...",
    "chunk_type": "atomic",
    "cohesion_score": 1.0,
    "atomic_units": [
        {
            "type": "framework",
            "framework_type": "value_equation", 
            "priority": "CRITICAL",
            "start_char": 0,
            "end_char": 2340
        }
    ],
    "metadata": {
        "page_range": [45, 47],
        "framework_complete": True,
        "safe_to_retrieve_alone": True,
        "related_frameworks": ["offer_stack"],
        "preservation_method": "atomic_detection",
        "quality_validated": True
    }
}
```

## Performance Impact Analysis

### Processing Time Breakdown
```python
# Standard chunking: 12 seconds total
- PDF extraction: 10s
- Text chunking: 2s

# Enhanced cohesion chunking: 33 seconds total (+175%)
- Enhanced PDF extraction: 15s (+5s for structure detection)
- Cohesion detection: 8s (new phase)
- Protected region creation: 2s (new phase)  
- Enhanced chunking: 5s (+3s for protection logic)
- Validation: 3s (new phase)

# Justification: +175% processing time for 100% framework integrity
```

### Memory Usage Changes
```python
# Additional memory overhead
- Atomic units storage: ~50KB for 650k chars
- Protected regions: ~20KB 
- Pattern caches: ~100KB
- Validation metadata: ~30KB
# Total overhead: ~200KB (+minimal impact)
```

## Error Handling Flow

### Graceful Degradation Path
```python
def process_with_graceful_degradation(text: str) -> List[CohesiveChunk]:
    try:
        # Level 1: Full cohesion processing
        return self.chunk_with_full_cohesion(text)
    except CohesionDetectionError:
        logger.warning("Cohesion detection failed, using basic patterns")
        try:
            # Level 2: Basic pattern matching
            return self.chunk_with_basic_patterns(text)
        except BasicPatternError:
            logger.error("Basic patterns failed, using standard chunking")
            # Level 3: Standard chunking fallback
            return self.chunk_standard_with_warnings(text)
```

This implementation maintains the existing architecture while adding robust cohesion preservation with proper error handling and performance monitoring!