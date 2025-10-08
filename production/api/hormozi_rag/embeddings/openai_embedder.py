"""
Simple OpenAI embedder for framework ingestion.

Provides basic embedding functionality using OpenAI API
without complex dependencies on the existing chunker system.
"""

import asyncio
import time
from typing import List, Optional
import numpy as np
from openai import OpenAI

from ..config.settings import settings
from ..core.logger import get_logger

logger = get_logger(__name__)


class OpenAIEmbedder:
    """
    Simple OpenAI embedder for framework chunks.
    
    Follows ARCHITECTURE.md single responsibility principle:
    - Generate embeddings using OpenAI API
    - Handle API errors with retry logic
    - Return numpy arrays for storage
    """
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS
        
    async def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        try:
            # Call OpenAI API in thread to avoid blocking
            response = await asyncio.to_thread(
                self._call_openai_api, 
                text
            )
            
            # Extract embedding
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to embed text", exception=e, text_length=len(text))
            # Return zero vector as fallback
            return np.zeros(self.dimensions, dtype=np.float32)
    
    def _call_openai_api(self, text: str):
        """
        Call OpenAI API with retry logic.
        
        Args:
            text: Text to embed
            
        Returns:
            OpenAI API response
        """
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text,
                    dimensions=self.dimensions if "text-embedding-3" in self.model else None
                )
                return response
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                
                delay = base_delay * (2 ** attempt)
                logger.warning(f"API call failed, retrying in {delay}s", attempt=attempt + 1)
                time.sleep(delay)
    
    def health_check(self) -> bool:
        """
        Check if embedder is working.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Test with a simple phrase
            test_embedding = asyncio.run(self.embed_text("test"))
            return test_embedding.shape[0] == self.dimensions
        except Exception:
            return False