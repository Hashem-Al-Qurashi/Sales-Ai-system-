"""
ChromaDB implementation of VectorDBInterface.

Follows ARCHITECTURE.md storage layer specification.
Implements DEVELOPMENT_RULES.md error handling hierarchy.
"""

import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError:
    raise ImportError("chromadb not installed. Run: pip install chromadb")

from ..config.settings import settings, DATA_DIR
from ..core.logger import get_logger
from .interfaces import VectorDBInterface, Document, SearchResult

logger = get_logger(__name__)


class ChromaVectorDB(VectorDBInterface):
    """
    ChromaDB implementation with proper error handling.
    
    Follows DEVELOPMENT_RULES.md: "Every operation can fail, plan for it"
    """
    
    def __init__(self):
        """Initialize ChromaDB client."""
        self.db_path = DATA_DIR / "vector_db"
        self.collection_name = "hormozi_frameworks"
        self.client = None
        self.collection = None
    
    def initialize(self) -> None:
        """
        Initialize ChromaDB connection with error handling.
        
        Follows DEVELOPMENT_RULES.md Level 3: System errors (circuit breaker)
        """
        try:
            self.db_path.mkdir(parents=True, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=False
                )
            )
            
            # Create or get collection
            try:
                self.collection = self.client.get_collection(self.collection_name)
                logger.info(f"Connected to existing collection: {self.collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={
                        "description": "Hormozi RAG Framework Storage",
                        "embedding_model": settings.EMBEDDING_MODEL,
                        "dimensions": settings.EMBEDDING_DIMENSIONS
                    }
                )
                logger.info(f"Created new collection: {self.collection_name}")
                
        except Exception as e:
            logger.critical(f"Failed to initialize ChromaDB: {e}")
            raise ConnectionError(f"ChromaDB initialization failed: {e}")
    
    def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents with proper error handling.
        
        Follows ARCHITECTURE.md contract: Document structure
        """
        if not self.collection:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")
        
        if not documents:
            logger.warning("No documents provided to add")
            return
        
        try:
            # Prepare data for ChromaDB
            ids = []
            embeddings = []
            metadatas = []
            doc_texts = []
            
            for doc in documents:
                if not doc.embedding:
                    raise ValueError(f"Document {doc.id} missing embedding")
                
                if len(doc.embedding) != settings.EMBEDDING_DIMENSIONS:
                    raise ValueError(
                        f"Document {doc.id} embedding dimension mismatch: "
                        f"expected {settings.EMBEDDING_DIMENSIONS}, got {len(doc.embedding)}"
                    )
                
                ids.append(doc.id)
                embeddings.append(doc.embedding)
                metadatas.append(doc.metadata)
                doc_texts.append(doc.text)
            
            # Add to ChromaDB in batches
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch_end = min(i + batch_size, len(documents))
                
                self.collection.add(
                    ids=ids[i:batch_end],
                    embeddings=embeddings[i:batch_end],
                    metadatas=metadatas[i:batch_end],
                    documents=doc_texts[i:batch_end]
                )
                
                logger.debug(f"Added batch {i//batch_size + 1}: {batch_end - i} documents")
            
            logger.info(f"Successfully added {len(documents)} documents to ChromaDB")
            
        except Exception as e:
            logger.error(f"Failed to add documents to ChromaDB: {e}")
            raise
    
    def search(self, query_embedding: List[float], top_k: int = 10, 
               filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        Search for similar documents.
        
        Follows ARCHITECTURE.md retrieval contract
        """
        if not self.collection:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")
        
        try:
            # Validate query embedding
            if len(query_embedding) != settings.EMBEDDING_DIMENSIONS:
                raise ValueError(
                    f"Query embedding dimension mismatch: "
                    f"expected {settings.EMBEDDING_DIMENSIONS}, got {len(query_embedding)}"
                )
            
            # Perform search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, settings.MAX_CHUNKS_PER_QUERY),
                where=filters
            )
            
            # Convert to SearchResult format
            search_results = []
            if results['documents'] and results['documents'][0]:
                for i, (doc_id, distance, metadata, text) in enumerate(zip(
                    results['ids'][0],
                    results['distances'][0], 
                    results['metadatas'][0],
                    results['documents'][0]
                )):
                    # Convert distance to similarity score (ChromaDB returns distances)
                    score = 1.0 - distance if distance <= 1.0 else 0.0
                    
                    document = Document(
                        id=doc_id,
                        text=text,
                        metadata=metadata or {}
                    )
                    
                    search_results.append(SearchResult(
                        document=document,
                        score=score,
                        rank=i + 1
                    ))
            
            logger.debug(f"Found {len(search_results)} results for query")
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def delete_documents(self, document_ids: List[str]) -> None:
        """Delete documents by IDs."""
        if not self.collection:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")
        
        try:
            self.collection.delete(ids=document_ids)
            logger.info(f"Deleted {len(document_ids)} documents")
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            raise
    
    def health_check(self) -> bool:
        """
        Health check as required by ARCHITECTURE.md.
        
        Implements /health endpoints pattern
        """
        try:
            if not self.client or not self.collection:
                return False
            
            # Try a simple operation
            count = self.collection.count()
            logger.debug(f"ChromaDB health check passed: {count} documents")
            return True
            
        except Exception as e:
            logger.warning(f"ChromaDB health check failed: {e}")
            return False