"""
Storage factory as specified in ARCHITECTURE.md extension points.

Follows DEVELOPMENT_RULES.md: "Configuration Over Code"
"""

from typing import Union
from ..config.settings import settings
from .interfaces import VectorDBInterface, DocumentStoreInterface, CacheInterface
from .chroma_db import ChromaVectorDB
from .memory_cache import MemoryCache


class StorageFactory:
    """
    Factory for creating storage instances.
    
    Implements ARCHITECTURE.md extension point: "Adding New Vector Database"
    """
    
    @staticmethod
    def create_vector_db() -> VectorDBInterface:
        """Create vector database based on configuration."""
        db_type = settings.VECTOR_DB_TYPE.lower()
        
        if db_type == "chroma":
            return ChromaVectorDB()
        elif db_type == "pinecone":
            # Future implementation
            raise NotImplementedError("Pinecone support not yet implemented")
        elif db_type == "weaviate":
            # Future implementation  
            raise NotImplementedError("Weaviate support not yet implemented")
        else:
            raise ValueError(f"Unsupported vector database type: {db_type}")
    
    @staticmethod
    def create_cache() -> CacheInterface:
        """Create cache based on configuration."""
        # For now, use in-memory cache
        # Can be extended to Redis when needed
        return MemoryCache()
    
    @staticmethod
    def create_document_store() -> DocumentStoreInterface:
        """Create document store based on configuration."""
        # Future implementation - for now, use vector DB for documents
        raise NotImplementedError("Separate document store not yet implemented")