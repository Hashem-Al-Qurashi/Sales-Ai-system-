"""
Cohesion Validation Module for Hormozi RAG System.

This module validates that content cohesion is preserved during chunking,
ensuring no business frameworks are split and quality standards are met.
"""

import time
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

from .cohesion_detector import AtomicUnit, AtomicType, Priority
from ..config.settings import settings
from ..core.logger import get_logger

logger = get_logger(__name__)


class ViolationSeverity(Enum):
    """Severity levels for cohesion violations."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class CohesionViolation:
    """Represents a cohesion preservation violation."""
    severity: ViolationSeverity
    violation_type: str
    chunk_id: str
    description: str
    affected_content: str
    suggestion: str
    
    def __post_init__(self):
        """Validate violation data."""
        if not self.chunk_id:
            raise ValueError("Chunk ID cannot be empty")
        if not self.description:
            raise ValueError("Description cannot be empty")


@dataclass
class CohesiveChunk:
    """Enhanced chunk with cohesion metadata."""
    chunk_id: str
    text: str
    start_char: int
    end_char: int
    chunk_type: str  # "atomic", "cohesive", "standard"
    atomic_units: List[AtomicUnit] = field(default_factory=list)
    cohesion_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate chunk data."""
        if self.start_char >= self.end_char:
            raise ValueError(f"Invalid chunk boundaries: {self.start_char} >= {self.end_char}")
        if self.cohesion_score < 0.0 or self.cohesion_score > 1.0:
            raise ValueError("Cohesion score must be between 0.0 and 1.0")
    
    def is_atomic(self) -> bool:
        """Check if chunk contains atomic content."""
        return len(self.atomic_units) > 0 and self.chunk_type == "atomic"
    
    def has_framework(self, framework_type: str) -> bool:
        """Check if chunk contains a specific framework."""
        return any(
            unit.type == AtomicType.FRAMEWORK and unit.framework_type == framework_type
            for unit in self.atomic_units
        )
    
    @property
    def length(self) -> int:
        """Get chunk length in characters."""
        return self.end_char - self.start_char


@dataclass
class CohesionReport:
    """Comprehensive cohesion validation report."""
    total_chunks: int
    atomic_chunks: int
    violations: List[CohesionViolation]
    cohesion_score: float
    framework_integrity_rate: float
    list_completeness_rate: float
    example_coherence_rate: float
    processing_time_ms: int
    
    def has_violations(self) -> bool:
        """Check if report has any violations."""
        return len(self.violations) > 0
    
    def has_critical_violations(self) -> bool:
        """Check if report has critical violations."""
        return any(v.severity == ViolationSeverity.CRITICAL for v in self.violations)
    
    def get_violations_by_severity(self, severity: ViolationSeverity) -> List[CohesionViolation]:
        """Get violations of specific severity."""
        return [v for v in self.violations if v.severity == severity]


class CohesionValidationError(Exception):
    """Raised when cohesion validation encounters an error."""
    pass


class CohesionValidator:
    """Validates cohesion preservation quality - Single Responsibility."""
    
    def __init__(self):
        """Initialize the cohesion validator."""
        self.framework_patterns = self._load_framework_validation_patterns()
        self.quality_thresholds = self._load_quality_thresholds()
        
        # Statistics tracking
        self._validation_stats = {
            "total_validations": 0,
            "violations_found": 0,
            "critical_violations": 0,
            "total_processing_time": 0.0
        }
    
    def validate_chunks(self, chunks: List[CohesiveChunk]) -> CohesionReport:
        """Main validation method - comprehensive cohesion validation."""
        start_time = time.time()
        
        # Level 1: Input validation
        if not chunks:
            raise ValueError("Chunks list cannot be empty")
        if not all(isinstance(chunk, CohesiveChunk) for chunk in chunks):
            raise TypeError("All items must be CohesiveChunk instances")
        
        violations = []
        
        try:
            # Level 2: Business logic validation
            
            # Critical: Framework integrity (highest priority)
            framework_violations = self._validate_framework_integrity(chunks)
            violations.extend(framework_violations)
            
            # High: List completeness
            list_violations = self._validate_list_completeness(chunks)
            violations.extend(list_violations)
            
            # Medium: Example coherence
            example_violations = self._validate_example_coherence(chunks)
            violations.extend(example_violations)
            
            # Low: General cohesion quality
            quality_violations = self._validate_general_quality(chunks)
            violations.extend(quality_violations)
            
        except Exception as e:
            # Level 3: System error handling
            logger.error(f"Validation error: {e}")
            raise CohesionValidationError(f"Validation failed: {e}")
        
        # Calculate quality metrics
        cohesion_score = self._calculate_overall_cohesion_score(chunks)
        framework_rate = self._calculate_framework_integrity_rate(chunks)
        list_rate = self._calculate_list_completeness_rate(chunks)
        example_rate = self._calculate_example_coherence_rate(chunks)
        
        processing_time = int((time.time() - start_time) * 1000)  # ms
        
        # Update statistics
        self._update_validation_stats(violations, processing_time)
        
        report = CohesionReport(
            total_chunks=len(chunks),
            atomic_chunks=len([c for c in chunks if c.is_atomic()]),
            violations=violations,
            cohesion_score=cohesion_score,
            framework_integrity_rate=framework_rate,
            list_completeness_rate=list_rate,
            example_coherence_rate=example_rate,
            processing_time_ms=processing_time
        )
        
        logger.info(f"Cohesion validation complete: {len(violations)} violations, "
                   f"score {cohesion_score:.3f}, {processing_time}ms")
        
        return report
    
    def _validate_framework_integrity(self, chunks: List[CohesiveChunk]) -> List[CohesionViolation]:
        """Ensure business frameworks are never split - CRITICAL validation."""
        violations = []
        
        # Group chunks by framework type
        framework_chunks = self._group_chunks_by_framework(chunks)
        
        for framework_type, fw_chunks in framework_chunks.items():
            if len(fw_chunks) > 1:
                # CRITICAL: Framework split across multiple chunks
                violations.append(CohesionViolation(
                    severity=ViolationSeverity.CRITICAL,
                    violation_type="SPLIT_FRAMEWORK",
                    chunk_id=fw_chunks[0].chunk_id,
                    description=f"{framework_type} framework split across {len(fw_chunks)} chunks",
                    affected_content=framework_type,
                    suggestion=f"Merge chunks containing {framework_type} framework"
                ))
            else:
                # Check framework completeness within single chunk
                chunk = fw_chunks[0]
                if not self._validate_framework_completeness(chunk, framework_type):
                    violations.append(CohesionViolation(
                        severity=ViolationSeverity.HIGH,
                        violation_type="INCOMPLETE_FRAMEWORK",
                        chunk_id=chunk.chunk_id,
                        description=f"{framework_type} framework incomplete in chunk",
                        affected_content=framework_type,
                        suggestion=f"Ensure all {framework_type} components are present"
                    ))
        
        return violations
    
    def _validate_list_completeness(self, chunks: List[CohesiveChunk]) -> List[CohesionViolation]:
        """Ensure numbered lists are complete - HIGH priority."""
        violations = []
        
        for chunk in chunks:
            list_units = [unit for unit in chunk.atomic_units if unit.type == AtomicType.NUMBERED_LIST]
            
            for list_unit in list_units:
                if not self._is_list_complete(chunk, list_unit):
                    violations.append(CohesionViolation(
                        severity=ViolationSeverity.HIGH,
                        violation_type="INCOMPLETE_LIST",
                        chunk_id=chunk.chunk_id,
                        description=f"Numbered list appears incomplete",
                        affected_content=f"List with {list_unit.metadata.get('item_count', 0)} items",
                        suggestion="Verify all list items are present in chunk"
                    ))
        
        return violations
    
    def _validate_example_coherence(self, chunks: List[CohesiveChunk]) -> List[CohesionViolation]:
        """Ensure examples stay with their explanations - MEDIUM priority."""
        violations = []
        
        for chunk in chunks:
            example_units = [unit for unit in chunk.atomic_units if unit.type == AtomicType.EXAMPLE_PAIR]
            
            for example_unit in example_units:
                if not self._is_example_coherent(chunk, example_unit):
                    violations.append(CohesionViolation(
                        severity=ViolationSeverity.MEDIUM,
                        violation_type="INCOHERENT_EXAMPLE",
                        chunk_id=chunk.chunk_id,
                        description="Example may be separated from its explanation",
                        affected_content=f"Example starting with '{example_unit.metadata.get('trigger', 'N/A')}'",
                        suggestion="Ensure example and explanation are in same chunk"
                    ))
        
        return violations
    
    def _validate_general_quality(self, chunks: List[CohesiveChunk]) -> List[CohesionViolation]:
        """Validate general cohesion quality metrics - LOW priority."""
        violations = []
        
        for chunk in chunks:
            # Check chunk size for atomic units
            if chunk.is_atomic() and chunk.length > 5000:
                violations.append(CohesionViolation(
                    severity=ViolationSeverity.LOW,
                    violation_type="OVERSIZED_ATOMIC_CHUNK",
                    chunk_id=chunk.chunk_id,
                    description=f"Atomic chunk is very large ({chunk.length} chars)",
                    affected_content="Entire chunk",
                    suggestion="Consider if this atomic unit can be safely subdivided"
                ))
            
            # Check cohesion score
            if chunk.cohesion_score < self.quality_thresholds.get('min_cohesion_score', 0.5):
                violations.append(CohesionViolation(
                    severity=ViolationSeverity.LOW,
                    violation_type="LOW_COHESION_SCORE",
                    chunk_id=chunk.chunk_id,
                    description=f"Low cohesion score ({chunk.cohesion_score:.3f})",
                    affected_content="Chunk content quality",
                    suggestion="Review chunk boundaries and content coherence"
                ))
        
        return violations
    
    def _group_chunks_by_framework(self, chunks: List[CohesiveChunk]) -> Dict[str, List[CohesiveChunk]]:
        """Group chunks by the frameworks they contain."""
        framework_chunks = {}
        
        for chunk in chunks:
            for atomic_unit in chunk.atomic_units:
                if atomic_unit.type == AtomicType.FRAMEWORK and atomic_unit.framework_type:
                    fw_type = atomic_unit.framework_type
                    if fw_type not in framework_chunks:
                        framework_chunks[fw_type] = []
                    framework_chunks[fw_type].append(chunk)
        
        return framework_chunks
    
    def _validate_framework_completeness(self, chunk: CohesiveChunk, framework_type: str) -> bool:
        """Check if a framework is complete within a chunk."""
        if framework_type not in self.framework_patterns:
            return True  # Unknown framework, assume complete
        
        pattern_info = self.framework_patterns[framework_type]
        required_components = pattern_info.get('required_components', [])
        
        # Count components present in chunk text
        components_found = 0
        for component in required_components:
            if component.lower() in chunk.text.lower():
                components_found += 1
        
        # Consider complete if most components are present
        min_components = len(required_components) * 0.75  # 75% threshold
        return components_found >= min_components
    
    def _is_list_complete(self, chunk: CohesiveChunk, list_unit: AtomicUnit) -> bool:
        """Check if a numbered list appears complete."""
        item_count = list_unit.metadata.get('item_count', 0)
        
        # Basic heuristics for list completeness
        if item_count < 2:
            return False
        
        # Check if list appears to be cut off
        list_text = chunk.text[
            list_unit.start_char - chunk.start_char:
            list_unit.end_char - chunk.start_char
        ]
        
        # Simple check: last item should end properly
        lines = list_text.strip().split('\n')
        if not lines:
            return False
        
        last_line = lines[-1].strip()
        # If last line is very short or ends abruptly, might be incomplete
        return len(last_line) > 10 and not last_line.endswith(',')
    
    def _is_example_coherent(self, chunk: CohesiveChunk, example_unit: AtomicUnit) -> bool:
        """Check if an example and its explanation are coherent."""
        example_length = example_unit.metadata.get('example_length', 0)
        
        # Basic heuristics for example coherence
        if example_length < 50:
            return False  # Too short to be a complete example
        
        if example_length > 2000:
            return False  # Too long, might include unrelated content
        
        return True  # Assume coherent if length is reasonable
    
    def _calculate_overall_cohesion_score(self, chunks: List[CohesiveChunk]) -> float:
        """Calculate overall cohesion score for all chunks."""
        if not chunks:
            return 0.0
        
        total_score = sum(chunk.cohesion_score for chunk in chunks)
        return total_score / len(chunks)
    
    def _calculate_framework_integrity_rate(self, chunks: List[CohesiveChunk]) -> float:
        """Calculate framework integrity preservation rate."""
        framework_chunks = self._group_chunks_by_framework(chunks)
        
        if not framework_chunks:
            return 1.0  # No frameworks, perfect integrity
        
        intact_frameworks = sum(
            1 for fw_chunks in framework_chunks.values()
            if len(fw_chunks) == 1  # Framework in single chunk
        )
        
        return intact_frameworks / len(framework_chunks)
    
    def _calculate_list_completeness_rate(self, chunks: List[CohesiveChunk]) -> float:
        """Calculate list completeness rate."""
        total_lists = 0
        complete_lists = 0
        
        for chunk in chunks:
            list_units = [unit for unit in chunk.atomic_units if unit.type == AtomicType.NUMBERED_LIST]
            total_lists += len(list_units)
            
            for list_unit in list_units:
                if self._is_list_complete(chunk, list_unit):
                    complete_lists += 1
        
        return complete_lists / total_lists if total_lists > 0 else 1.0
    
    def _calculate_example_coherence_rate(self, chunks: List[CohesiveChunk]) -> float:
        """Calculate example coherence rate."""
        total_examples = 0
        coherent_examples = 0
        
        for chunk in chunks:
            example_units = [unit for unit in chunk.atomic_units if unit.type == AtomicType.EXAMPLE_PAIR]
            total_examples += len(example_units)
            
            for example_unit in example_units:
                if self._is_example_coherent(chunk, example_unit):
                    coherent_examples += 1
        
        return coherent_examples / total_examples if total_examples > 0 else 1.0
    
    def _load_framework_validation_patterns(self) -> Dict[str, Dict]:
        """Load framework validation patterns."""
        return {
            "value_equation": {
                "required_components": [
                    "dream outcome", "perceived likelihood", 
                    "time delay", "effort", "sacrifice"
                ],
                "min_length": 500,
                "max_length": 3000
            },
            "offer_stack": {
                "required_components": [
                    "step 1", "step 2", "step 3", "step 4", "step 5"
                ],
                "min_length": 1000,
                "max_length": 4000
            },
            "guarantee_framework": {
                "required_components": [
                    "unconditional", "conditional", "anti-guarantee"
                ],
                "min_length": 400,
                "max_length": 2500
            }
        }
    
    def _load_quality_thresholds(self) -> Dict[str, float]:
        """Load quality thresholds for validation."""
        return {
            "min_cohesion_score": 0.5,
            "min_framework_integrity": 0.95,
            "min_list_completeness": 0.90,
            "min_example_coherence": 0.85
        }
    
    def _update_validation_stats(self, violations: List[CohesionViolation], processing_time: int):
        """Update validation statistics."""
        self._validation_stats["total_validations"] += 1
        self._validation_stats["violations_found"] += len(violations)
        self._validation_stats["critical_violations"] += len([
            v for v in violations if v.severity == ViolationSeverity.CRITICAL
        ])
        self._validation_stats["total_processing_time"] += processing_time
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics for monitoring."""
        return self._validation_stats.copy()
    
    def remediate_violations(self, chunks: List[CohesiveChunk], report: CohesionReport) -> List[CohesiveChunk]:
        """Attempt to remediate critical violations."""
        if not report.has_critical_violations():
            return chunks
        
        logger.warning(f"Attempting to remediate {len(report.get_violations_by_severity(ViolationSeverity.CRITICAL))} critical violations")
        
        # For now, return original chunks with warnings
        # In a full implementation, this would merge split frameworks
        for violation in report.get_violations_by_severity(ViolationSeverity.CRITICAL):
            logger.error(f"CRITICAL VIOLATION: {violation.description}")
        
        return chunks