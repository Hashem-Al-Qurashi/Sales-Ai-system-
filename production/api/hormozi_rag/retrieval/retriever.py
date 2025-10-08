"""
Hybrid retrieval system with vector and keyword search.

This module implements intelligent retrieval that combines vector similarity,
keyword matching, and framework-aware ranking for optimal results.
"""

import re
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
from rank_bm25 import BM25Okapi
import cohere
from datetime import datetime

from ..config.settings import settings
from ..core.logger import get_logger
from ..core.chunker import Chunk, Priority, ContentType
from ..embeddings.embedder import EmbeddedChunk, EmbeddingPipeline

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    """Represents a single retrieval result."""
    
    chunk: Chunk
    score: float
    vector_score: float = 0.0
    keyword_score: float = 0.0
    rerank_score: float = 0.0
    match_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunk_id": self.chunk.chunk_id,
            "content": self.chunk.content_raw,
            "framework": self.chunk.framework_name,
            "score": self.score,
            "vector_score": self.vector_score,
            "keyword_score": self.keyword_score,
            "rerank_score": self.rerank_score,
            "match_reason": self.match_reason,
            "metadata": {
                "source": self.chunk.source_file,
                "page_range": self.chunk.page_range,
                "priority": self.chunk.priority.value,
                "content_type": self.chunk.content_type.value,
                "use_cases": self.chunk.use_cases
            }
        }


class QueryProcessor:
    """Processes and enhances user queries."""
    
    def __init__(self):
        """Initialize the query processor."""
        self.framework_keywords = {
            "value_equation": [
                "value equation", "dream outcome", "perceived likelihood",
                "time delay", "effort", "sacrifice", "value formula"
            ],
            "offer_creation": [
                "create offer", "offer creation", "offer stack", "structure offer",
                "build offer", "design offer", "irresistible offer"
            ],
            "pricing": [
                "price", "pricing", "charge", "cost", "fee", "investment",
                "pricing psychology", "divergent pricing", "price anchor"
            ],
            "guarantee": [
                "guarantee", "risk reversal", "conditional guarantee",
                "unconditional guarantee", "promise", "assurance"
            ],
            "urgency": [
                "urgency", "scarcity", "limited", "deadline", "expiring",
                "limited time", "limited supply", "FOMO"
            ],
            "bonus": [
                "bonus", "bonuses", "extra value", "stack value", "additional"
            ]
        }
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process and analyze a query.
        
        Args:
            query: User query string
            
        Returns:
            Processed query information
        """
        query_lower = query.lower()
        
        # Detect query intent
        intent = self._detect_intent(query_lower)
        
        # Detect relevant frameworks
        relevant_frameworks = self._detect_frameworks(query_lower)
        
        # Detect use cases
        use_cases = self._detect_use_cases(query_lower)
        
        # Expand query with synonyms
        expanded_query = self._expand_query(query)
        
        # Extract key terms for keyword search
        key_terms = self._extract_key_terms(query_lower)
        
        return {
            "original": query,
            "expanded": expanded_query,
            "intent": intent,
            "frameworks": relevant_frameworks,
            "use_cases": use_cases,
            "key_terms": key_terms
        }
    
    def _detect_intent(self, query: str) -> str:
        """Detect the intent of the query.
        
        Args:
            query: Lowercase query string
            
        Returns:
            Intent type
        """
        if any(word in query for word in ["what is", "define", "explain", "describe"]):
            return "definition"
        elif any(word in query for word in ["how to", "how do i", "steps to", "process"]):
            return "process"
        elif any(word in query for word in ["example", "sample", "instance", "case"]):
            return "example"
        elif any(word in query for word in ["template", "script", "exact", "word for word"]):
            return "template"
        else:
            return "general"
    
    def _detect_frameworks(self, query: str) -> List[str]:
        """Detect which frameworks are relevant to the query.
        
        Args:
            query: Lowercase query string
            
        Returns:
            List of relevant framework names
        """
        relevant = []
        
        for framework, keywords in self.framework_keywords.items():
            if any(keyword in query for keyword in keywords):
                relevant.append(framework)
        
        return relevant
    
    def _detect_use_cases(self, query: str) -> List[str]:
        """Detect use cases from the query.
        
        Args:
            query: Lowercase query string
            
        Returns:
            List of use case identifiers
        """
        use_cases = []
        
        use_case_patterns = {
            "offer_creation": ["create", "build", "design", "structure", "offer"],
            "objection_handling": ["objection", "too expensive", "concern", "pushback"],
            "pricing": ["price", "charge", "cost", "justify", "$"],
            "guarantee_design": ["guarantee", "risk", "promise", "assurance"],
            "urgency_creation": ["urgency", "scarcity", "limited", "deadline"]
        }
        
        for use_case, patterns in use_case_patterns.items():
            if any(pattern in query for pattern in patterns):
                use_cases.append(use_case)
        
        return use_cases if use_cases else ["general"]
    
    def _expand_query(self, query: str) -> str:
        """Expand query with synonyms and related terms.
        
        Args:
            query: Original query
            
        Returns:
            Expanded query string
        """
        expansions = {
            "value equation": "value equation formula dream outcome perceived likelihood time delay effort sacrifice",
            "offer": "offer package deal proposal solution",
            "price": "price cost fee investment charge",
            "guarantee": "guarantee promise assurance warranty risk reversal",
            "bonus": "bonus extra additional value stack incentive",
            "urgency": "urgency scarcity limited deadline FOMO fear missing out"
        }
        
        expanded = query
        for term, expansion in expansions.items():
            if term in query.lower():
                expanded = f"{expanded} {expansion}"
        
        return expanded
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """Extract key terms for keyword search.
        
        Args:
            query: Lowercase query string
            
        Returns:
            List of key terms
        """
        # Remove common stop words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "as", "is", "was", "are",
            "were", "been", "be", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "must",
            "can", "what", "how", "when", "where", "why", "who"
        }
        
        # Split and filter
        words = query.split()
        key_terms = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Add framework-specific terms if detected
        for framework in self._detect_frameworks(query):
            if framework == "value_equation":
                key_terms.extend(["value", "equation", "dream", "outcome"])
            elif framework == "offer_creation":
                key_terms.extend(["offer", "creation", "stack"])
            elif framework == "pricing":
                key_terms.extend(["pricing", "psychology", "divergent"])
        
        return list(set(key_terms))


class HybridRetriever:
    """Implements hybrid retrieval with vector and keyword search."""
    
    def __init__(self, embedded_chunks: List[EmbeddedChunk]):
        """Initialize the retriever with embedded chunks.
        
        Args:
            embedded_chunks: List of chunks with embeddings
        """
        self.embedded_chunks = embedded_chunks
        self.chunks = [ec.chunk for ec in embedded_chunks]
        self.embeddings = np.array([ec.embedding for ec in embedded_chunks])
        
        # Initialize components
        self.query_processor = QueryProcessor()
        self.embedder = EmbeddingPipeline()
        
        # Initialize BM25 for keyword search
        self._initialize_bm25()
        
        # Initialize Cohere reranker if configured
        self.reranker = None
        if settings.retrieval.enable_reranking and settings.retrieval.cohere_api_key:
            try:
                self.reranker = cohere.Client(settings.retrieval.cohere_api_key)
                logger.info("Cohere reranker initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Cohere reranker", exception=e)
    
    def _initialize_bm25(self):
        """Initialize BM25 index for keyword search."""
        # Tokenize documents for BM25
        tokenized_docs = []
        for chunk in self.chunks:
            # Combine content with metadata for richer keyword matching
            text = f"{chunk.content_raw} {chunk.framework_name or ''} {' '.join(chunk.use_cases)}"
            tokens = text.lower().split()
            tokenized_docs.append(tokens)
        
        self.bm25 = BM25Okapi(tokenized_docs)
        logger.info(f"BM25 index initialized", documents=len(tokenized_docs))
    
    def retrieve(self, query: str, top_k: int = None) -> List[RetrievalResult]:
        """Retrieve relevant chunks for a query.
        
        Args:
            query: User query string
            top_k: Number of results to return
            
        Returns:
            List of retrieval results
        """
        if top_k is None:
            top_k = settings.retrieval.reranker_top_k
        
        logger.info(f"Starting retrieval", query=query[:50], top_k=top_k)
        
        # Process query
        processed_query = self.query_processor.process_query(query)
        
        # Get candidates from both vector and keyword search
        candidates = self._get_candidates(processed_query)
        
        # Rerank if available
        if self.reranker and len(candidates) > 0:
            candidates = self._rerank_candidates(query, candidates)
        
        # Apply framework-aware boosting
        candidates = self._apply_framework_boosting(processed_query, candidates)
        
        # Sort by final score and return top k
        candidates.sort(key=lambda x: x.score, reverse=True)
        results = candidates[:top_k]
        
        # Log retrieval metrics
        self._log_retrieval_metrics(query, results)
        
        return results
    
    def _get_candidates(self, processed_query: Dict[str, Any]) -> List[RetrievalResult]:
        """Get candidate chunks using hybrid search.
        
        Args:
            processed_query: Processed query information
            
        Returns:
            List of candidate results
        """
        candidates = []
        seen_chunks = set()
        
        # Vector search
        if settings.retrieval.vector_weight > 0:
            vector_results = self._vector_search(
                processed_query["expanded"],
                top_k=settings.retrieval.top_k
            )
            
            for chunk, score in vector_results:
                if chunk.chunk_id not in seen_chunks:
                    result = RetrievalResult(
                        chunk=chunk,
                        score=score * settings.retrieval.vector_weight,
                        vector_score=score,
                        match_reason="vector_similarity"
                    )
                    candidates.append(result)
                    seen_chunks.add(chunk.chunk_id)
        
        # Keyword search
        if settings.retrieval.keyword_weight > 0:
            keyword_results = self._keyword_search(
                processed_query["key_terms"],
                top_k=settings.retrieval.top_k
            )
            
            for chunk, score in keyword_results:
                if chunk.chunk_id in seen_chunks:
                    # Update existing result
                    for result in candidates:
                        if result.chunk.chunk_id == chunk.chunk_id:
                            result.keyword_score = score
                            result.score += score * settings.retrieval.keyword_weight
                            result.match_reason = "hybrid_match"
                            break
                else:
                    # Add new result
                    result = RetrievalResult(
                        chunk=chunk,
                        score=score * settings.retrieval.keyword_weight,
                        keyword_score=score,
                        match_reason="keyword_match"
                    )
                    candidates.append(result)
                    seen_chunks.add(chunk.chunk_id)
        
        # Framework-specific retrieval
        if processed_query["frameworks"]:
            framework_results = self._framework_search(
                processed_query["frameworks"],
                top_k=5
            )
            
            for chunk, score in framework_results:
                if chunk.chunk_id in seen_chunks:
                    # Boost existing result
                    for result in candidates:
                        if result.chunk.chunk_id == chunk.chunk_id:
                            result.score *= 1.5  # Framework boost
                            result.match_reason = f"{result.match_reason}+framework"
                            break
                else:
                    # Add framework result
                    result = RetrievalResult(
                        chunk=chunk,
                        score=score,
                        match_reason="framework_match"
                    )
                    candidates.append(result)
                    seen_chunks.add(chunk.chunk_id)
        
        return candidates
    
    def _vector_search(self, query: str, top_k: int) -> List[Tuple[Chunk, float]]:
        """Perform vector similarity search.
        
        Args:
            query: Query string
            top_k: Number of results
            
        Returns:
            List of (chunk, score) tuples
        """
        # Generate query embedding
        query_embedding = self.embedder.embed_query(query)
        
        # Compute similarities
        similarities = self.embedder.compute_similarity(query_embedding, self.embeddings)
        
        # Get top k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] >= settings.retrieval.similarity_threshold:
                results.append((self.chunks[idx], similarities[idx]))
        
        return results
    
    def _keyword_search(self, key_terms: List[str], top_k: int) -> List[Tuple[Chunk, float]]:
        """Perform keyword search using BM25.
        
        Args:
            key_terms: List of key terms
            top_k: Number of results
            
        Returns:
            List of (chunk, score) tuples
        """
        # Get BM25 scores
        scores = self.bm25.get_scores(key_terms)
        
        # Normalize scores to 0-1 range
        max_score = max(scores) if max(scores) > 0 else 1
        normalized_scores = scores / max_score
        
        # Get top k indices
        top_indices = np.argsort(normalized_scores)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if normalized_scores[idx] > 0.1:  # Minimum keyword relevance
                results.append((self.chunks[idx], float(normalized_scores[idx])))
        
        return results
    
    def _framework_search(self, frameworks: List[str], top_k: int) -> List[Tuple[Chunk, float]]:
        """Search for specific frameworks.
        
        Args:
            frameworks: List of framework identifiers
            top_k: Number of results per framework
            
        Returns:
            List of (chunk, score) tuples
        """
        results = []
        
        for chunk in self.chunks:
            if not chunk.framework_name:
                continue
            
            # Check if chunk matches any requested framework
            for framework in frameworks:
                if framework.lower() in chunk.framework_name.lower():
                    # Higher score for complete frameworks
                    score = 1.0 if chunk.is_complete_framework else 0.8
                    
                    # Boost GOLD priority frameworks
                    if chunk.priority == Priority.GOLD:
                        score *= 1.2
                    
                    results.append((chunk, score))
                    break
        
        # Sort by score and return top k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def _rerank_candidates(self, query: str, 
                          candidates: List[RetrievalResult]) -> List[RetrievalResult]:
        """Rerank candidates using Cohere.
        
        Args:
            query: Original query
            candidates: List of candidates to rerank
            
        Returns:
            Reranked list of candidates
        """
        if not self.reranker or not candidates:
            return candidates
        
        try:
            # Prepare documents for reranking
            documents = [result.chunk.content_raw for result in candidates]
            
            # Call Cohere rerank API
            response = self.reranker.rerank(
                query=query,
                documents=documents,
                top_n=min(len(documents), settings.retrieval.reranker_top_k * 2),
                model="rerank-english-v2.0"
            )
            
            # Update scores based on reranking
            reranked = []
            for result in response:
                original_result = candidates[result.index]
                original_result.rerank_score = result.relevance_score
                
                # Combine scores
                original_result.score = (
                    original_result.score * 0.5 +
                    result.relevance_score * 0.5
                )
                
                reranked.append(original_result)
            
            # Add any candidates that weren't reranked (shouldn't happen)
            reranked_indices = {r.index for r in response}
            for i, candidate in enumerate(candidates):
                if i not in reranked_indices:
                    reranked.append(candidate)
            
            logger.debug(f"Reranked candidates", 
                       original=len(candidates),
                       reranked=len(reranked))
            
            return reranked
            
        except Exception as e:
            logger.warning(f"Reranking failed, using original order", exception=e)
            return candidates
    
    def _apply_framework_boosting(self, processed_query: Dict[str, Any],
                                 candidates: List[RetrievalResult]) -> List[RetrievalResult]:
        """Apply framework-aware score boosting.
        
        Args:
            processed_query: Processed query information
            candidates: List of candidates
            
        Returns:
            Candidates with boosted scores
        """
        for result in candidates:
            chunk = result.chunk
            
            # Boost based on query intent matching
            if processed_query["intent"] == "definition" and chunk.content_type == ContentType.DEFINITION:
                result.score *= 1.3
            elif processed_query["intent"] == "process" and chunk.content_type == ContentType.PROCESS:
                result.score *= 1.3
            elif processed_query["intent"] == "example" and chunk.content_type == ContentType.EXAMPLE:
                result.score *= 1.2
            elif processed_query["intent"] == "template" and chunk.content_type == ContentType.TEMPLATE:
                result.score *= 1.4
            
            # Boost based on use case matching
            matching_use_cases = set(chunk.use_cases) & set(processed_query["use_cases"])
            if matching_use_cases:
                result.score *= (1 + 0.1 * len(matching_use_cases))
            
            # Boost based on priority
            if chunk.priority == Priority.GOLD:
                result.score *= 1.2
            elif chunk.priority == Priority.SILVER:
                result.score *= 1.1
            
            # Boost complete frameworks
            if chunk.is_complete_framework and processed_query["frameworks"]:
                result.score *= 1.3
            
            # Update usage count (for learning)
            chunk.usage_count += 1
        
        return candidates
    
    def _log_retrieval_metrics(self, query: str, results: List[RetrievalResult]):
        """Log metrics for retrieval operation.
        
        Args:
            query: Original query
            results: Retrieved results
        """
        if not results:
            logger.warning("No results retrieved", query=query)
            return
        
        scores = [r.score for r in results]
        frameworks = [r.chunk.framework_name for r in results if r.chunk.framework_name]
        
        logger.log_retrieval(
            query=query,
            results_count=len(results),
            relevance_scores=scores,
            avg_score=sum(scores) / len(scores),
            max_score=max(scores),
            min_score=min(scores),
            frameworks_retrieved=list(set(frameworks)),
            match_reasons=[r.match_reason for r in results[:3]]
        )
    
    def get_framework(self, framework_name: str) -> List[RetrievalResult]:
        """Retrieve all chunks for a specific framework.
        
        Args:
            framework_name: Name of the framework
            
        Returns:
            List of chunks belonging to the framework
        """
        results = []
        
        for chunk in self.chunks:
            if chunk.framework_name and framework_name.lower() in chunk.framework_name.lower():
                result = RetrievalResult(
                    chunk=chunk,
                    score=1.0 if chunk.is_complete_framework else 0.8,
                    match_reason="framework_lookup"
                )
                results.append(result)
        
        # Sort by importance
        results.sort(key=lambda x: (
            x.chunk.is_complete_framework,
            x.chunk.importance_score
        ), reverse=True)
        
        return results
    
    def search_by_use_case(self, use_case: str, top_k: int = 10) -> List[RetrievalResult]:
        """Search chunks by use case.
        
        Args:
            use_case: Use case identifier
            top_k: Number of results
            
        Returns:
            List of relevant chunks
        """
        results = []
        
        for chunk in self.chunks:
            if use_case in chunk.use_cases:
                # Score based on priority and content type
                score = chunk.importance_score / 10.0
                
                result = RetrievalResult(
                    chunk=chunk,
                    score=score,
                    match_reason=f"use_case:{use_case}"
                )
                results.append(result)
        
        # Sort by score and return top k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]