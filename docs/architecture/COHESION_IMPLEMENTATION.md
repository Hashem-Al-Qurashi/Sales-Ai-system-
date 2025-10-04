# Cohesion Preservation System Implementation

## Overview
This document specifies the exact implementation of the cohesion preservation system within the existing Hormozi RAG architecture.

## Architecture Integration

### Existing Pipeline (ARCHITECTURE.md)
```
PDF Files → Extractor → Chunker → Embedder → VectorDB
```

### Enhanced Pipeline (Implementation)
```
PDF Files → Extractor → [Cohesion Detector] → Enhanced Chunker → [Validator] → Embedder → VectorDB
```

### Module Placement
- **Location**: Enhance existing `hormozi_rag/core/chunker.py`
- **New Modules**: 
  - `hormozi_rag/core/cohesion_detector.py`
  - `hormozi_rag/core/cohesion_validator.py`
- **Contract Preservation**: Output remains `[{id, text, metadata, embedding: None}]`

## Current State Analysis

### Prerequisites ✅
- Configuration: 95% complete (API keys set)
- Chunking config: Framework-aware settings already exist
- Error logging: Basic logging in place

### Blockers to Address 🔧
- PDF extraction needs error handling
- No chunks created yet (this will be first implementation)
- Vector database not initialized (not needed for chunking)

## Implementation Architecture

### 1. Core Components

```python
# New Module: hormozi_rag/core/cohesion_detector.py
class CohesionDetector:
    """Detects content patterns that must stay together"""
    
    def detect_atomic_units(self, text: str) -> List[AtomicUnit]:
        """Find frameworks, lists, sequences that cannot be split"""
        
    def detect_cohesive_units(self, text: str) -> List[CohesiveUnit]:
        """Find related content that should stay together"""

# Enhanced Module: hormozi_rag/core/chunker.py  
class EnhancedHormoziChunker:
    """Cohesion-aware chunking with framework preservation"""
    
    def __init__(self):
        self.cohesion_detector = CohesionDetector()
        self.validator = CohesionValidator()
    
    def chunk_with_cohesion(self, extracted_content) -> List[CohesiveChunk]:
        """Main chunking method that preserves cohesion"""

# New Module: hormozi_rag/core/cohesion_validator.py
class CohesionValidator:
    """Validates cohesion preservation quality"""
    
    def validate_chunks(self, chunks: List[CohesiveChunk]) -> CohesionReport:
        """Ensure no critical content was split"""
```

### 2. Data Structures (Development Rules Compliant)

```python
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional

class AtomicType(Enum):
    """Types of atomic content that cannot be split"""
    FRAMEWORK = "framework"
    NUMBERED_LIST = "numbered_list"
    SEQUENCE = "sequence"
    EXAMPLE_PAIR = "example_pair"

@dataclass
class AtomicUnit:
    """Content that must never be split - Single Responsibility"""
    start_char: int
    end_char: int
    type: AtomicType
    framework_type: Optional[str]  # "value_equation", "offer_stack", etc.
    priority: str  # "CRITICAL", "HIGH", "MEDIUM"
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        # Input validation (Level 1 Error Handling)
        if self.start_char >= self.end_char:
            raise ValueError("Invalid character positions")
        if self.type not in AtomicType:
            raise TypeError("Invalid atomic type")

@dataclass
class CohesiveChunk:
    """Enhanced chunk with cohesion metadata"""
    chunk_id: str
    text: str
    start_char: int
    end_char: int
    chunk_type: str  # "atomic", "cohesive", "standard"
    atomic_units: List[AtomicUnit]
    cohesion_score: float  # 0.0 to 1.0
    metadata: Dict[str, Any]
    
    def is_atomic(self) -> bool:
        """Check if chunk contains atomic content"""
        return len(self.atomic_units) > 0 and self.chunk_type == "atomic"

@dataclass 
class CohesionReport:
    """Validation report for cohesion quality"""
    total_chunks: int
    atomic_chunks: int
    violations: List[str]
    cohesion_score: float
    framework_integrity_rate: float
    processing_time_ms: int
```

### 3. Implementation Strategy (Following Development Rules)

#### Phase 1: Cohesion Detection Engine

```python
# hormozi_rag/core/cohesion_detector.py
class CohesionDetector:
    """Single Responsibility: Detect content cohesion patterns"""
    
    def __init__(self):
        self.framework_patterns = self._load_framework_patterns()
        self.list_patterns = self._compile_list_patterns()
        
    def detect_atomic_units(self, text: str) -> List[AtomicUnit]:
        """Main detection method - under 50 lines"""
        # Level 1: Input validation
        if not text or not isinstance(text, str):
            raise ValueError("Text must be non-empty string")
        
        atomic_units = []
        
        try:
            # Level 2: Business logic with error recovery
            frameworks = self._detect_frameworks(text)
            atomic_units.extend(frameworks)
            
            lists = self._detect_numbered_lists(text)  
            atomic_units.extend(lists)
            
            sequences = self._detect_sequences(text)
            atomic_units.extend(sequences)
            
        except DetectionError as e:
            # Graceful degradation
            logger.warning(f"Cohesion detection partially failed: {e}")
            atomic_units.extend(self._basic_pattern_fallback(text))
        
        return self._resolve_overlaps(atomic_units)
    
    def _detect_frameworks(self, text: str) -> List[AtomicUnit]:
        """Detect Hormozi frameworks - under 50 lines"""
        frameworks = []
        
        for framework_type, patterns in self.framework_patterns.items():
            matches = self._find_pattern_boundaries(text, patterns)
            
            for match in matches:
                if self._validate_framework_completeness(text, match, framework_type):
                    frameworks.append(AtomicUnit(
                        start_char=match.start,
                        end_char=match.end,
                        type=AtomicType.FRAMEWORK,
                        framework_type=framework_type,
                        priority="CRITICAL",
                        metadata={"components": match.components}
                    ))
        
        return frameworks
    
    def _detect_numbered_lists(self, text: str) -> List[AtomicUnit]:
        """Detect numbered/bulleted lists - under 50 lines"""
        lists = []
        
        # Pattern for numbered lists: 1. 2. 3. or • • •
        pattern = r'(?:^\s*(?:\d+\.|[•\-\*])\s+.+(?:\n|$))+'
        matches = re.finditer(pattern, text, re.MULTILINE)
        
        for match in matches:
            items = self._extract_list_items(match.group())
            
            # Only preserve lists with 2+ items
            if len(items) >= 2:
                lists.append(AtomicUnit(
                    start_char=match.start(),
                    end_char=match.end(),
                    type=AtomicType.NUMBERED_LIST,
                    framework_type=None,
                    priority="HIGH",
                    metadata={"item_count": len(items), "items": items}
                ))
        
        return lists
```

#### Phase 2: Enhanced Chunker Integration

```python
# Enhanced hormozi_rag/core/chunker.py
class EnhancedHormoziChunker:
    """Enhanced chunker with cohesion preservation"""
    
    def __init__(self):
        self.cohesion_detector = CohesionDetector()
        self.validator = CohesionValidator()
        self.config = settings.chunking
        
    def chunk_with_cohesion(self, extracted_content) -> List[CohesiveChunk]:
        """Main chunking method - follows single responsibility"""
        # Level 1: Input validation
        if not extracted_content or not extracted_content.text:
            raise ValueError("Extracted content must contain text")
        
        text = extracted_content.text
        
        try:
            # Level 2: Business logic with error recovery
            atomic_units = self.cohesion_detector.detect_atomic_units(text)
            protected_regions = self._create_protected_regions(atomic_units)
            chunks = self._chunk_with_protection(text, protected_regions)
            
            # Level 3: Validation
            report = self.validator.validate_chunks(chunks)
            if report.has_critical_violations():
                raise CriticalCohesionError("Framework integrity violated")
            
        except CohesionDetectionError as e:
            # Fallback to standard chunking with warning
            logger.warning(f"Cohesion chunking failed, using standard: {e}")
            chunks = self._standard_chunk_fallback(text)
        
        return chunks
    
    def _create_protected_regions(self, atomic_units: List[AtomicUnit]) -> List[ProtectedRegion]:
        """Create no-split zones from atomic units - under 50 lines"""
        if not atomic_units:
            return []
        
        # Sort by priority and position
        sorted_units = sorted(atomic_units, 
                            key=lambda u: (self._priority_score(u.priority), u.start_char))
        
        protected_regions = []
        
        for unit in sorted_units:
            # Ensure atomic units are never split
            region = ProtectedRegion(
                start=unit.start_char,
                end=unit.end_char,
                type=unit.type,
                priority=unit.priority,
                reason=f"{unit.type.value}_{unit.framework_type or 'detected'}"
            )
            protected_regions.append(region)
        
        return self._merge_overlapping_regions(protected_regions)
```

#### Phase 3: Validation System

```python
# hormozi_rag/core/cohesion_validator.py
class CohesionValidator:
    """Single Responsibility: Validate cohesion preservation"""
    
    def validate_chunks(self, chunks: List[CohesiveChunk]) -> CohesionReport:
        """Validate cohesion quality - under 50 lines"""
        violations = []
        
        # Check framework integrity (most critical)
        framework_violations = self._check_framework_integrity(chunks)
        violations.extend(framework_violations)
        
        # Check list completeness
        list_violations = self._check_list_completeness(chunks)
        violations.extend(list_violations)
        
        # Calculate scores
        cohesion_score = self._calculate_cohesion_score(chunks)
        framework_rate = self._calculate_framework_integrity_rate(chunks)
        
        return CohesionReport(
            total_chunks=len(chunks),
            atomic_chunks=len([c for c in chunks if c.is_atomic()]),
            violations=violations,
            cohesion_score=cohesion_score,
            framework_integrity_rate=framework_rate,
            processing_time_ms=0  # Will be measured
        )
    
    def _check_framework_integrity(self, chunks: List[CohesiveChunk]) -> List[str]:
        """Ensure no frameworks are split - under 50 lines"""
        violations = []
        
        # Group chunks by framework type
        framework_chunks = {}
        for chunk in chunks:
            for atomic_unit in chunk.atomic_units:
                if atomic_unit.type == AtomicType.FRAMEWORK:
                    fw_type = atomic_unit.framework_type
                    if fw_type not in framework_chunks:
                        framework_chunks[fw_type] = []
                    framework_chunks[fw_type].append(chunk)
        
        # Validate each framework is complete
        for fw_type, fw_chunks in framework_chunks.items():
            if len(fw_chunks) > 1:
                violations.append(
                    f"CRITICAL: {fw_type} framework split across {len(fw_chunks)} chunks"
                )
            else:
                # Check completeness within single chunk
                if not self._validate_framework_components(fw_chunks[0], fw_type):
                    violations.append(
                        f"WARNING: {fw_type} framework incomplete in chunk {fw_chunks[0].chunk_id}"
                    )
        
        return violations
```

## Error Handling Strategy (Development Rules Compliant)

### 3-Level Error Hierarchy

```python
# Level 1: Input Validation (Fail Fast)
def detect_atomic_units(self, text: str) -> List[AtomicUnit]:
    if not text or not isinstance(text, str):
        raise ValueError("Text must be non-empty string")
    if len(text) < 10:
        raise ValueError("Text too short for meaningful chunking")

# Level 2: Business Logic Errors (Recover Gracefully)  
try:
    atomic_units = self.cohesion_detector.detect_atomic_units(text)
except CohesionDetectionError as e:
    logger.warning(f"Cohesion detection failed: {e}")
    atomic_units = self._basic_pattern_fallback(text)
    metrics.record_fallback("cohesion_detection")

# Level 3: System Errors (Circuit Breaker)
@circuit_breaker(failure_threshold=5, recovery_timeout=60)
def process_large_document(self, text: str):
    # Only for very large documents that might overwhelm system
    pass
```

## Performance Considerations

### Processing Time Targets
- **Total Overhead**: <30% vs standard chunking
- **Cohesion Detection**: <10s for 650k chars
- **Validation**: <3s for 450 chunks
- **Memory Usage**: <500MB peak

### Optimization Strategies
```python
# Efficient pattern matching
compiled_patterns = {
    fw_type: re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    for fw_type, pattern in FRAMEWORK_PATTERNS.items()
}

# Batch processing for large texts
def chunk_large_text(self, text: str) -> List[CohesiveChunk]:
    if len(text) > 100000:  # 100k chars
        return self._batch_process_chunks(text, batch_size=50000)
    return self._standard_process_chunks(text)
```

## Quality Targets

| Metric | Target | Validation |
|--------|--------|------------|
| Framework Integrity | 100% | No split frameworks in validation |
| List Completeness | >95% | All numbered lists preserved |
| Processing Overhead | <30% | Measured vs standard chunking |
| Function Complexity | <50 lines | All functions under limit |
| Error Recovery | >90% | Graceful degradation rate |

## Testing Strategy

```python
# Unit tests for each component
def test_framework_detection():
    text = "Value = (Dream Outcome × Perceived Likelihood) / (Time Delay + Effort)"
    detector = CohesionDetector()
    units = detector.detect_atomic_units(text)
    assert len(units) == 1
    assert units[0].type == AtomicType.FRAMEWORK
    assert units[0].framework_type == "value_equation"

# Integration tests for complete pipeline  
def test_cohesion_preservation_end_to_end():
    # Test with actual Hormozi content
    pdf_path = "data/raw/$100m Offers.pdf"
    # ... process and validate cohesion
    
# Performance tests
def test_processing_performance():
    large_text = "..." * 100000  # 100k chars
    start_time = time.time()
    chunks = chunker.chunk_with_cohesion(large_text)
    duration = time.time() - start_time
    assert duration < 30  # 30 second limit
```

This implementation follows all development rules while delivering the cohesion preservation requirements!