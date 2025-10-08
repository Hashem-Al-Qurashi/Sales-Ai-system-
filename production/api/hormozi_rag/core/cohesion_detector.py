"""
Cohesion Detection Module for Hormozi RAG System.

This module detects content patterns that must stay together during chunking,
ensuring business frameworks, lists, and sequences remain intact.
"""

import re
import time
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

from ..config.settings import settings
from ..core.logger import get_logger

logger = get_logger(__name__)


class AtomicType(Enum):
    """Types of atomic content that cannot be split."""
    FRAMEWORK = "framework"
    NUMBERED_LIST = "numbered_list"
    SEQUENCE = "sequence"
    EXAMPLE_PAIR = "example_pair"


class Priority(Enum):
    """Priority levels for atomic units."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


@dataclass
class AtomicUnit:
    """Content that must never be split - Single Responsibility."""
    start_char: int
    end_char: int
    type: AtomicType
    framework_type: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    
    def __post_init__(self):
        """Input validation (Level 1 Error Handling)."""
        if self.start_char >= self.end_char:
            raise ValueError(f"Invalid character positions: {self.start_char} >= {self.end_char}")
        if self.start_char < 0:
            raise ValueError("Start position cannot be negative")
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
    
    @property
    def length(self) -> int:
        """Get the length of this atomic unit."""
        return self.end_char - self.start_char
    
    def overlaps_with(self, other: 'AtomicUnit') -> bool:
        """Check if this unit overlaps with another."""
        return not (self.end_char <= other.start_char or other.end_char <= self.start_char)


@dataclass
class ProtectedRegion:
    """Region that cannot be split during chunking."""
    start: int
    end: int
    type: AtomicType
    priority: Priority
    atomic_units: List[AtomicUnit]
    reason: str
    
    def __post_init__(self):
        """Validation for protected regions."""
        if self.start >= self.end:
            raise ValueError(f"Invalid region boundaries: {self.start} >= {self.end}")


class CohesionDetectionError(Exception):
    """Raised when cohesion detection fails."""
    pass


class CohesionDetector:
    """Detects content patterns that must stay together."""
    
    def __init__(self):
        """Initialize the cohesion detector."""
        self.framework_patterns = self._load_framework_patterns()
        self.list_patterns = self._compile_list_patterns()
        self.sequence_patterns = self._compile_sequence_patterns()
        self.example_patterns = self._compile_example_patterns()
        
        # Performance tracking
        self._detection_stats = {
            "frameworks_detected": 0,
            "lists_detected": 0,
            "sequences_detected": 0,
            "examples_detected": 0,
            "total_processing_time": 0.0
        }
    
    def detect_atomic_units(self, text: str) -> List[AtomicUnit]:
        """Main detection method - Single Responsibility."""
        start_time = time.time()
        
        # Level 1: Input validation (fail fast)
        if not text or not isinstance(text, str):
            raise ValueError("Text must be non-empty string")
        if len(text) < 10:
            raise ValueError("Text too short for meaningful detection")
        
        atomic_units = []
        
        try:
            # Level 2: Business logic with error recovery
            frameworks = self._detect_frameworks(text)
            atomic_units.extend(frameworks)
            logger.debug(f"Detected {len(frameworks)} frameworks")
            
            lists = self._detect_numbered_lists(text)
            atomic_units.extend(lists)
            logger.debug(f"Detected {len(lists)} numbered lists")
            
            sequences = self._detect_sequences(text)
            atomic_units.extend(sequences)
            logger.debug(f"Detected {len(sequences)} sequences")
            
            examples = self._detect_example_pairs(text)
            atomic_units.extend(examples)
            logger.debug(f"Detected {len(examples)} example pairs")
            
        except Exception as e:
            # Level 3: Graceful degradation
            logger.warning(f"Advanced detection failed: {e}")
            atomic_units.extend(self._basic_pattern_fallback(text))
        
        # Resolve overlaps and conflicts
        resolved_units = self._resolve_overlaps(atomic_units)
        
        # Update statistics
        processing_time = time.time() - start_time
        self._update_stats(resolved_units, processing_time)
        
        logger.info(f"Cohesion detection complete: {len(resolved_units)} atomic units in {processing_time:.2f}s")
        return resolved_units
    
    def _detect_frameworks(self, text: str) -> List[AtomicUnit]:
        """Detect Hormozi business frameworks."""
        frameworks = []
        
        for framework_type, patterns in self.framework_patterns.items():
            try:
                matches = self._find_framework_boundaries(text, framework_type, patterns)
                
                for match in matches:
                    if self._validate_framework_completeness(text, match, framework_type):
                        frameworks.append(AtomicUnit(
                            start_char=match['start'],
                            end_char=match['end'],
                            type=AtomicType.FRAMEWORK,
                            framework_type=framework_type,
                            priority=Priority.CRITICAL,
                            metadata={
                                "components": match.get('components', []),
                                "detection_method": "pattern_matching",
                                "confidence": match.get('confidence', 0.8)
                            },
                            confidence=match.get('confidence', 0.8)
                        ))
                        
            except Exception as e:
                logger.warning(f"Framework detection failed for {framework_type}: {e}")
                continue
        
        return frameworks
    
    def _detect_numbered_lists(self, text: str) -> List[AtomicUnit]:
        """Detect numbered and bulleted lists."""
        lists = []
        
        # Pattern for numbered lists: 1. 2. 3. or • • •
        list_pattern = r'(?:^\s*(?:\d+\.|[•\-\*])\s+.+(?:\n|$))+'
        matches = re.finditer(list_pattern, text, re.MULTILINE)
        
        for match in matches:
            try:
                items = self._extract_list_items(match.group())
                
                # Only preserve lists with minimum items
                min_items = getattr(settings.cohesion, 'list_min_items', 2)
                if len(items) >= min_items:
                    lists.append(AtomicUnit(
                        start_char=match.start(),
                        end_char=match.end(),
                        type=AtomicType.NUMBERED_LIST,
                        framework_type=None,
                        priority=Priority.HIGH,
                        metadata={
                            "item_count": len(items),
                            "items": items[:10],  # Store first 10 items for reference
                            "list_type": self._determine_list_type(match.group())
                        }
                    ))
                    
            except Exception as e:
                logger.warning(f"List processing failed: {e}")
                continue
        
        return lists
    
    def _detect_sequences(self, text: str) -> List[AtomicUnit]:
        """Detect step-by-step sequences."""
        sequences = []
        
        # Pattern for step sequences
        step_patterns = [
            r'(?:Step\s+\d+|First|Second|Third|Next|Then|Finally).*?(?=Step\s+\d+|First|Second|$)',
            r'(?:\d+\.\s+.+?\n){2,}',  # Numbered steps
            r'(?:Phase\s+\d+.*?\n){2,}'  # Phase sequences
        ]
        
        for pattern in step_patterns:
            try:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                grouped_steps = self._group_sequential_steps(matches, text)
                
                for group in grouped_steps:
                    min_steps = getattr(settings.cohesion, 'sequence_min_steps', 2)
                    if len(group['steps']) >= min_steps:
                        sequences.append(AtomicUnit(
                            start_char=group['start'],
                            end_char=group['end'],
                            type=AtomicType.SEQUENCE,
                            framework_type=group.get('sequence_type'),
                            priority=Priority.HIGH,
                            metadata={
                                "step_count": len(group['steps']),
                                "sequence_type": group.get('sequence_type', 'generic'),
                                "steps": group['steps'][:5]  # Store first 5 steps
                            }
                        ))
                        
            except Exception as e:
                logger.warning(f"Sequence detection failed for pattern {pattern}: {e}")
                continue
        
        return sequences
    
    def _detect_example_pairs(self, text: str) -> List[AtomicUnit]:
        """Detect example-explanation pairs."""
        examples = []
        
        example_triggers = [
            r'For example[,:]?\s*',
            r'Example[:\s]+',
            r'For instance[,:]?\s*',
            r'Let\'s say\s*',
            r'Imagine\s*'
        ]
        
        for trigger in example_triggers:
            try:
                matches = re.finditer(trigger, text, re.IGNORECASE)
                
                for match in matches:
                    example_end = self._find_example_end(text, match.end())
                    
                    if example_end > match.start() + 50:  # Minimum example length
                        examples.append(AtomicUnit(
                            start_char=match.start(),
                            end_char=example_end,
                            type=AtomicType.EXAMPLE_PAIR,
                            framework_type=None,
                            priority=Priority.MEDIUM,
                            metadata={
                                "trigger": match.group(),
                                "example_length": example_end - match.start()
                            }
                        ))
                        
            except Exception as e:
                logger.warning(f"Example detection failed for trigger {trigger}: {e}")
                continue
        
        return examples
    
    def _resolve_overlaps(self, atomic_units: List[AtomicUnit]) -> List[AtomicUnit]:
        """Resolve overlapping atomic units by priority."""
        if not atomic_units:
            return []
        
        # Sort by priority, then by confidence, then by start position
        sorted_units = sorted(
            atomic_units,
            key=lambda u: (
                self._priority_score(u.priority),
                -u.confidence,
                u.start_char
            )
        )
        
        resolved = []
        
        for unit in sorted_units:
            # Check for overlaps with already resolved units
            has_overlap = False
            
            for existing in resolved:
                if unit.overlaps_with(existing):
                    # Keep the higher priority unit
                    if self._priority_score(unit.priority) > self._priority_score(existing.priority):
                        resolved.remove(existing)
                        resolved.append(unit)
                    has_overlap = True
                    break
            
            if not has_overlap:
                resolved.append(unit)
        
        return sorted(resolved, key=lambda u: u.start_char)
    
    def _load_framework_patterns(self) -> Dict[str, Dict]:
        """Load Hormozi framework detection patterns."""
        return {
            "value_equation": {
                "start_markers": [
                    r"Value\s*=",
                    r"value equation",
                    r"dream outcome.*perceived likelihood"
                ],
                "components": ["dream outcome", "perceived likelihood", "time delay", "effort"],
                "end_markers": [r"\n\n", r"next chapter", r"another framework"],
                "required_components": 3  # Must find at least 3 components
            },
            "offer_stack": {
                "start_markers": [
                    r"offer creation",
                    r"step 1.*identify",
                    r"offer stack",
                    r"grand slam offer"
                ],
                "components": ["step 1", "step 2", "step 3", "step 4", "step 5"],
                "end_markers": [r"step 6", r"\n\n", r"next section"],
                "required_components": 4
            },
            "guarantee_framework": {
                "start_markers": [
                    r"guarantee framework",
                    r"unconditional guarantee",
                    r"types of guarantees"
                ],
                "components": ["unconditional", "conditional", "anti-guarantee", "implied"],
                "end_markers": [r"\n\n", r"bonus strategy", r"next framework"],
                "required_components": 2
            }
        }
    
    def _compile_list_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for list detection."""
        patterns = [
            re.compile(r'^\s*\d+\.\s+.+$', re.MULTILINE),  # Numbered lists
            re.compile(r'^\s*[•\-\*]\s+.+$', re.MULTILINE),  # Bulleted lists
            re.compile(r'^\s*[a-z]\)\s+.+$', re.MULTILINE),  # Lettered lists
        ]
        return patterns
    
    def _compile_sequence_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for sequence detection."""
        patterns = [
            re.compile(r'Step\s+\d+', re.IGNORECASE),
            re.compile(r'Phase\s+\d+', re.IGNORECASE),
            re.compile(r'(?:First|Second|Third|Fourth|Fifth)', re.IGNORECASE),
            re.compile(r'(?:Next|Then|Finally|Lastly)', re.IGNORECASE),
        ]
        return patterns
    
    def _compile_example_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for example detection."""
        patterns = [
            re.compile(r'For example[,:]?\s*', re.IGNORECASE),
            re.compile(r'Example[:\s]+', re.IGNORECASE),
            re.compile(r'For instance[,:]?\s*', re.IGNORECASE),
        ]
        return patterns
    
    def _find_framework_boundaries(self, text: str, framework_type: str, patterns: Dict) -> List[Dict]:
        """Find start and end boundaries for frameworks."""
        matches = []
        
        for start_marker in patterns['start_markers']:
            for match in re.finditer(start_marker, text, re.IGNORECASE):
                start_pos = match.start()
                
                # Find end boundary
                end_pos = self._find_framework_end(text, start_pos, patterns['end_markers'])
                
                # Validate components are present
                framework_text = text[start_pos:end_pos]
                components_found = self._count_framework_components(framework_text, patterns['components'])
                
                if components_found >= patterns.get('required_components', 1):
                    matches.append({
                        'start': start_pos,
                        'end': end_pos,
                        'components': components_found,
                        'confidence': min(1.0, components_found / len(patterns['components']))
                    })
        
        return matches
    
    def _basic_pattern_fallback(self, text: str) -> List[AtomicUnit]:
        """Fallback to basic pattern detection when advanced detection fails."""
        logger.info("Using basic pattern fallback for cohesion detection")
        basic_units = []
        
        # Simple numbered list detection
        simple_lists = re.finditer(r'(?:\d+\.\s+.+\n){2,}', text, re.MULTILINE)
        for match in simple_lists:
            basic_units.append(AtomicUnit(
                start_char=match.start(),
                end_char=match.end(),
                type=AtomicType.NUMBERED_LIST,
                priority=Priority.MEDIUM,
                metadata={"detection_method": "fallback"}
            ))
        
        return basic_units
    
    # Helper methods (keeping under 50 lines each per development rules)
    def _priority_score(self, priority: Priority) -> int:
        """Convert priority to numeric score for sorting."""
        return {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1}.get(priority.value, 0)
    
    def _extract_list_items(self, list_text: str) -> List[str]:
        """Extract individual items from a list."""
        lines = list_text.strip().split('\n')
        items = []
        for line in lines:
            line = line.strip()
            if re.match(r'^\s*(?:\d+\.|[•\-\*])', line):
                items.append(line)
        return items
    
    def _determine_list_type(self, list_text: str) -> str:
        """Determine the type of list (numbered, bulleted, etc.)."""
        if re.search(r'^\s*\d+\.', list_text, re.MULTILINE):
            return "numbered"
        elif re.search(r'^\s*[•\-\*]', list_text, re.MULTILINE):
            return "bulleted"
        else:
            return "unknown"
    
    def _group_sequential_steps(self, matches, text: str) -> List[Dict]:
        """Group sequential step matches into coherent sequences."""
        # Simplified implementation - can be enhanced
        groups = []
        for match in matches:
            groups.append({
                'start': match.start(),
                'end': match.end(),
                'steps': [match.group()],
                'sequence_type': 'step_sequence'
            })
        return groups
    
    def _find_example_end(self, text: str, start_pos: int) -> int:
        """Find the end of an example section."""
        # Look for natural boundaries
        end_markers = ['\n\n', '. Another', '. Next', '. However']
        
        search_text = text[start_pos:start_pos + 1000]  # Search within 1000 chars
        
        min_end = start_pos + len(search_text)
        for marker in end_markers:
            pos = search_text.find(marker)
            if pos != -1:
                min_end = min(min_end, start_pos + pos)
        
        return min_end
    
    def _validate_framework_completeness(self, text: str, match: Dict, framework_type: str) -> bool:
        """Validate that a framework match is complete."""
        # Basic validation - ensure minimum length and component presence
        framework_text = text[match['start']:match['end']]
        return len(framework_text) > 100 and match.get('components', 0) > 0
    
    def _find_framework_end(self, text: str, start_pos: int, end_markers: List[str]) -> int:
        """Find the end position of a framework."""
        search_text = text[start_pos:start_pos + 5000]  # Search within 5000 chars
        
        end_pos = start_pos + len(search_text)
        for marker in end_markers:
            pos = search_text.find(marker)
            if pos != -1:
                end_pos = min(end_pos, start_pos + pos)
        
        return end_pos
    
    def _count_framework_components(self, framework_text: str, components: List[str]) -> int:
        """Count how many framework components are present."""
        count = 0
        for component in components:
            if re.search(component, framework_text, re.IGNORECASE):
                count += 1
        return count
    
    def _update_stats(self, atomic_units: List[AtomicUnit], processing_time: float):
        """Update detection statistics."""
        self._detection_stats["total_processing_time"] += processing_time
        
        for unit in atomic_units:
            if unit.type == AtomicType.FRAMEWORK:
                self._detection_stats["frameworks_detected"] += 1
            elif unit.type == AtomicType.NUMBERED_LIST:
                self._detection_stats["lists_detected"] += 1
            elif unit.type == AtomicType.SEQUENCE:
                self._detection_stats["sequences_detected"] += 1
            elif unit.type == AtomicType.EXAMPLE_PAIR:
                self._detection_stats["examples_detected"] += 1
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get detection statistics for monitoring."""
        return self._detection_stats.copy()