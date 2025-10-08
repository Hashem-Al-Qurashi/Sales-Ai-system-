"""
Hierarchical chunking system with framework preservation.

This module implements intelligent chunking that maintains the integrity
of Alex Hormozi's frameworks while creating optimal chunks for retrieval.
Enhanced with cohesion detection and validation.
"""

import re
import time
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from datetime import datetime

from ..config.settings import settings
from ..core.logger import get_logger
from ..extractors.pdf_extractor import ExtractedPage, FrameworkBoundary
from .cohesion_detector import CohesionDetector, AtomicUnit, AtomicType, ProtectedRegion
from .cohesion_validator import CohesionValidator, CohesiveChunk, CohesionReport

logger = get_logger(__name__)


class ContentType(Enum):
    """Types of content in the book."""
    DEFINITION = "definition"
    PROCESS = "process"
    EXAMPLE = "example"
    TEMPLATE = "template"


class Priority(Enum):
    """Content priority levels."""
    GOLD = "GOLD"
    SILVER = "SILVER"
    BRONZE = "BRONZE"


@dataclass
class Chunk:
    """Represents a text chunk with rich metadata."""
    
    # Core content
    content: str
    content_raw: str  # Without context header
    chunk_id: str
    
    # Framework information
    framework_name: Optional[str] = None
    framework_component: Optional[str] = None
    is_complete_framework: bool = False
    
    # Content classification
    content_type: ContentType = ContentType.EXAMPLE
    priority: Priority = Priority.BRONZE
    
    # Use cases and relationships
    use_cases: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    
    # Source information
    source_file: str = ""
    chapter: Optional[str] = None
    section: Optional[str] = None
    page_range: str = ""
    
    # Scoring and tracking
    importance_score: float = 5.0
    manual_quality_rating: float = 0.0
    usage_count: int = 0
    effectiveness_rating: float = 0.0
    
    # Technical metadata
    char_count: int = 0
    word_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    # Hierarchical information
    parent_chunk_id: Optional[str] = None
    child_chunk_ids: List[str] = field(default_factory=list)
    hierarchy_level: str = "paragraph"  # chapter, section, subsection, paragraph
    
    def __post_init__(self):
        """Post-initialization processing."""
        if not self.chunk_id:
            self.chunk_id = self._generate_chunk_id()
        
        self.char_count = len(self.content_raw)
        self.word_count = len(self.content_raw.split())
    
    def _generate_chunk_id(self) -> str:
        """Generate a unique chunk ID based on content."""
        content_hash = hashlib.md5(self.content_raw.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"chunk_{content_hash}_{timestamp}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary for storage."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "content_raw": self.content_raw,
            "framework_name": self.framework_name,
            "framework_component": self.framework_component,
            "is_complete_framework": self.is_complete_framework,
            "content_type": self.content_type.value,
            "priority": self.priority.value,
            "use_cases": self.use_cases,
            "prerequisites": self.prerequisites,
            "related_concepts": self.related_concepts,
            "source_file": self.source_file,
            "chapter": self.chapter,
            "section": self.section,
            "page_range": self.page_range,
            "importance_score": self.importance_score,
            "manual_quality_rating": self.manual_quality_rating,
            "usage_count": self.usage_count,
            "effectiveness_rating": self.effectiveness_rating,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "created_at": self.created_at.isoformat(),
            "parent_chunk_id": self.parent_chunk_id,
            "child_chunk_ids": self.child_chunk_ids,
            "hierarchy_level": self.hierarchy_level
        }


class HierarchicalChunker:
    """Implements hierarchical chunking with framework preservation and cohesion detection."""
    
    def __init__(self):
        """Initialize the chunker with cohesion components."""
        self.chunks: List[Chunk] = []
        self.framework_chunks: Dict[str, List[Chunk]] = {}
        self.hierarchy_map: Dict[str, List[str]] = {}
        
        # Cohesion system components
        self.cohesion_detector = CohesionDetector()
        self.cohesion_validator = CohesionValidator()
        self.enable_cohesion = getattr(settings.cohesion, 'enable_cohesion_detection', True)
    
    def chunk_documents(self, 
                       extracted_pages: List[ExtractedPage],
                       framework_boundaries: List[FrameworkBoundary],
                       source_file: str) -> List[Chunk]:
        """Create chunks from extracted pages with framework preservation.
        
        Args:
            extracted_pages: List of extracted PDF pages
            framework_boundaries: Detected framework boundaries
            source_file: Name of source PDF file
            
        Returns:
            List of chunks with rich metadata
        """
        logger.info("Starting hierarchical chunking", 
                   pages=len(extracted_pages),
                   frameworks=len(framework_boundaries))
        
        # First, create framework chunks (highest priority)
        self._create_framework_chunks(framework_boundaries, source_file)
        
        # Then, chunk remaining content
        self._chunk_non_framework_content(extracted_pages, framework_boundaries, source_file)
        
        # Build hierarchy relationships
        self._build_hierarchy()
        
        # Enrich metadata
        self._enrich_metadata()
        
        logger.info(f"Chunking completed",
                   total_chunks=len(self.chunks),
                   framework_chunks=len(self.framework_chunks))
        
        return self.chunks
    
    def _create_framework_chunks(self, 
                                framework_boundaries: List[FrameworkBoundary],
                                source_file: str):
        """Create chunks for complete frameworks.
        
        Args:
            framework_boundaries: Detected framework boundaries
            source_file: Name of source PDF file
        """
        for boundary in framework_boundaries:
            # Create context header
            context_header = self._create_context_header(
                source_file=source_file,
                chapter=f"Pages {boundary.start_page}-{boundary.end_page}",
                section=boundary.framework_name,
                framework=boundary.framework_name,
                page_range=f"{boundary.start_page}-{boundary.end_page}"
            )
            
            # Determine content type and priority
            content_type = self._determine_content_type(boundary.full_text)
            priority = Priority[boundary.priority]
            
            # Determine use cases
            use_cases = self._determine_use_cases(boundary.framework_name)
            
            # Create the framework chunk
            chunk = Chunk(
                content=context_header + "\n\n" + boundary.full_text,
                content_raw=boundary.full_text,
                chunk_id="",
                framework_name=boundary.framework_name,
                framework_component=None,
                is_complete_framework=True,
                content_type=content_type,
                priority=priority,
                use_cases=use_cases,
                prerequisites=self._get_prerequisites(boundary.framework_name),
                related_concepts=self._get_related_concepts(boundary.framework_name),
                source_file=source_file,
                chapter=f"Pages {boundary.start_page}-{boundary.end_page}",
                section=boundary.framework_name,
                page_range=f"{boundary.start_page}-{boundary.end_page}",
                importance_score=self._calculate_importance_score(boundary.framework_name, priority),
                manual_quality_rating=10.0 if priority == Priority.GOLD else 8.0,
                hierarchy_level="section"
            )
            
            self.chunks.append(chunk)
            
            # Store framework chunks separately for easy access
            if boundary.framework_name not in self.framework_chunks:
                self.framework_chunks[boundary.framework_name] = []
            self.framework_chunks[boundary.framework_name].append(chunk)
            
            # If framework has components, create sub-chunks for each
            if boundary.components:
                self._create_component_chunks(boundary, chunk, source_file)
            
            logger.debug(f"Created framework chunk",
                       framework=boundary.framework_name,
                       size=len(boundary.full_text),
                       components=len(boundary.components))
    
    def _create_component_chunks(self, 
                                boundary: FrameworkBoundary,
                                parent_chunk: Chunk,
                                source_file: str):
        """Create sub-chunks for framework components.
        
        Args:
            boundary: Framework boundary information
            parent_chunk: Parent framework chunk
            source_file: Name of source PDF file
        """
        # For Value Equation, create chunks for each component
        if boundary.framework_name == "Value Equation":
            component_patterns = {
                "dream_outcome": (
                    r"Dream Outcome[:\s]*([\s\S]*?)(?=Perceived Likelihood|Time Delay|$)",
                    ["offer_creation", "value_communication"]
                ),
                "perceived_likelihood": (
                    r"Perceived Likelihood[:\s]*([\s\S]*?)(?=Dream Outcome|Time Delay|Effort|$)",
                    ["objection_handling", "risk_reversal"]
                ),
                "time_delay": (
                    r"Time Delay[:\s]*([\s\S]*?)(?=Dream Outcome|Perceived|Effort|$)",
                    ["urgency_creation", "offer_creation"]
                ),
                "effort_sacrifice": (
                    r"Effort (?:&|and) Sacrifice[:\s]*([\s\S]*?)(?=Dream Outcome|Perceived|Time Delay|$)",
                    ["objection_handling", "value_communication"]
                )
            }
            
            for component_name, (pattern, use_cases) in component_patterns.items():
                match = re.search(pattern, boundary.full_text, re.IGNORECASE)
                if match:
                    component_text = match.group(1).strip()
                    
                    if component_text and len(component_text) > 50:
                        context_header = self._create_context_header(
                            source_file=source_file,
                            chapter=parent_chunk.chapter,
                            section=boundary.framework_name,
                            framework=boundary.framework_name,
                            component=component_name.replace("_", " ").title(),
                            page_range=parent_chunk.page_range
                        )
                        
                        component_chunk = Chunk(
                            content=context_header + "\n\n" + component_text,
                            content_raw=component_text,
                            chunk_id="",
                            framework_name=boundary.framework_name,
                            framework_component=component_name,
                            is_complete_framework=False,
                            content_type=ContentType.DEFINITION,
                            priority=Priority.GOLD,
                            use_cases=use_cases,
                            prerequisites=["understand_value_equation"],
                            related_concepts=[c for c in component_patterns.keys() if c != component_name],
                            source_file=source_file,
                            chapter=parent_chunk.chapter,
                            section=boundary.framework_name,
                            page_range=parent_chunk.page_range,
                            importance_score=9.0,
                            manual_quality_rating=10.0,
                            parent_chunk_id=parent_chunk.chunk_id,
                            hierarchy_level="subsection"
                        )
                        
                        self.chunks.append(component_chunk)
                        parent_chunk.child_chunk_ids.append(component_chunk.chunk_id)
                        
                        if boundary.framework_name not in self.framework_chunks:
                            self.framework_chunks[boundary.framework_name] = []
                        self.framework_chunks[boundary.framework_name].append(component_chunk)
    
    def _chunk_non_framework_content(self, 
                                    extracted_pages: List[ExtractedPage],
                                    framework_boundaries: List[FrameworkBoundary],
                                    source_file: str):
        """Chunk content that isn't part of complete frameworks.
        
        Args:
            extracted_pages: List of extracted PDF pages
            framework_boundaries: Detected framework boundaries
            source_file: Name of source PDF file
        """
        # Create a set of page ranges that are already in frameworks
        framework_pages = set()
        for boundary in framework_boundaries:
            for page in range(boundary.start_page, boundary.end_page + 1):
                framework_pages.add(page)
        
        # Process pages not fully covered by frameworks
        current_text = ""
        current_pages = []
        current_chapter = None
        current_section = None
        
        for page in extracted_pages:
            # Skip if this page is fully within a framework
            if page.page_number in framework_pages:
                # Save any accumulated text first
                if current_text:
                    self._create_standard_chunks(
                        current_text, 
                        current_pages, 
                        current_chapter,
                        current_section,
                        source_file
                    )
                    current_text = ""
                    current_pages = []
                continue
            
            # Update chapter/section if changed
            if page.chapter:
                current_chapter = page.chapter
            if page.section:
                current_section = page.section
            
            # Accumulate text
            current_text += "\n\n" + page.text
            current_pages.append(page.page_number)
            
            # Create chunks if we've accumulated enough
            if len(current_text) >= settings.chunking.default_chunk_size * 2:
                self._create_standard_chunks(
                    current_text,
                    current_pages,
                    current_chapter,
                    current_section,
                    source_file
                )
                current_text = ""
                current_pages = []
        
        # Don't forget the last chunk
        if current_text:
            self._create_standard_chunks(
                current_text,
                current_pages,
                current_chapter,
                current_section,
                source_file
            )
    
    def _create_standard_chunks(self, 
                               text: str,
                               pages: List[int],
                               chapter: Optional[str],
                               section: Optional[str],
                               source_file: str):
        """Create standard chunks with overlap.
        
        Args:
            text: Text to chunk
            pages: Page numbers covered
            chapter: Chapter name
            section: Section name
            source_file: Source file name
        """
        if not text.strip():
            return
        
        # Split into paragraphs first
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        current_size = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            para_size = len(paragraph)
            
            # If paragraph itself is too large, split it
            if para_size > settings.chunking.max_chunk_size:
                # Save current chunk if any
                if current_chunk:
                    self._save_standard_chunk(
                        current_chunk, pages, chapter, section, source_file
                    )
                    current_chunk = ""
                    current_size = 0
                
                # Split large paragraph
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                for sentence in sentences:
                    if current_size + len(sentence) > settings.chunking.default_chunk_size:
                        if current_chunk:
                            self._save_standard_chunk(
                                current_chunk, pages, chapter, section, source_file
                            )
                            # Add overlap
                            overlap_text = current_chunk[-settings.chunking.chunk_overlap:]
                            current_chunk = overlap_text + " " + sentence
                            current_size = len(current_chunk)
                        else:
                            current_chunk = sentence
                            current_size = len(sentence)
                    else:
                        current_chunk += " " + sentence
                        current_size += len(sentence)
            
            # If adding this paragraph exceeds limit, save current and start new
            elif current_size + para_size > settings.chunking.default_chunk_size:
                if current_chunk:
                    self._save_standard_chunk(
                        current_chunk, pages, chapter, section, source_file
                    )
                    # Add overlap
                    overlap_text = current_chunk[-settings.chunking.chunk_overlap:]
                    current_chunk = overlap_text + "\n\n" + paragraph
                    current_size = len(current_chunk)
                else:
                    current_chunk = paragraph
                    current_size = para_size
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
                current_size += para_size
        
        # Save any remaining chunk
        if current_chunk and len(current_chunk) >= settings.chunking.min_chunk_size:
            self._save_standard_chunk(
                current_chunk, pages, chapter, section, source_file
            )
    
    def _save_standard_chunk(self, 
                            text: str,
                            pages: List[int],
                            chapter: Optional[str],
                            section: Optional[str],
                            source_file: str):
        """Save a standard chunk with metadata.
        
        Args:
            text: Chunk text
            pages: Page numbers covered
            chapter: Chapter name
            section: Section name
            source_file: Source file name
        """
        # Determine content type and priority
        content_type = self._determine_content_type(text)
        priority = self._determine_priority(text)
        use_cases = self._determine_use_cases_from_text(text)
        
        # Create context header
        page_range = f"{min(pages)}-{max(pages)}" if len(pages) > 1 else str(pages[0])
        context_header = self._create_context_header(
            source_file=source_file,
            chapter=chapter,
            section=section,
            page_range=page_range
        )
        
        chunk = Chunk(
            content=context_header + "\n\n" + text,
            content_raw=text,
            chunk_id="",
            framework_name=self._detect_framework_reference(text),
            content_type=content_type,
            priority=priority,
            use_cases=use_cases,
            source_file=source_file,
            chapter=chapter,
            section=section,
            page_range=page_range,
            importance_score=self._calculate_importance_score(None, priority),
            hierarchy_level="paragraph"
        )
        
        self.chunks.append(chunk)
    
    def _create_context_header(self, 
                              source_file: str,
                              chapter: Optional[str] = None,
                              section: Optional[str] = None,
                              framework: Optional[str] = None,
                              component: Optional[str] = None,
                              page_range: str = "") -> str:
        """Create a context header for a chunk.
        
        Args:
            source_file: Name of source file
            chapter: Chapter name
            section: Section name
            framework: Framework name
            component: Framework component name
            page_range: Page range
            
        Returns:
            Formatted context header
        """
        header_lines = [f"Source: {source_file}"]
        
        if chapter:
            header_lines.append(f"Chapter: {chapter}")
        if section:
            header_lines.append(f"Section: {section}")
        if framework:
            header_lines.append(f"Framework: {framework}")
        if component:
            header_lines.append(f"Component: {component}")
        if page_range:
            header_lines.append(f"Page Range: {page_range}")
        
        return "\n".join(header_lines)
    
    def _determine_content_type(self, text: str) -> ContentType:
        """Determine the content type based on text analysis.
        
        Args:
            text: Text to analyze
            
        Returns:
            ContentType enum value
        """
        text_lower = text.lower()
        
        # Check for definitions
        definition_indicators = [
            "is defined as", "means", "refers to", "= ", 
            "equation", "formula", "principle"
        ]
        if any(indicator in text_lower for indicator in definition_indicators):
            return ContentType.DEFINITION
        
        # Check for processes
        process_indicators = [
            "step 1", "step 2", "first,", "second,", "then",
            "process", "method", "approach", "how to"
        ]
        if any(indicator in text_lower for indicator in process_indicators):
            return ContentType.PROCESS
        
        # Check for templates
        template_indicators = [
            "script", "template", "say this", "use this",
            "exact words", "verbatim"
        ]
        if any(indicator in text_lower for indicator in template_indicators):
            return ContentType.TEMPLATE
        
        # Default to example
        return ContentType.EXAMPLE
    
    def _determine_priority(self, text: str) -> Priority:
        """Determine content priority based on text analysis.
        
        Args:
            text: Text to analyze
            
        Returns:
            Priority enum value
        """
        text_lower = text.lower()
        
        # Check for GOLD priority indicators
        gold_indicators = [
            "value equation", "dream outcome", "perceived likelihood",
            "offer creation", "pricing psychology", "guarantee",
            "critical", "essential", "must", "framework"
        ]
        if sum(1 for ind in gold_indicators if ind in text_lower) >= 2:
            return Priority.GOLD
        
        # Check for SILVER priority indicators
        silver_indicators = [
            "bonus", "scarcity", "urgency", "example",
            "case study", "technique", "tactic"
        ]
        if any(indicator in text_lower for indicator in silver_indicators):
            return Priority.SILVER
        
        # Default to BRONZE
        return Priority.BRONZE
    
    def _determine_use_cases(self, framework_name: str) -> List[str]:
        """Determine use cases based on framework name.
        
        Args:
            framework_name: Name of the framework
            
        Returns:
            List of relevant use cases
        """
        use_case_map = {
            "Value Equation": ["offer_creation", "pricing", "value_communication"],
            "Offer Creation Stack": ["offer_creation"],
            "Pricing Psychology": ["pricing", "objection_handling"],
            "Guarantee Framework": ["guarantee_design", "risk_reversal", "objection_handling"],
            "Scarcity & Urgency": ["urgency_creation", "offer_creation"],
            "Bonus Strategy": ["bonus_creation", "value_stacking", "offer_creation"]
        }
        
        return use_case_map.get(framework_name, ["general"])
    
    def _determine_use_cases_from_text(self, text: str) -> List[str]:
        """Determine use cases based on text content.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of relevant use cases
        """
        use_cases = []
        text_lower = text.lower()
        
        use_case_keywords = {
            "offer_creation": ["create offer", "build offer", "structure offer"],
            "objection_handling": ["objection", "concern", "pushback", "resistance"],
            "pricing": ["price", "cost", "charge", "fee", "investment"],
            "guarantee_design": ["guarantee", "risk reversal", "promise"],
            "bonus_creation": ["bonus", "extra", "additional value"],
            "urgency_creation": ["urgency", "scarcity", "limited", "deadline"]
        }
        
        for use_case, keywords in use_case_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                use_cases.append(use_case)
        
        return use_cases if use_cases else ["general"]
    
    def _get_prerequisites(self, framework_name: str) -> List[str]:
        """Get prerequisites for understanding a framework.
        
        Args:
            framework_name: Name of the framework
            
        Returns:
            List of prerequisite concepts
        """
        prerequisites_map = {
            "Offer Creation Stack": ["understand_value_equation"],
            "Pricing Psychology": ["understand_value_equation"],
            "Guarantee Framework": ["understand_offer_structure"],
            "Bonus Strategy": ["understand_value_equation", "understand_offer_structure"]
        }
        
        return prerequisites_map.get(framework_name, [])
    
    def _get_related_concepts(self, framework_name: str) -> List[str]:
        """Get related concepts for a framework.
        
        Args:
            framework_name: Name of the framework
            
        Returns:
            List of related concept names
        """
        related_map = {
            "Value Equation": ["pricing_psychology", "offer_creation"],
            "Offer Creation Stack": ["value_equation", "bonus_strategy"],
            "Pricing Psychology": ["value_equation", "price_anchoring"],
            "Guarantee Framework": ["risk_reversal", "objection_handling"],
            "Scarcity & Urgency": ["limited_supply", "limited_time", "bonus_strategy"],
            "Bonus Strategy": ["value_stacking", "offer_creation"]
        }
        
        return related_map.get(framework_name, [])
    
    def _calculate_importance_score(self, 
                                   framework_name: Optional[str],
                                   priority: Priority) -> float:
        """Calculate importance score for a chunk.
        
        Args:
            framework_name: Name of framework (if applicable)
            priority: Content priority
            
        Returns:
            Importance score (0-10)
        """
        base_score = {
            Priority.GOLD: 8.0,
            Priority.SILVER: 6.0,
            Priority.BRONZE: 4.0
        }[priority]
        
        # Boost score for core frameworks
        if framework_name in ["Value Equation", "Offer Creation Stack"]:
            base_score += 2.0
        elif framework_name:
            base_score += 1.0
        
        return min(10.0, base_score)
    
    def _detect_framework_reference(self, text: str) -> Optional[str]:
        """Detect if text references a specific framework.
        
        Args:
            text: Text to analyze
            
        Returns:
            Framework name if detected, None otherwise
        """
        text_lower = text.lower()
        
        framework_keywords = {
            "Value Equation": ["value equation", "dream outcome", "perceived likelihood"],
            "Offer Creation Stack": ["offer creation", "identify dream", "list problems"],
            "Pricing Psychology": ["pricing psychology", "divergent pricing", "price anchor"],
            "Guarantee Framework": ["guarantee", "risk reversal", "conditional guarantee"],
            "Scarcity & Urgency": ["scarcity", "urgency", "limited time", "limited supply"],
            "Bonus Strategy": ["bonus", "stack value", "10x value"]
        }
        
        for framework_name, keywords in framework_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return framework_name
        
        return None
    
    def _build_hierarchy(self):
        """Build hierarchical relationships between chunks."""
        # Group chunks by chapter
        chapters = {}
        for chunk in self.chunks:
            if chunk.chapter:
                if chunk.chapter not in chapters:
                    chapters[chunk.chapter] = []
                chapters[chunk.chapter].append(chunk.chunk_id)
        
        self.hierarchy_map["chapters"] = chapters
        
        # Group chunks by framework
        frameworks = {}
        for chunk in self.chunks:
            if chunk.framework_name:
                if chunk.framework_name not in frameworks:
                    frameworks[chunk.framework_name] = []
                frameworks[chunk.framework_name].append(chunk.chunk_id)
        
        self.hierarchy_map["frameworks"] = frameworks
    
    def _enrich_metadata(self):
        """Enrich chunk metadata with additional information."""
        # Add cross-references between related chunks
        for chunk in self.chunks:
            if chunk.framework_name and chunk.framework_name in self.framework_chunks:
                # Link to other chunks from same framework
                related_chunks = self.framework_chunks[chunk.framework_name]
                chunk.related_concepts.extend([
                    c.chunk_id for c in related_chunks 
                    if c.chunk_id != chunk.chunk_id
                ])
    
    def get_chunking_summary(self) -> Dict[str, Any]:
        """Get a summary of the chunking results.
        
        Returns:
            Dictionary with chunking statistics
        """
        priority_counts = {p.value: 0 for p in Priority}
        content_type_counts = {ct.value: 0 for ct in ContentType}
        
        for chunk in self.chunks:
            priority_counts[chunk.priority.value] += 1
            content_type_counts[chunk.content_type.value] += 1
        
        return {
            "total_chunks": len(self.chunks),
            "framework_chunks": sum(len(chunks) for chunks in self.framework_chunks.values()),
            "avg_chunk_size": sum(c.char_count for c in self.chunks) / len(self.chunks) if self.chunks else 0,
            "priority_distribution": priority_counts,
            "content_type_distribution": content_type_counts,
            "frameworks_preserved": list(self.framework_chunks.keys())
        }
    
    def chunk_with_cohesion(self, text: str, source_file: str = "unknown") -> List[CohesiveChunk]:
        """Enhanced chunking method with cohesion preservation.
        
        This method integrates cohesion detection and validation to ensure
        that business frameworks, lists, and sequences stay together.
        
        Args:
            text: Input text to chunk
            source_file: Source file name for metadata
            
        Returns:
            List of cohesive chunks with preserved content integrity
        """
        start_time = time.time()
        
        # Level 1: Input validation (fail fast)
        if not text or not isinstance(text, str):
            raise ValueError("Text must be non-empty string")
        if len(text) < 50:
            raise ValueError("Text too short for meaningful chunking")
        
        try:
            # Level 2: Business logic with cohesion preservation
            if self.enable_cohesion:
                logger.info("Starting cohesion-aware chunking")
                
                # Step 1: Detect atomic units that cannot be split
                atomic_units = self.cohesion_detector.detect_atomic_units(text)
                logger.info(f"Detected {len(atomic_units)} atomic units")
                
                # Step 2: Create protected regions
                protected_regions = self._create_protected_regions(atomic_units)
                
                # Step 3: Chunk with protection
                chunks = self._chunk_respecting_protection(text, protected_regions, source_file)
                
                # Step 4: Validate cohesion
                validation_report = self.cohesion_validator.validate_chunks(chunks)
                
                if validation_report.has_critical_violations():
                    logger.error(f"Critical cohesion violations detected: {len(validation_report.get_violations_by_severity('CRITICAL'))}")
                    chunks = self.cohesion_validator.remediate_violations(chunks, validation_report)
                
                logger.info(f"Cohesion-aware chunking complete: {len(chunks)} chunks, "
                           f"score {validation_report.cohesion_score:.3f}")
                
            else:
                # Fallback to standard chunking
                logger.info("Cohesion detection disabled, using standard chunking")
                chunks = self._standard_chunk_text(text, source_file)
                
        except Exception as e:
            # Level 3: System error handling - graceful degradation
            logger.error(f"Cohesion chunking failed: {e}")
            logger.info("Falling back to standard chunking")
            chunks = self._standard_chunk_text(text, source_file)
        
        processing_time = time.time() - start_time
        logger.info(f"Total chunking time: {processing_time:.2f}s")
        
        return chunks
    
    def _create_protected_regions(self, atomic_units: List[AtomicUnit]) -> List[ProtectedRegion]:
        """Create protected regions from atomic units.
        
        Args:
            atomic_units: List of detected atomic units
            
        Returns:
            List of protected regions that cannot be split
        """
        if not atomic_units:
            return []
        
        # Sort by priority and position
        sorted_units = sorted(
            atomic_units,
            key=lambda u: (self._priority_score_numeric(u.priority), u.start_char)
        )
        
        protected_regions = []
        
        for unit in sorted_units:
            region = ProtectedRegion(
                start=unit.start_char,
                end=unit.end_char,
                type=unit.type,
                priority=unit.priority,
                atomic_units=[unit],
                reason=f"{unit.type.value}_{unit.framework_type or 'detected'}"
            )
            protected_regions.append(region)
        
        # Merge overlapping regions
        return self._merge_overlapping_regions(protected_regions)
    
    def _chunk_respecting_protection(self, text: str, protected_regions: List[ProtectedRegion], source_file: str) -> List[CohesiveChunk]:
        """Chunk text while respecting protected regions.
        
        Args:
            text: Text to chunk
            protected_regions: Regions that cannot be split
            source_file: Source file name
            
        Returns:
            List of cohesive chunks
        """
        chunks = []
        current_pos = 0
        
        # Sort protected regions by start position
        sorted_regions = sorted(protected_regions, key=lambda r: r.start)
        
        for region in sorted_regions:
            # Chunk text before protected region
            if current_pos < region.start:
                pre_chunks = self._standard_chunk_segment(
                    text[current_pos:region.start], 
                    offset=current_pos,
                    source_file=source_file
                )
                chunks.extend(pre_chunks)
            
            # Create atomic chunk for protected region
            atomic_chunk = self._create_atomic_chunk(text, region, source_file)
            chunks.append(atomic_chunk)
            
            current_pos = region.end
        
        # Chunk remaining text
        if current_pos < len(text):
            final_chunks = self._standard_chunk_segment(
                text[current_pos:],
                offset=current_pos,
                source_file=source_file
            )
            chunks.extend(final_chunks)
        
        return chunks
    
    def _create_atomic_chunk(self, text: str, region: ProtectedRegion, source_file: str) -> CohesiveChunk:
        """Create an atomic chunk from a protected region.
        
        Args:
            text: Full text
            region: Protected region
            source_file: Source file name
            
        Returns:
            Atomic cohesive chunk
        """
        chunk_text = text[region.start:region.end]
        
        # Generate chunk ID
        chunk_id = self._generate_atomic_chunk_id(region, source_file)
        
        # Create metadata
        metadata = {
            "source_file": source_file,
            "framework_complete": region.type == AtomicType.FRAMEWORK,
            "atomic_preservation": True,
            "preservation_method": region.reason,
            "safe_to_retrieve_alone": True,
            "region_type": region.type.value,
            "priority": region.priority.value
        }
        
        # Add framework-specific metadata
        if region.atomic_units:
            unit = region.atomic_units[0]
            if unit.framework_type:
                metadata["framework_type"] = unit.framework_type
                metadata["related_frameworks"] = self._get_related_concepts(unit.framework_type)
        
        return CohesiveChunk(
            chunk_id=chunk_id,
            text=chunk_text,
            start_char=region.start,
            end_char=region.end,
            chunk_type="atomic",
            atomic_units=region.atomic_units,
            cohesion_score=1.0,  # Perfect cohesion for atomic units
            metadata=metadata
        )
    
    def _standard_chunk_segment(self, text: str, offset: int, source_file: str) -> List[CohesiveChunk]:
        """Apply standard chunking to a text segment.
        
        Args:
            text: Text segment to chunk
            offset: Character offset in original text
            source_file: Source file name
            
        Returns:
            List of standard cohesive chunks
        """
        chunks = []
        chunk_size = settings.chunking.default_chunk_size
        overlap = settings.chunking.chunk_overlap
        
        current_pos = 0
        chunk_index = 0
        
        while current_pos < len(text):
            end_pos = min(current_pos + chunk_size, len(text))
            
            # Find good break point (sentence or paragraph boundary)
            if end_pos < len(text):
                end_pos = self._find_good_break_point(text, current_pos, end_pos)
            
            chunk_text = text[current_pos:end_pos]
            
            if len(chunk_text.strip()) > 50:  # Only create non-trivial chunks
                chunk_id = f"{source_file}_std_{chunk_index:03d}"
                
                chunk = CohesiveChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    start_char=offset + current_pos,
                    end_char=offset + end_pos,
                    chunk_type="standard",
                    atomic_units=[],
                    cohesion_score=0.7,  # Default score for standard chunks
                    metadata={
                        "source_file": source_file,
                        "chunk_method": "standard_segmentation",
                        "atomic_preservation": False
                    }
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # Move to next position with overlap
            current_pos = max(current_pos + 1, end_pos - overlap)
        
        return chunks
    
    def _standard_chunk_text(self, text: str, source_file: str) -> List[CohesiveChunk]:
        """Fallback standard chunking method.
        
        Args:
            text: Text to chunk
            source_file: Source file name
            
        Returns:
            List of standard chunks
        """
        return self._standard_chunk_segment(text, 0, source_file)
    
    def _priority_score_numeric(self, priority) -> int:
        """Convert priority to numeric score for sorting."""
        priority_map = {
            "CRITICAL": 3,
            "HIGH": 2, 
            "MEDIUM": 1,
            "LOW": 0
        }
        priority_str = priority.value if hasattr(priority, 'value') else str(priority)
        return priority_map.get(priority_str, 0)
    
    def _merge_overlapping_regions(self, regions: List[ProtectedRegion]) -> List[ProtectedRegion]:
        """Merge overlapping protected regions.
        
        Args:
            regions: List of protected regions
            
        Returns:
            List of non-overlapping merged regions
        """
        if not regions:
            return []
        
        # Sort by start position
        sorted_regions = sorted(regions, key=lambda r: r.start)
        merged = [sorted_regions[0]]
        
        for current in sorted_regions[1:]:
            last_merged = merged[-1]
            
            # Check for overlap
            if current.start <= last_merged.end:
                # Merge regions
                last_merged.end = max(last_merged.end, current.end)
                last_merged.atomic_units.extend(current.atomic_units)
                last_merged.reason += f", {current.reason}"
            else:
                merged.append(current)
        
        return merged
    
    def _generate_atomic_chunk_id(self, region: ProtectedRegion, source_file: str) -> str:
        """Generate ID for atomic chunk.
        
        Args:
            region: Protected region
            source_file: Source file name
            
        Returns:
            Unique chunk ID
        """
        # Extract base filename
        base_name = source_file.replace('.pdf', '').replace(' ', '_').lower()
        
        # Generate type-specific ID
        if region.type == AtomicType.FRAMEWORK and region.atomic_units:
            fw_type = region.atomic_units[0].framework_type or "framework"
            return f"{base_name}_{fw_type}_atomic"
        elif region.type == AtomicType.NUMBERED_LIST:
            return f"{base_name}_list_{region.start}_atomic"
        elif region.type == AtomicType.SEQUENCE:
            return f"{base_name}_seq_{region.start}_atomic"
        else:
            return f"{base_name}_{region.type.value}_{region.start}_atomic"
    
    def _find_good_break_point(self, text: str, start: int, end: int) -> int:
        """Find a good break point for chunking.
        
        Args:
            text: Text to search
            start: Start position
            end: Preferred end position
            
        Returns:
            Optimal break point
        """
        # Look for sentence endings within reasonable distance
        search_start = max(start, end - 200)  # Don't go too far back
        
        # Look for sentence endings
        for pos in range(end, search_start, -1):
            if pos < len(text) and text[pos] in '.!?':
                # Make sure it's not an abbreviation
                if pos + 1 < len(text) and text[pos + 1] in ' \n':
                    return pos + 1
        
        # Look for paragraph breaks
        for pos in range(end, search_start, -1):
            if pos < len(text) and text[pos] == '\n':
                if pos + 1 < len(text) and text[pos + 1] == '\n':
                    return pos + 1
        
        # Fallback to original end
        return end