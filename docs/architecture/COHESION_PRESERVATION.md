# Cohesion Preservation System Design

## Overview
This document defines how to ensure that content pieces that belong together stay together during the chunking process for Hormozi's business frameworks.

## The Cohesion Problem

### Current Risk
- **Framework Splitting**: Value Equation components scattered across chunks
- **List Fragmentation**: Numbered lists broken mid-sequence
- **Example Separation**: Examples divorced from their concepts
- **Process Interruption**: Step-by-step guides split randomly

### Real Impact Analysis
From book analysis:
- **Page 11**: 12 numbered lists detected - high fragmentation risk
- **Framework Detection**: Multiple frameworks per page require careful boundary detection
- **Sequential Content**: Step-by-step processes need complete preservation

## Cohesion Detection System

### 1. Content Cohesion Patterns

#### **🔴 CRITICAL - Never Split**
```python
ATOMIC_PATTERNS = {
    # Complete frameworks (GOLD level)
    "value_equation": {
        "start_markers": ["Value =", "value equation", "dream outcome"],
        "components": ["dream outcome", "perceived likelihood", "time delay", "effort"],
        "end_markers": ["equation complete", "next framework", "chapter"]
    },
    
    # Numbered sequences
    "numbered_lists": {
        "pattern": r"(?:1\.|2\.|3\.|4\.|5\.|\•|\-).*?(?=\n\n|\n[A-Z]|$)",
        "min_items": 2,
        "max_separation": 100  # chars between items
    },
    
    # Step-by-step processes
    "sequential_steps": {
        "pattern": r"Step \d+.*?(?=Step \d+|$)",
        "sequence_words": ["first", "second", "then", "next", "finally"],
        "preserve_complete": True
    }
}
```

#### **🟡 IMPORTANT - Smart Split**
```python
COHESIVE_PATTERNS = {
    # Example + explanation pairs
    "example_pairs": {
        "triggers": ["For example", "Example:", "For instance"],
        "max_distance": 500,  # chars from trigger to end
        "end_markers": ["\n\n", "Another example", "Next,"]
    },
    
    # Concept definitions
    "definitions": {
        "pattern": r"([A-Z][a-z\s]+) is (when|the|a).*?(?=\n\n|[A-Z][a-z]+ is)",
        "keep_with_examples": True
    },
    
    # Cause-effect relationships
    "causality": {
        "triggers": ["because", "therefore", "as a result", "this means"],
        "preserve_chain": True
    }
}
```

### 2. Cohesion Detection Pipeline

```python
class CohesionDetector:
    def detect_atomic_units(self, text: str) -> List[AtomicUnit]:
        """Detect content that must never be split"""
        atomic_units = []
        
        # 1. Framework detection
        frameworks = self.detect_frameworks(text)
        atomic_units.extend(frameworks)
        
        # 2. List detection
        lists = self.detect_numbered_lists(text)
        atomic_units.extend(lists)
        
        # 3. Sequential processes
        sequences = self.detect_sequences(text)
        atomic_units.extend(sequences)
        
        # 4. Example-explanation pairs
        examples = self.detect_example_pairs(text)
        atomic_units.extend(examples)
        
        return self.resolve_overlaps(atomic_units)
    
    def detect_frameworks(self, text: str) -> List[FrameworkUnit]:
        """Detect complete business frameworks"""
        frameworks = []
        
        for framework_type, patterns in FRAMEWORK_PATTERNS.items():
            matches = self.find_framework_boundaries(text, patterns)
            for match in matches:
                frameworks.append(FrameworkUnit(
                    type=framework_type,
                    start=match.start,
                    end=match.end,
                    priority="ATOMIC",
                    components=match.components
                ))
        
        return frameworks
    
    def detect_numbered_lists(self, text: str) -> List[ListUnit]:
        """Detect numbered/bulleted lists"""
        lists = []
        
        # Find list patterns
        list_pattern = r'(?:^\s*(?:\d+\.|[•\-\*])\s+.+(?:\n|$))+'
        matches = re.finditer(list_pattern, text, re.MULTILINE)
        
        for match in matches:
            items = self.extract_list_items(match.group())
            if len(items) >= 2:  # Must have at least 2 items
                lists.append(ListUnit(
                    start=match.start(),
                    end=match.end(),
                    items=items,
                    priority="ATOMIC"
                ))
        
        return lists
    
    def detect_sequences(self, text: str) -> List[SequenceUnit]:
        """Detect step-by-step processes"""
        sequences = []
        
        # Pattern for "Step 1... Step 2..." sequences
        step_pattern = r'(?:Step\s+\d+|First|Second|Third|Next|Then|Finally).*?(?=Step\s+\d+|First|Second|$)'
        matches = re.finditer(step_pattern, text, re.IGNORECASE | re.DOTALL)
        
        grouped_steps = self.group_sequential_steps(matches)
        for group in grouped_steps:
            if len(group) >= 2:
                sequences.append(SequenceUnit(
                    start=min(step.start for step in group),
                    end=max(step.end for step in group),
                    steps=group,
                    priority="ATOMIC"
                ))
        
        return sequences
```

### 3. Cohesion-Aware Chunking Algorithm

```python
class CohesionAwareChunker:
    def chunk_with_cohesion(self, text: str) -> List[CohesiveChunk]:
        """Chunk text while preserving cohesion"""
        
        # 1. Detect all atomic units
        atomic_units = self.detector.detect_atomic_units(text)
        
        # 2. Sort by priority and position
        atomic_units.sort(key=lambda u: (u.priority_score, u.start))
        
        # 3. Create protected regions
        protected_regions = self.create_protected_regions(atomic_units)
        
        # 4. Chunk unprotected text
        chunks = []
        current_pos = 0
        
        for region in protected_regions:
            # Chunk text before protected region
            if current_pos < region.start:
                pre_chunks = self.standard_chunk(
                    text[current_pos:region.start],
                    offset=current_pos
                )
                chunks.extend(pre_chunks)
            
            # Add protected region as single chunk
            protected_chunk = CohesiveChunk(
                text=text[region.start:region.end],
                start=region.start,
                end=region.end,
                type=region.type,
                priority="ATOMIC",
                cohesion_score=1.0,
                metadata=region.metadata
            )
            chunks.append(protected_chunk)
            
            current_pos = region.end
        
        # Chunk remaining text
        if current_pos < len(text):
            final_chunks = self.standard_chunk(
                text[current_pos:],
                offset=current_pos
            )
            chunks.extend(final_chunks)
        
        return self.optimize_chunk_boundaries(chunks)
```

### 4. Quality Validation System

```python
class CohesionValidator:
    def validate_cohesion(self, chunks: List[CohesiveChunk]) -> CohesionReport:
        """Validate that cohesion is preserved"""
        
        violations = []
        
        # Check for split frameworks
        framework_violations = self.check_framework_integrity(chunks)
        violations.extend(framework_violations)
        
        # Check for fragmented lists
        list_violations = self.check_list_completeness(chunks)
        violations.extend(list_violations)
        
        # Check for orphaned examples
        example_violations = self.check_example_coherence(chunks)
        violations.extend(example_violations)
        
        return CohesionReport(
            total_chunks=len(chunks),
            violations=violations,
            cohesion_score=self.calculate_cohesion_score(chunks),
            atomic_preservation_rate=self.calculate_atomic_rate(chunks)
        )
    
    def check_framework_integrity(self, chunks: List[CohesiveChunk]) -> List[Violation]:
        """Ensure frameworks are never split"""
        violations = []
        
        for framework_type in FRAMEWORK_PATTERNS.keys():
            framework_chunks = [c for c in chunks if c.metadata.get('framework') == framework_type]
            
            for chunk in framework_chunks:
                components = self.extract_framework_components(chunk.text, framework_type)
                expected_components = FRAMEWORK_PATTERNS[framework_type]['components']
                
                missing_components = set(expected_components) - set(components)
                if missing_components:
                    violations.append(Violation(
                        type="SPLIT_FRAMEWORK",
                        severity="CRITICAL",
                        chunk_id=chunk.id,
                        description=f"{framework_type} missing components: {missing_components}"
                    ))
        
        return violations
```

## Data Structure Definitions

```python
@dataclass
class AtomicUnit:
    """Content that must never be split"""
    start: int
    end: int
    type: str  # "framework", "list", "sequence", "example"
    priority: str  # "ATOMIC", "HIGH", "MEDIUM"
    metadata: Dict[str, Any]
    cohesion_score: float  # 0.0 to 1.0

@dataclass
class CohesiveChunk:
    """Chunk with cohesion preservation"""
    chunk_id: str
    text: str
    start: int
    end: int
    type: str
    priority: str
    cohesion_score: float
    atomic_units: List[AtomicUnit]
    metadata: ChunkMetadata
    
@dataclass
class CohesionReport:
    """Validation report for cohesion quality"""
    total_chunks: int
    violations: List[Violation]
    cohesion_score: float
    atomic_preservation_rate: float
    framework_integrity_rate: float
    list_completeness_rate: float
```

## Implementation Strategy

### Phase 1: Core Detection (2 days)
1. Implement framework detection patterns
2. Build list detection algorithms
3. Create sequence identification logic
4. Add example-explanation pairing

### Phase 2: Chunking Integration (2 days)
1. Modify existing chunker to respect atomic units
2. Implement protected region management
3. Add boundary optimization
4. Create chunk metadata enrichment

### Phase 3: Validation System (1 day)
1. Build cohesion validation pipeline
2. Implement quality scoring
3. Add violation detection
4. Create reporting system

### Phase 4: Testing & Optimization (1 day)
1. Test with actual Hormozi content
2. Optimize detection parameters
3. Fine-tune boundary algorithms
4. Validate quality metrics

## Quality Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Framework Integrity | 100% | No split frameworks |
| List Completeness | 95% | Complete numbered lists |
| Example Coherence | 90% | Examples with explanations |
| Overall Cohesion Score | >0.85 | Weighted average |
| Processing Overhead | <20% | vs. standard chunking |

## Error Handling

```python
# Graceful degradation strategy
try:
    atomic_units = detect_atomic_units(text)
except DetectionError:
    # Fallback to simple pattern matching
    atomic_units = detect_basic_patterns(text)
    
try:
    cohesive_chunks = chunk_with_cohesion(text, atomic_units)
except ChunkingError:
    # Fallback to standard chunking with warnings
    cohesive_chunks = standard_chunk_with_warnings(text)
```

## Monitoring

Track these metrics:
- Atomic unit detection accuracy
- Cohesion preservation rate
- Framework integrity violations
- List fragmentation incidents
- Processing performance impact

This ensures content that belongs together stays together while maintaining system reliability and performance.