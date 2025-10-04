"""
PDF extraction module with framework boundary detection.

This module handles PDF text extraction while preserving the structure
and boundaries of Alex Hormozi's frameworks from $100M Offers.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
import pdfplumber
from tqdm import tqdm

from ..config.settings import settings
from ..core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedPage:
    """Represents an extracted page from a PDF."""
    
    page_number: int
    text: str
    chapter: Optional[str] = None
    section: Optional[str] = None
    detected_frameworks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FrameworkBoundary:
    """Represents a detected framework boundary in the text."""
    
    framework_name: str
    start_page: int
    end_page: int
    start_char: int
    end_char: int
    full_text: str
    components: List[str] = field(default_factory=list)
    priority: str = "BRONZE"


class PDFExtractor:
    """Handles PDF text extraction with framework awareness."""
    
    def __init__(self):
        """Initialize the PDF extractor."""
        self.framework_patterns = settings.framework.detection_patterns
        self.core_frameworks = settings.framework.core_frameworks
        self.extracted_pages: List[ExtractedPage] = []
        self.detected_frameworks: List[FrameworkBoundary] = []
    
    def extract_pdf(self, pdf_path: Path) -> List[ExtractedPage]:
        """Extract text from PDF with structure preservation.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of extracted pages with metadata
        """
        logger.info(f"Starting PDF extraction", pdf_path=str(pdf_path))
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        extracted_pages = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"Processing PDF", total_pages=total_pages)
                
                for page_num, page in enumerate(tqdm(pdf.pages, desc="Extracting pages"), 1):
                    text = self._extract_page_text(page)
                    
                    if text and len(text) >= settings.pdf.min_text_length:
                        # Detect chapter and section
                        chapter = self._detect_chapter(text, page_num)
                        section = self._detect_section(text)
                        
                        # Detect frameworks on this page
                        frameworks = self._detect_frameworks_on_page(text)
                        
                        extracted_page = ExtractedPage(
                            page_number=page_num,
                            text=text,
                            chapter=chapter,
                            section=section,
                            detected_frameworks=frameworks,
                            metadata={
                                "pdf_name": pdf_path.name,
                                "total_pages": total_pages,
                                "char_count": len(text)
                            }
                        )
                        
                        extracted_pages.append(extracted_page)
                        
                        logger.debug(
                            "Page extracted",
                            page_number=page_num,
                            char_count=len(text),
                            frameworks_detected=len(frameworks)
                        )
        
        except Exception as e:
            logger.error(f"Error extracting PDF", exception=e, pdf_path=str(pdf_path))
            raise
        
        self.extracted_pages = extracted_pages
        
        # Detect framework boundaries across pages
        self._detect_framework_boundaries()
        
        logger.info(
            "PDF extraction completed",
            pages_extracted=len(extracted_pages),
            frameworks_detected=len(self.detected_frameworks)
        )
        
        return extracted_pages
    
    def _extract_page_text(self, page) -> str:
        """Extract clean text from a PDF page.
        
        Args:
            page: pdfplumber page object
            
        Returns:
            Cleaned text from the page
        """
        try:
            text = page.extract_text()
            
            if not text:
                return ""
            
            # Clean the text
            text = self._clean_text(text)
            
            return text
            
        except Exception as e:
            logger.warning(f"Error extracting page text", exception=e)
            return ""
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text while preserving structure.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace while preserving paragraph breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Fix common extraction issues
        text = text.replace('', '')  # Remove null characters
        text = text.replace('\x00', '')
        
        # Normalize quotes and dashes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('—', '-').replace('–', '-')
        
        return text.strip()
    
    def _detect_chapter(self, text: str, page_num: int) -> Optional[str]:
        """Detect chapter from page text.
        
        Args:
            text: Page text
            page_num: Page number
            
        Returns:
            Detected chapter name or None
        """
        # Common chapter patterns in business books
        chapter_patterns = [
            r'Chapter\s+(\d+)[:\s]+([^\n]+)',
            r'CHAPTER\s+(\d+)[:\s]+([^\n]+)',
            r'Part\s+(\w+)[:\s]+([^\n]+)',
            r'Section\s+(\d+)[:\s]+([^\n]+)'
        ]
        
        for pattern in chapter_patterns:
            match = re.search(pattern, text[:500])  # Check first 500 chars
            if match:
                chapter_num = match.group(1)
                chapter_title = match.group(2).strip()
                return f"Chapter {chapter_num}: {chapter_title}"
        
        return None
    
    def _detect_section(self, text: str) -> Optional[str]:
        """Detect section headers from page text.
        
        Args:
            text: Page text
            
        Returns:
            Detected section name or None
        """
        # Look for section headers (usually in title case or all caps)
        lines = text.split('\n')
        
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            
            # Skip if too short or too long
            if len(line) < 5 or len(line) > 100:
                continue
            
            # Check if it looks like a section header
            if (line.isupper() or 
                (line[0].isupper() and sum(1 for c in line if c.isupper()) > len(line) * .2)):
                
                # Check if it contains framework keywords
                for framework_name, patterns in self.framework_patterns.items():
                    for pattern in patterns:
                        if pattern.lower() in line.lower():
                            return line
                
                # Check for common section indicators
                section_keywords = [
                    'framework', 'equation', 'formula', 'step', 
                    'principle', 'strategy', 'method', 'approach'
                ]
                
                if any(keyword in line.lower() for keyword in section_keywords):
                    return line
        
        return None
    
    def _detect_frameworks_on_page(self, text: str) -> List[str]:
        """Detect which frameworks are mentioned on this page.
        
        Args:
            text: Page text
            
        Returns:
            List of detected framework names
        """
        detected = []
        
        for framework_name, patterns in self.framework_patterns.items():
            for pattern in patterns:
                if pattern.lower() in text.lower():
                    if framework_name not in detected:
                        detected.append(framework_name)
                    break
        
        return detected
    
    def _detect_framework_boundaries(self):
        """Detect complete framework boundaries across all pages."""
        logger.info("Detecting framework boundaries across pages")
        
        full_text = "\n\n".join([page.text for page in self.extracted_pages])
        
        for framework_key, framework_info in self.core_frameworks.items():
            boundaries = self._find_framework_boundary(
                framework_key,
                framework_info,
                full_text
            )
            
            if boundaries:
                self.detected_frameworks.extend(boundaries)
                logger.info(
                    f"Framework boundaries detected",
                    framework=framework_key,
                    count=len(boundaries)
                )
    
    def _find_framework_boundary(self, framework_key: str, 
                                framework_info: Dict,
                                full_text: str) -> List[FrameworkBoundary]:
        """Find the boundaries of a specific framework in the text.
        
        Args:
            framework_key: Framework identifier
            framework_info: Framework configuration
            full_text: Complete text from all pages
            
        Returns:
            List of detected framework boundaries
        """
        boundaries = []
        patterns = self.framework_patterns.get(framework_key, [])
        
        if not patterns:
            return boundaries
        
        # Look for the strongest pattern match
        for pattern in patterns:
            # Case-insensitive search
            matches = list(re.finditer(
                re.escape(pattern), 
                full_text, 
                re.IGNORECASE
            ))
            
            for match in matches:
                start_pos = match.start()
                
                # Expand to find the complete framework explanation
                framework_text, start_char, end_char = self._expand_to_framework_bounds(
                    full_text,
                    start_pos,
                    framework_key,
                    framework_info
                )
                
                if framework_text and len(framework_text) > settings.pdf.min_text_length:
                    # Determine which pages this spans
                    start_page, end_page = self._find_page_span(start_char, end_char)
                    
                    # Extract framework components
                    components = self._extract_framework_components(
                        framework_text,
                        framework_info
                    )
                    
                    boundary = FrameworkBoundary(
                        framework_name=framework_info.get("name", framework_key),
                        start_page=start_page,
                        end_page=end_page,
                        start_char=start_char,
                        end_char=end_char,
                        full_text=framework_text,
                        components=components,
                        priority=framework_info.get("priority", "BRONZE")
                    )
                    
                    boundaries.append(boundary)
                    
                    # Only keep the first good match for each framework
                    break
            
            if boundaries:
                break
        
        return boundaries
    
    def _expand_to_framework_bounds(self, text: str, start_pos: int,
                                   framework_key: str, 
                                   framework_info: Dict) -> Tuple[str, int, int]:
        """Expand from a match point to capture the complete framework.
        
        Args:
            text: Full text
            start_pos: Starting position of match
            framework_key: Framework identifier
            framework_info: Framework configuration
            
        Returns:
            Tuple of (framework_text, start_char, end_char)
        """
        max_size = settings.chunking.framework_boundaries.get(
            framework_key,
            settings.chunking.default_chunk_size
        )
        
        # Find a good starting point (beginning of paragraph or section)
        start_char = start_pos
        for i in range(start_pos, max(0, start_pos - 500), -1):
            if i < len(text) and text[i:i+2] == '\n\n':
                start_char = i + 2
                break
        
        # Find a good ending point based on framework type
        end_char = min(start_pos + max_size, len(text))
        
        # For the Value Equation, look for the complete formula
        if framework_key == "value_equation":
            # Look for the end of the equation explanation
            equation_end_patterns = [
                "Effort & Sacrifice",
                "Effort and Sacrifice",
                "This is the value equation",
                "That's the entire equation"
            ]
            
            for pattern in equation_end_patterns:
                match = text.find(pattern, start_pos, end_char)
                if match != -1:
                    # Extend to end of paragraph
                    paragraph_end = text.find('\n\n', match, end_char)
                    if paragraph_end != -1:
                        end_char = paragraph_end
                    else:
                        end_char = min(match + 200, end_char)
                    break
        
        # For process frameworks, look for numbered steps
        elif framework_key == "offer_stack":
            # Look for the last step (usually step 5)
            step_pattern = r'(?:Step\s*)?5[.:\s)]'
            matches = list(re.finditer(step_pattern, text[start_pos:end_char], re.IGNORECASE))
            if matches:
                last_step = matches[-1]
                # Extend to end of that step's explanation
                paragraph_end = text.find('\n\n', start_pos + last_step.end(), end_char)
                if paragraph_end != -1:
                    end_char = paragraph_end
        
        # Extract and validate the framework text
        framework_text = text[start_char:end_char].strip()
        
        # Ensure we haven't cut off mid-sentence
        if framework_text and not framework_text[-1] in '.!?':
            # Try to find the end of the sentence
            sentence_end = text.find('.', end_char, end_char + 200)
            if sentence_end != -1:
                end_char = sentence_end + 1
                framework_text = text[start_char:end_char].strip()
        
        return framework_text, start_char, end_char
    
    def _find_page_span(self, start_char: int, end_char: int) -> Tuple[int, int]:
        """Find which pages a character range spans.
        
        Args:
            start_char: Starting character position in full text
            end_char: Ending character position in full text
            
        Returns:
            Tuple of (start_page, end_page)
        """
        char_count = 0
        start_page = 1
        end_page = 1
        
        for page in self.extracted_pages:
            page_start = char_count
            page_end = char_count + len(page.text) + 2  # +2 for page separator
            
            if page_start <= start_char < page_end:
                start_page = page.page_number
            
            if page_start < end_char <= page_end:
                end_page = page.page_number
                break
            
            char_count = page_end
        
        return start_page, end_page
    
    def _extract_framework_components(self, text: str, 
                                     framework_info: Dict) -> List[str]:
        """Extract specific components from framework text.
        
        Args:
            text: Framework text
            framework_info: Framework configuration
            
        Returns:
            List of detected components
        """
        components = []
        
        # Extract based on framework type
        if "components" in framework_info:
            # Look for specific components (e.g., Value Equation parts)
            component_patterns = {
                "dream_outcome": ["Dream Outcome", "what they want"],
                "perceived_likelihood": ["Perceived Likelihood", "likelihood of achievement"],
                "time_delay": ["Time Delay", "how long"],
                "effort_sacrifice": ["Effort", "Sacrifice", "what they have to"]
            }
            
            for component_key in framework_info["components"]:
                if component_key in component_patterns:
                    for pattern in component_patterns[component_key]:
                        if pattern.lower() in text.lower():
                            components.append(component_key)
                            break
        
        elif "steps" in framework_info:
            # Look for numbered steps
            step_count = framework_info["steps"]
            for i in range(1, step_count + 1):
                step_patterns = [
                    f"Step {i}",
                    f"{i}.",
                    f"{i})",
                    f"#{i}"
                ]
                
                for pattern in step_patterns:
                    if pattern in text:
                        components.append(f"step_{i}")
                        break
        
        elif "types" in framework_info:
            # Look for different types (e.g., guarantee types)
            for type_name in framework_info.get("types", []):
                if type_name.replace("_", " ").lower() in text.lower():
                    components.append(type_name)
        
        return components
    
    def get_framework_summary(self) -> Dict[str, Any]:
        """Get a summary of detected frameworks.
        
        Returns:
            Dictionary with framework detection summary
        """
        summary = {
            "total_pages": len(self.extracted_pages),
            "frameworks_detected": len(self.detected_frameworks),
            "frameworks": []
        }
        
        for framework in self.detected_frameworks:
            summary["frameworks"].append({
                "name": framework.framework_name,
                "pages": f"{framework.start_page}-{framework.end_page}",
                "components": framework.components,
                "priority": framework.priority,
                "text_length": len(framework.full_text)
            })
        
        return summary