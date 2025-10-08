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

from ..config.settings import settings
from ..core.logger import get_logger
from ..extractors.pdf_extractor import PDFExtractor
from ..core.chunker import HierarchicalChunker
from ..embeddings.embedder import EmbeddingPipeline, ParallelEmbeddingPipeline

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