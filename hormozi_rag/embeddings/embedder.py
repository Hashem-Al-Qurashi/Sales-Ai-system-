"""
Embedding generation pipeline with caching and batch processing.

This module handles the creation of vector embeddings for chunks
using OpenAI's text-embedding models with intelligent caching.
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from dataclasses import dataclass
import pickle
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import openai
from openai import OpenAI
from tqdm import tqdm

from ..config.settings import settings
from ..core.logger import get_logger
from ..core.chunker import Chunk

logger = get_logger(__name__)


@dataclass
class EmbeddedChunk:
    """Represents a chunk with its embedding."""
    
    chunk: Chunk
    embedding: np.ndarray
    embedding_model: str
    embedding_dim: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            **self.chunk.to_dict(),
            "embedding": self.embedding.tolist(),
            "embedding_model": self.embedding_model,
            "embedding_dim": self.embedding_dim
        }


class EmbeddingCache:
    """Manages caching of embeddings to avoid redundant API calls."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the embedding cache.
        
        Args:
            cache_dir: Directory for storing cached embeddings
        """
        self.cache_dir = cache_dir or settings.embedding.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "embedding_cache.pkl"
        self.cache: Dict[str, np.ndarray] = self._load_cache()
    
    def _load_cache(self) -> Dict[str, np.ndarray]:
        """Load existing cache from disk.
        
        Returns:
            Dictionary of cached embeddings
        """
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    cache = pickle.load(f)
                logger.info(f"Loaded embedding cache", entries=len(cache))
                return cache
            except Exception as e:
                logger.warning(f"Failed to load cache, starting fresh", exception=e)
                return {}
        return {}
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
            logger.debug(f"Saved embedding cache", entries=len(self.cache))
        except Exception as e:
            logger.error(f"Failed to save cache", exception=e)
    
    def get_cache_key(self, text: str, model: str) -> str:
        """Generate a cache key for text and model combination.
        
        Args:
            text: Text to embed
            model: Model name
            
        Returns:
            Cache key string
        """
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, text: str, model: str) -> Optional[np.ndarray]:
        """Get cached embedding if it exists.
        
        Args:
            text: Text to look up
            model: Model name
            
        Returns:
            Cached embedding or None
        """
        key = self.get_cache_key(text, model)
        return self.cache.get(key)
    
    def set(self, text: str, model: str, embedding: np.ndarray):
        """Store embedding in cache.
        
        Args:
            text: Original text
            model: Model name
            embedding: Embedding vector
        """
        key = self.get_cache_key(text, model)
        self.cache[key] = embedding
        
        # Periodically save cache
        if len(self.cache) % 100 == 0:
            self._save_cache()
    
    def flush(self):
        """Force save cache to disk."""
        self._save_cache()


class EmbeddingPipeline:
    """Handles embedding generation for chunks with batching and caching."""
    
    def __init__(self):
        """Initialize the embedding pipeline."""
        self.client = OpenAI(api_key=settings.embedding.api_key)
        self.model = settings.embedding.model_name
        self.dimensions = settings.embedding.dimensions
        self.cache = EmbeddingCache() if settings.embedding.cache_embeddings else None
        self.batch_size = settings.embedding.batch_size
    
    def embed_chunks(self, chunks: List[Chunk]) -> List[EmbeddedChunk]:
        """Generate embeddings for a list of chunks.
        
        Args:
            chunks: List of chunks to embed
            
        Returns:
            List of embedded chunks
        """
        logger.info(f"Starting embedding generation", chunks=len(chunks))
        
        embedded_chunks = []
        
        # Process in batches
        for i in tqdm(range(0, len(chunks), self.batch_size), desc="Embedding chunks"):
            batch = chunks[i:i + self.batch_size]
            batch_embeddings = self._embed_batch(batch)
            
            for chunk, embedding in zip(batch, batch_embeddings):
                if embedding is not None:
                    embedded_chunk = EmbeddedChunk(
                        chunk=chunk,
                        embedding=embedding,
                        embedding_model=self.model,
                        embedding_dim=self.dimensions
                    )
                    embedded_chunks.append(embedded_chunk)
        
        # Flush cache
        if self.cache:
            self.cache.flush()
        
        logger.info(f"Embedding generation completed",
                   total_chunks=len(chunks),
                   embedded=len(embedded_chunks))
        
        return embedded_chunks
    
    def _embed_batch(self, chunks: List[Chunk]) -> List[Optional[np.ndarray]]:
        """Embed a batch of chunks.
        
        Args:
            chunks: Batch of chunks to embed
            
        Returns:
            List of embeddings (None for failures)
        """
        embeddings = []
        texts_to_embed = []
        chunk_indices = []
        
        # Check cache first
        for i, chunk in enumerate(chunks):
            text = self._prepare_text_for_embedding(chunk)
            
            if self.cache:
                cached = self.cache.get(text, self.model)
                if cached is not None:
                    embeddings.append(cached)
                    continue
            
            texts_to_embed.append(text)
            chunk_indices.append(i)
            embeddings.append(None)
        
        # Embed uncached texts
        if texts_to_embed:
            try:
                response = self._call_embedding_api(texts_to_embed)
                
                for idx, embedding_data in enumerate(response.data):
                    embedding = np.array(embedding_data.embedding)
                    
                    if settings.embedding.normalize_embeddings:
                        embedding = self._normalize_embedding(embedding)
                    
                    # Store in results and cache
                    chunk_idx = chunk_indices[idx]
                    embeddings[chunk_idx] = embedding
                    
                    if self.cache:
                        self.cache.set(texts_to_embed[idx], self.model, embedding)
                
            except Exception as e:
                logger.error(f"Batch embedding failed", exception=e, batch_size=len(texts_to_embed))
                # Return None for failed embeddings
                for idx in chunk_indices:
                    if embeddings[idx] is None:
                        embeddings[idx] = self._get_fallback_embedding()
        
        return embeddings
    
    def _prepare_text_for_embedding(self, chunk: Chunk) -> str:
        """Prepare chunk text for embedding.
        
        Args:
            chunk: Chunk to prepare
            
        Returns:
            Prepared text string
        """
        # Combine content with metadata for richer embeddings
        text_parts = [chunk.content_raw]
        
        # Add framework context if available
        if chunk.framework_name:
            text_parts.append(f"Framework: {chunk.framework_name}")
        
        if chunk.framework_component:
            text_parts.append(f"Component: {chunk.framework_component}")
        
        # Add use cases for better retrieval
        if chunk.use_cases:
            text_parts.append(f"Use cases: {', '.join(chunk.use_cases)}")
        
        # Add section context
        if chunk.section:
            text_parts.append(f"Section: {chunk.section}")
        
        return "\n\n".join(text_parts)
    
    def _call_embedding_api(self, texts: List[str]) -> Any:
        """Call OpenAI embedding API with retry logic.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            API response object
        """
        retries = 0
        max_retries = settings.embedding.max_retries
        
        while retries < max_retries:
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                    dimensions=self.dimensions if "text-embedding-3" in self.model else None
                )
                return response
                
            except openai.RateLimitError as e:
                wait_time = min(2 ** retries, 30)
                logger.warning(f"Rate limit hit, waiting {wait_time}s", retry=retries)
                time.sleep(wait_time)
                retries += 1
                
            except openai.APIError as e:
                logger.error(f"OpenAI API error", exception=e, retry=retries)
                retries += 1
                if retries >= max_retries:
                    raise
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Unexpected error in embedding API", exception=e)
                raise
        
        raise Exception(f"Max retries ({max_retries}) exceeded")
    
    def _normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """Normalize embedding vector to unit length.
        
        Args:
            embedding: Embedding vector
            
        Returns:
            Normalized embedding
        """
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding
    
    def _get_fallback_embedding(self) -> np.ndarray:
        """Get a fallback embedding for failed cases.
        
        Returns:
            Zero vector of appropriate dimensions
        """
        return np.zeros(self.dimensions)
    
    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string.
        
        Args:
            query: Query text
            
        Returns:
            Query embedding vector
        """
        try:
            # Check cache first
            if self.cache:
                cached = self.cache.get(query, self.model)
                if cached is not None:
                    logger.debug("Using cached query embedding")
                    return cached
            
            # Generate embedding
            response = self.client.embeddings.create(
                model=self.model,
                input=query,
                dimensions=self.dimensions if "text-embedding-3" in self.model else None
            )
            
            embedding = np.array(response.data[0].embedding)
            
            if settings.embedding.normalize_embeddings:
                embedding = self._normalize_embedding(embedding)
            
            # Cache the result
            if self.cache:
                self.cache.set(query, self.model, embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Query embedding failed", exception=e, query=query)
            return self._get_fallback_embedding()
    
    def compute_similarity(self, query_embedding: np.ndarray, 
                         chunk_embeddings: List[np.ndarray]) -> List[float]:
        """Compute similarity scores between query and chunk embeddings.
        
        Args:
            query_embedding: Query embedding vector
            chunk_embeddings: List of chunk embedding vectors
            
        Returns:
            List of similarity scores
        """
        if settings.storage.distance_metric == "cosine":
            # Cosine similarity
            scores = []
            for chunk_embedding in chunk_embeddings:
                similarity = np.dot(query_embedding, chunk_embedding)
                scores.append(float(similarity))
            return scores
            
        elif settings.storage.distance_metric == "euclidean":
            # Euclidean distance (convert to similarity)
            scores = []
            for chunk_embedding in chunk_embeddings:
                distance = np.linalg.norm(query_embedding - chunk_embedding)
                # Convert distance to similarity (inverse)
                similarity = 1 / (1 + distance)
                scores.append(float(similarity))
            return scores
            
        else:
            raise ValueError(f"Unknown distance metric: {settings.storage.distance_metric}")
    
    def get_embedding_stats(self, embedded_chunks: List[EmbeddedChunk]) -> Dict[str, Any]:
        """Get statistics about the embeddings.
        
        Args:
            embedded_chunks: List of embedded chunks
            
        Returns:
            Dictionary with embedding statistics
        """
        if not embedded_chunks:
            return {}
        
        embeddings = np.array([ec.embedding for ec in embedded_chunks])
        
        return {
            "total_embeddings": len(embeddings),
            "embedding_dim": embeddings.shape[1],
            "mean_norm": float(np.mean(np.linalg.norm(embeddings, axis=1))),
            "std_norm": float(np.std(np.linalg.norm(embeddings, axis=1))),
            "model": self.model,
            "cache_size": len(self.cache.cache) if self.cache else 0
        }


class ParallelEmbeddingPipeline(EmbeddingPipeline):
    """Parallel version of embedding pipeline for faster processing."""
    
    def __init__(self, max_workers: int = 4):
        """Initialize parallel embedding pipeline.
        
        Args:
            max_workers: Maximum number of parallel workers
        """
        super().__init__()
        self.max_workers = max_workers
    
    def embed_chunks(self, chunks: List[Chunk]) -> List[EmbeddedChunk]:
        """Generate embeddings for chunks in parallel.
        
        Args:
            chunks: List of chunks to embed
            
        Returns:
            List of embedded chunks
        """
        logger.info(f"Starting parallel embedding generation",
                   chunks=len(chunks),
                   workers=self.max_workers)
        
        embedded_chunks = []
        
        # Split chunks into batches for parallel processing
        batches = [
            chunks[i:i + self.batch_size]
            for i in range(0, len(chunks), self.batch_size)
        ]
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self._embed_batch_with_retry, batch): batch
                for batch in batches
            }
            
            # Process completed batches
            for future in tqdm(as_completed(future_to_batch), 
                             total=len(batches),
                             desc="Embedding batches"):
                batch = future_to_batch[future]
                try:
                    batch_embeddings = future.result()
                    
                    for chunk, embedding in zip(batch, batch_embeddings):
                        if embedding is not None:
                            embedded_chunk = EmbeddedChunk(
                                chunk=chunk,
                                embedding=embedding,
                                embedding_model=self.model,
                                embedding_dim=self.dimensions
                            )
                            embedded_chunks.append(embedded_chunk)
                            
                except Exception as e:
                    logger.error(f"Batch processing failed", exception=e)
        
        # Flush cache
        if self.cache:
            self.cache.flush()
        
        logger.info(f"Parallel embedding completed",
                   total_chunks=len(chunks),
                   embedded=len(embedded_chunks))
        
        return embedded_chunks
    
    def _embed_batch_with_retry(self, chunks: List[Chunk]) -> List[Optional[np.ndarray]]:
        """Embed a batch with additional retry logic for parallel processing.
        
        Args:
            chunks: Batch of chunks to embed
            
        Returns:
            List of embeddings
        """
        try:
            return self._embed_batch(chunks)
        except Exception as e:
            logger.error(f"Batch embedding failed in parallel processing", exception=e)
            # Return fallback embeddings
            return [self._get_fallback_embedding() for _ in chunks]