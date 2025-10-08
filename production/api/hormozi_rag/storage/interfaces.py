"""
Storage layer interfaces as defined in ARCHITECTURE.md.

Implements clean abstraction for vector databases, document stores, and cache.
Follows DEVELOPMENT_RULES.md single responsibility principle.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Document:
    """Document representation as defined in ARCHITECTURE.md contracts."""
    id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass 
class SearchResult:
    """Search result as defined in ARCHITECTURE.md contracts."""
    document: Document
    score: float
    rank: int


class VectorDBInterface(ABC):
    """
    Vector database interface as specified in ARCHITECTURE.md.
    
    Extension point: "Adding New Vector Database"
    """
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the vector database connection."""
        pass
    
    @abstractmethod
    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the vector database."""
        pass
    
    @abstractmethod
    def search(self, query_embedding: List[float], top_k: int = 10, 
               filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Search for similar documents."""
        pass
    
    @abstractmethod
    def delete_documents(self, document_ids: List[str]) -> None:
        """Delete documents from the database."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the database is healthy."""
        pass


class DocumentStoreInterface(ABC):
    """
    Document store interface for metadata and raw text.
    
    Follows ARCHITECTURE.md storage layer specification.
    """
    
    @abstractmethod
    def store_document(self, document: Document) -> None:
        """Store a document with metadata."""
        pass
    
    @abstractmethod
    def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a document by ID."""
        pass
    
    @abstractmethod
    def update_metadata(self, document_id: str, metadata: Dict[str, Any]) -> None:
        """Update document metadata."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the document store is healthy."""
        pass


class CacheInterface(ABC):
    """
    Cache layer interface for performance optimization.
    
    As specified in ARCHITECTURE.md optimization points.
    """
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set cached value with optional TTL."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete cached value."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the cache is healthy."""
        pass