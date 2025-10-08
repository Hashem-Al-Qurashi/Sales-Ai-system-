"""
Main orchestrator for the Hormozi RAG pipeline.

This module coordinates the entire RAG pipeline from PDF extraction
through embedding generation and storage.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import pickle
import time
import uuid

from ..config.settings import settings
from ..core.logger import get_logger
from ..extractors.pdf_extractor import PDFExtractor
from ..core.chunker import HierarchicalChunker
from ..embeddings.embedder import EmbeddingPipeline, ParallelEmbeddingPipeline
from ..storage.interfaces import SearchResult, Document

logger = get_logger(__name__)


class RAGOrchestrator:
    """Orchestrates the complete RAG pipeline."""
    
    def __init__(self, use_parallel: bool = True):
        """Initialize the orchestrator.
        
        Args:
            use_parallel: Whether to use parallel processing for embeddings
        """
        self.pdf_extractor = PDFExtractor()
        self.chunker = HierarchicalChunker()
        
        if use_parallel:
            self.embedder = ParallelEmbeddingPipeline(max_workers=4)
        else:
            self.embedder = EmbeddingPipeline()
        
        self.processed_data_dir = settings.PROJECT_ROOT / "data" / "processed"
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)
    
    def process_documents(self, pdf_paths: Optional[List[Path]] = None) -> Dict[str, Any]:
        """Process PDF documents through the complete pipeline.
        
        Args:
            pdf_paths: List of PDF paths to process (uses config if None)
            
        Returns:
            Dictionary with processing results
        """
        if pdf_paths is None:
            pdf_paths = settings.pdf.source_files
        
        logger.info("Starting document processing pipeline", documents=len(pdf_paths))
        
        results = {
            "documents_processed": [],
            "total_chunks": 0,
            "total_frameworks": 0,
            "processing_time": None,
            "errors": []
        }
        
        start_time = datetime.now()
        
        all_embedded_chunks = []
        
        for pdf_path in pdf_paths:
            try:
                logger.info(f"Processing document", document=pdf_path.name)
                
                # Step 1: Extract PDF
                extracted_pages = self.pdf_extractor.extract_pdf(pdf_path)
                
                if not extracted_pages:
                    logger.warning(f"No pages extracted", document=pdf_path.name)
                    results["errors"].append(f"No pages extracted from {pdf_path.name}")
                    continue
                
                # Get framework boundaries
                framework_boundaries = self.pdf_extractor.detected_frameworks
                
                # Step 2: Create chunks
                chunks = self.chunker.chunk_documents(
                    extracted_pages,
                    framework_boundaries,
                    pdf_path.name
                )
                
                if not chunks:
                    logger.warning(f"No chunks created", document=pdf_path.name)
                    results["errors"].append(f"No chunks created from {pdf_path.name}")
                    continue
                
                # Step 3: Generate embeddings
                embedded_chunks = self.embedder.embed_chunks(chunks)
                
                all_embedded_chunks.extend(embedded_chunks)
                
                # Record results
                doc_result = {
                    "name": pdf_path.name,
                    "pages": len(extracted_pages),
                    "chunks": len(chunks),
                    "frameworks": len(framework_boundaries),
                    "embedded": len(embedded_chunks)
                }
                
                results["documents_processed"].append(doc_result)
                results["total_chunks"] += len(chunks)
                results["total_frameworks"] += len(framework_boundaries)
                
                logger.info(f"Document processed successfully",
                          document=pdf_path.name,
                          chunks=len(chunks),
                          frameworks=len(framework_boundaries))
                
            except Exception as e:
                logger.error(f"Error processing document", 
                           document=pdf_path.name,
                           exception=e)
                results["errors"].append(f"Error processing {pdf_path.name}: {str(e)}")
        
        # Save processed data
        if all_embedded_chunks:
            self._save_processed_data(all_embedded_chunks)
            
            # Get statistics
            extraction_summary = self.pdf_extractor.get_framework_summary()
            chunking_summary = self.chunker.get_chunking_summary()
            embedding_stats = self.embedder.get_embedding_stats(all_embedded_chunks)
            
            results["extraction_summary"] = extraction_summary
            results["chunking_summary"] = chunking_summary
            results["embedding_stats"] = embedding_stats
        
        end_time = datetime.now()
        results["processing_time"] = str(end_time - start_time)
        
        logger.info("Document processing pipeline completed",
                   documents=len(pdf_paths),
                   total_chunks=results["total_chunks"],
                   total_frameworks=results["total_frameworks"],
                   processing_time=results["processing_time"])
        
        return results
    
    def _save_processed_data(self, embedded_chunks):
        """Save processed data to disk.
        
        Args:
            embedded_chunks: List of embedded chunks to save
        """
        try:
            # Save as pickle for fast loading
            pickle_file = self.processed_data_dir / "embedded_chunks.pkl"
            with open(pickle_file, 'wb') as f:
                pickle.dump(embedded_chunks, f)
            
            # Also save as JSON for inspection
            json_file = self.processed_data_dir / "chunks_metadata.json"
            chunks_data = [
                {
                    **chunk.chunk.to_dict(),
                    "embedding_model": chunk.embedding_model,
                    "embedding_dim": chunk.embedding_dim
                }
                for chunk in embedded_chunks
            ]
            
            with open(json_file, 'w') as f:
                json.dump(chunks_data, f, indent=2, default=str)
            
            # Save framework mappings
            framework_file = self.processed_data_dir / "framework_mappings.json"
            framework_data = {
                "frameworks": {
                    name: [c.chunk.chunk_id for c in embedded_chunks 
                          if c.chunk.framework_name == name]
                    for name in set(c.chunk.framework_name for c in embedded_chunks 
                                  if c.chunk.framework_name)
                },
                "hierarchy": self.chunker.hierarchy_map
            }
            
            with open(framework_file, 'w') as f:
                json.dump(framework_data, f, indent=2)
            
            logger.info("Processed data saved",
                      chunks=len(embedded_chunks),
                      location=str(self.processed_data_dir))
            
        except Exception as e:
            logger.error("Failed to save processed data", exception=e)
            raise
    
    def load_processed_data(self) -> List:
        """Load previously processed data from disk.
        
        Returns:
            List of embedded chunks
        """
        pickle_file = self.processed_data_dir / "embedded_chunks.pkl"
        
        if not pickle_file.exists():
            raise FileNotFoundError(f"No processed data found at {pickle_file}")
        
        try:
            with open(pickle_file, 'rb') as f:
                embedded_chunks = pickle.load(f)
            
            logger.info("Loaded processed data", chunks=len(embedded_chunks))
            return embedded_chunks
            
        except Exception as e:
            logger.error("Failed to load processed data", exception=e)
            raise
    
    def validate_pipeline(self) -> Dict[str, Any]:
        """Validate that the pipeline is working correctly.
        
        Returns:
            Validation results dictionary
        """
        logger.info("Starting pipeline validation")
        
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "errors": [],
            "warnings": []
        }
        
        # Check 1: PDF files exist
        pdf_check = {"status": "pass", "details": []}
        for pdf_path in settings.pdf.source_files:
            if pdf_path.exists():
                pdf_check["details"].append(f"✓ {pdf_path.name} exists")
            else:
                pdf_check["status"] = "fail"
                pdf_check["details"].append(f"✗ {pdf_path.name} not found")
                validation_results["errors"].append(f"PDF not found: {pdf_path}")
        
        validation_results["checks"]["pdf_files"] = pdf_check
        
        # Check 2: OpenAI API key
        api_check = {"status": "pass", "details": []}
        if settings.embedding.api_key:
            api_check["details"].append("✓ OpenAI API key configured")
        else:
            api_check["status"] = "fail"
            api_check["details"].append("✗ OpenAI API key missing")
            validation_results["errors"].append("OpenAI API key not configured")
        
        validation_results["checks"]["api_keys"] = api_check
        
        # Check 3: Test extraction on first page
        if settings.pdf.source_files and settings.pdf.source_files[0].exists():
            extraction_check = {"status": "pass", "details": []}
            try:
                test_extractor = PDFExtractor()
                test_pages = test_extractor.extract_pdf(settings.pdf.source_files[0])
                
                if test_pages:
                    extraction_check["details"].append(f"✓ Extracted {len(test_pages)} pages")
                    
                    # Check for framework detection
                    if test_extractor.detected_frameworks:
                        extraction_check["details"].append(
                            f"✓ Detected {len(test_extractor.detected_frameworks)} frameworks"
                        )
                    else:
                        extraction_check["status"] = "warning"
                        extraction_check["details"].append("⚠ No frameworks detected")
                        validation_results["warnings"].append("No frameworks detected in PDF")
                else:
                    extraction_check["status"] = "fail"
                    extraction_check["details"].append("✗ No pages extracted")
                    validation_results["errors"].append("PDF extraction failed")
                    
            except Exception as e:
                extraction_check["status"] = "fail"
                extraction_check["details"].append(f"✗ Extraction error: {str(e)}")
                validation_results["errors"].append(f"Extraction error: {str(e)}")
            
            validation_results["checks"]["extraction"] = extraction_check
        
        # Check 4: Test embedding generation
        embedding_check = {"status": "pass", "details": []}
        try:
            test_text = "This is a test of the Value Equation framework"
            test_embedding = self.embedder.embed_query(test_text)
            
            if test_embedding is not None and len(test_embedding) > 0:
                embedding_check["details"].append(
                    f"✓ Embedding generation working (dim={len(test_embedding)})"
                )
            else:
                embedding_check["status"] = "fail"
                embedding_check["details"].append("✗ Embedding generation failed")
                validation_results["errors"].append("Embedding generation not working")
                
        except Exception as e:
            embedding_check["status"] = "fail"
            embedding_check["details"].append(f"✗ Embedding error: {str(e)}")
            validation_results["errors"].append(f"Embedding error: {str(e)}")
        
        validation_results["checks"]["embeddings"] = embedding_check
        
        # Overall status
        if validation_results["errors"]:
            validation_results["overall_status"] = "FAIL"
        elif validation_results["warnings"]:
            validation_results["overall_status"] = "WARNING"
        else:
            validation_results["overall_status"] = "PASS"
        
        logger.info("Pipeline validation completed",
                   status=validation_results["overall_status"],
                   errors=len(validation_results["errors"]),
                   warnings=len(validation_results["warnings"]))
        
        return validation_results
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current status of the pipeline.
        
        Returns:
            Status dictionary
        """
        status = {
            "timestamp": datetime.now().isoformat(),
            "processed_data_exists": False,
            "chunks_available": 0,
            "frameworks_available": [],
            "cache_status": {}
        }
        
        # Check for processed data
        pickle_file = self.processed_data_dir / "embedded_chunks.pkl"
        if pickle_file.exists():
            status["processed_data_exists"] = True
            
            try:
                embedded_chunks = self.load_processed_data()
                status["chunks_available"] = len(embedded_chunks)
                
                # Get available frameworks
                frameworks = set(
                    c.chunk.framework_name for c in embedded_chunks 
                    if c.chunk.framework_name
                )
                status["frameworks_available"] = list(frameworks)
                
            except Exception as e:
                logger.warning("Could not load processed data for status", exception=e)
        
        # Check cache status
        if self.embedder.cache:
            status["cache_status"] = {
                "enabled": True,
                "entries": len(self.embedder.cache.cache),
                "location": str(self.embedder.cache.cache_dir)
            }
        else:
            status["cache_status"] = {"enabled": False}
        
        return status
    
    # ============================================================================
    # QUERY PROCESSING METHODS - Added for API Service Layer
    # Following ARCHITECTURE.md Orchestration Layer responsibilities
    # ============================================================================
    
    def __init_query_components(self):
        """Initialize query-specific components following ARCHITECTURE.md singleton pattern"""
        if not hasattr(self, '_query_components_initialized'):
            # Import here to avoid circular dependencies
            from ..storage.postgresql_storage import PostgreSQLVectorDB
            from ..embeddings.openai_embedder import OpenAIEmbedder
            
            self.vector_store = PostgreSQLVectorDB()  # Singleton service per ARCHITECTURE.md
            self.query_embedder = OpenAIEmbedder()    # Singleton service per ARCHITECTURE.md
            
            self._query_components_initialized = True
            
            logger.info("Query processing components initialized", extra={
                "vector_store": "PostgreSQLVectorDB",
                "embedder": "OpenAIEmbedder"
            })
    
    async def process_framework_query(self, query: str, top_k: int = 5, 
                                     filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process framework search query following ARCHITECTURE.md Query Processing Pipeline:
        User Query → Validation → Embedding → Retrieval → Response
        
        Args:
            query: User's business question or framework search query
            top_k: Maximum results to return (ARCHITECTURE.md limit: max 20)
            filters: Optional filters for search (future extension)
            
        Returns:
            Query response following ARCHITECTURE.md response contracts
            
        Performance Target: <300ms total (leaves 200ms for API overhead)
        Error Handling: Following ARCHITECTURE.md 3-level strategy
        """
        # Initialize query components if needed
        self.__init_query_components()
        
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            # Level 1: Input validation (fail fast per ARCHITECTURE.md)
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")
            
            if top_k <= 0 or top_k > 20:  # ARCHITECTURE.md performance boundary
                raise ValueError("top_k must be between 1 and 20 per architecture limits")
            
            logger.info(f"Processing framework query", extra={
                "request_id": request_id,
                "query_length": len(query),
                "top_k": top_k
            })
            
            # Step 1: Generate embedding for query using existing OpenAI integration
            query_embedding = await self._generate_query_embedding(query, request_id)
            
            # Step 2: Execute search through storage interface (single responsibility)
            search_results = self.vector_store.search(query_embedding, top_k, filters)
            
            # Step 3: Format response following ARCHITECTURE.md contracts
            response = {
                "query": query.strip(),
                "results": [self._format_framework_result(result) for result in search_results],
                "total_results": len(search_results),
                "query_time_ms": (time.time() - start_time) * 1000,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
                "performance_metrics": {
                    "embedding_time_ms": None,  # Will be populated by _generate_query_embedding
                    "search_time_ms": None,     # Will be populated by storage layer
                    "formatting_time_ms": None   # Will be calculated
                }
            }
            
            # Performance monitoring per ARCHITECTURE.md monitoring points
            total_time = response["query_time_ms"]
            if total_time > 300:  # Budget for API layer
                logger.warning(f"Query processing time {total_time:.1f}ms exceeds 300ms budget", extra={
                    "request_id": request_id,
                    "query_time_ms": total_time,
                    "performance_target": "300ms"
                })
            
            logger.info(f"Framework query completed successfully", extra={
                "request_id": request_id,
                "results_count": len(search_results),
                "query_time_ms": total_time,
                "performance_status": "within_budget" if total_time <= 300 else "exceeds_budget"
            })
            
            return response
            
        except ValueError as e:
            # Level 1: Validation error handling per ARCHITECTURE.md
            logger.warning(f"Query validation failed: {e}", extra={
                "request_id": request_id,
                "error_level": "validation"
            })
            raise
            
        except Exception as e:
            # Level 2/3: Retrieval/System error handling per ARCHITECTURE.md
            logger.error(f"Query processing failed: {e}", extra={
                "request_id": request_id,
                "error_level": "system"
            }, exc_info=True)
            raise
    
    async def process_hybrid_query(self, query: str, top_k: int = 5, 
                                  vector_weight: float = 0.7) -> Dict[str, Any]:
        """
        Process hybrid search query following DATABASE_ENGINEERING_SPEC.md FR2:
        Combines vector similarity (70%) + text relevance (30%) per specification
        
        Args:
            query: User's search query
            top_k: Maximum results (ARCHITECTURE.md limit: max 20)
            vector_weight: Weight for vector similarity (0.7 default per FR2)
            
        Returns:
            Hybrid search response with combined relevance scoring
            
        Performance Target: <1000ms per DATABASE_ENGINEERING_SPEC.md FR2
        """
        self.__init_query_components()
        
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            # Input validation per ARCHITECTURE.md
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")
            
            if not (0.0 <= vector_weight <= 1.0):
                raise ValueError("vector_weight must be between 0.0 and 1.0")
            
            logger.info(f"Processing hybrid query", extra={
                "request_id": request_id,
                "query_length": len(query),
                "vector_weight": vector_weight,
                "text_weight": 1.0 - vector_weight
            })
            
            # Generate embedding for vector component
            query_embedding = await self._generate_query_embedding(query, request_id)
            
            # Execute hybrid search through storage interface
            search_results = self.vector_store.hybrid_search(
                query_embedding=query_embedding,
                query_text=query.strip(),
                top_k=top_k,
                vector_weight=vector_weight
            )
            
            # Format response following ARCHITECTURE.md contracts
            response = {
                "query": query.strip(),
                "search_type": "hybrid",
                "vector_weight": vector_weight,
                "text_weight": 1.0 - vector_weight,
                "results": [self._format_framework_result(result) for result in search_results],
                "total_results": len(search_results),
                "query_time_ms": (time.time() - start_time) * 1000,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Performance validation per DATABASE_ENGINEERING_SPEC.md FR2
            if response["query_time_ms"] > 1000:
                logger.warning(f"Hybrid query {response['query_time_ms']:.1f}ms exceeds 1000ms target")
            
            return response
            
        except Exception as e:
            logger.error(f"Hybrid query processing failed: {e}", extra={
                "request_id": request_id
            }, exc_info=True)
            raise
    
    async def _generate_query_embedding(self, query: str, request_id: str) -> List[float]:
        """
        Generate embedding for query using existing OpenAI integration
        
        Following ARCHITECTURE.md:
        - Single Responsibility: Embedding generation only
        - Error Handling: Level 2 (external API) with retry logic
        """
        embedding_start = time.time()
        
        try:
            # Use existing embedder component per ARCHITECTURE.md reuse principle
            embedding = await self.query_embedder.embed_text(query)
            
            embedding_time = (time.time() - embedding_start) * 1000
            
            logger.info(f"Query embedding generated", extra={
                "request_id": request_id,
                "embedding_time_ms": embedding_time,
                "embedding_dimensions": len(embedding),
                "query_length": len(query)
            })
            
            return embedding
            
        except Exception as e:
            # Level 2: External API error handling per ARCHITECTURE.md
            logger.error(f"Embedding generation failed: {e}", extra={
                "request_id": request_id,
                "query_length": len(query)
            }, exc_info=True)
            raise
    
    def _format_framework_result(self, result: SearchResult) -> Dict[str, Any]:
        """
        Format SearchResult for API response following ARCHITECTURE.md contracts
        
        Args:
            result: SearchResult object from VectorDBInterface
            
        Returns:
            Formatted result dictionary for API consumption
        """
        return {
            "chunk_id": result.document.metadata.get("chunk_id", "unknown"),
            "framework_name": result.document.metadata.get("framework_name", "unknown"),
            "section": result.document.metadata.get("section", "unknown"),
            "title": result.document.metadata.get("title", "untitled"),
            "content": result.document.text,
            "similarity_score": result.score,
            "rank": result.rank,
            "chunk_type": result.document.metadata.get("chunk_type", "unknown"),
            "metadata": {
                "character_count": result.document.metadata.get("character_count", 0),
                "word_count": result.document.metadata.get("word_count", 0)
            }
        }
    
    async def get_framework_by_name(self, framework_name: str) -> Dict[str, Any]:
        """
        Retrieve specific framework by name following ARCHITECTURE.md contracts
        
        Args:
            framework_name: Name of framework to retrieve
            
        Returns:
            Framework response with all chunks for that framework
        """
        self.__init_query_components()
        
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Input validation
            if not framework_name or not framework_name.strip():
                raise ValueError("Framework name cannot be empty")
            
            logger.info(f"Retrieving framework", extra={
                "request_id": request_id,
                "framework_name": framework_name
            })
            
            # Get framework chunks through storage interface
            search_results = self.vector_store.get_framework_by_name(framework_name.strip())
            
            response = {
                "framework_name": framework_name.strip(),
                "results": [self._format_framework_result(result) for result in search_results],
                "total_results": len(search_results),
                "query_time_ms": (time.time() - start_time) * 1000,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Framework retrieval completed", extra={
                "request_id": request_id,
                "framework_name": framework_name,
                "chunks_found": len(search_results)
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Framework retrieval failed: {e}", extra={
                "request_id": request_id,
                "framework_name": framework_name
            }, exc_info=True)
            raise