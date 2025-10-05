"""
Generation engine interfaces as defined in ARCHITECTURE.md.

Implements LLM provider abstraction for extensibility.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class GenerationRequest:
    """Request for text generation as per ARCHITECTURE.md contracts."""
    query: str
    context: List[str]
    history: List[Dict[str, str]]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


@dataclass
class GenerationResponse:
    """Response from text generation as per ARCHITECTURE.md contracts."""
    answer: str
    sources: List[str]
    confidence: float
    metadata: Dict[str, Any]
    token_usage: Dict[str, int]


class LLMInterface(ABC):
    """
    LLM provider interface as specified in ARCHITECTURE.md.
    
    Extension point: "Adding New LLM Provider"
    """
    
    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate response from query and context."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the LLM provider is healthy."""
        pass
    
    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """Count tokens in text for usage tracking."""
        pass