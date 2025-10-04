"""
Test suite for validating framework queries work perfectly.

This module contains the critical queries that MUST work for the Friday demo
and validates that the core frameworks are accessible and complete.
"""

import unittest
from typing import List, Dict, Any
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hormozi_rag.core.orchestrator import RAGOrchestrator
from hormozi_rag.retrieval.retriever import HybridRetriever, RetrievalResult
from hormozi_rag.config.settings import settings
from hormozi_rag.core.logger import get_logger

logger = get_logger(__name__)


class FrameworkQueryTestCase(unittest.TestCase):
    """Base class for framework query tests."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.orchestrator = RAGOrchestrator()
        
        # Try to load processed data
        try:
            cls.embedded_chunks = cls.orchestrator.load_processed_data()
            cls.retriever = HybridRetriever(cls.embedded_chunks)
            cls.data_available = True
            logger.info("Test data loaded successfully")
        except FileNotFoundError:
            cls.data_available = False
            logger.warning("No processed data found - tests will be skipped")
    
    def setUp(self):
        """Set up for each test."""
        if not self.data_available:
            self.skipTest("No processed data available")
    
    def assert_framework_complete(self, results: List[RetrievalResult], 
                                 framework_name: str,
                                 expected_components: List[str] = None):
        """Assert that a framework is returned completely.
        
        Args:
            results: Retrieval results
            framework_name: Expected framework name
            expected_components: Expected components in the framework
        """
        # Find framework results
        framework_results = [
            r for r in results 
            if r.chunk.framework_name and framework_name.lower() in r.chunk.framework_name.lower()
        ]
        
        self.assertGreater(
            len(framework_results), 0,
            f"No results found for framework: {framework_name}"
        )
        
        # Check for complete framework
        complete_frameworks = [
            r for r in framework_results 
            if r.chunk.is_complete_framework
        ]
        
        self.assertGreater(
            len(complete_frameworks), 0,
            f"No complete framework found for: {framework_name}"
        )
        
        # If components specified, check they're present
        if expected_components:
            complete_framework = complete_frameworks[0]
            content = complete_framework.chunk.content_raw.lower()
            
            for component in expected_components:
                self.assertIn(
                    component.lower(), content,
                    f"Component '{component}' not found in {framework_name}"
                )
    
    def assert_high_relevance(self, results: List[RetrievalResult], 
                             min_score: float = 0.7):
        """Assert that top results have high relevance scores.
        
        Args:
            results: Retrieval results
            min_score: Minimum acceptable score
        """
        self.assertGreater(len(results), 0, "No results returned")
        
        top_result = results[0]
        self.assertGreaterEqual(
            top_result.score, min_score,
            f"Top result score {top_result.score} below minimum {min_score}"
        )
    
    def assert_source_citation(self, results: List[RetrievalResult]):
        """Assert that results include proper source citations.
        
        Args:
            results: Retrieval results
        """
        for result in results[:3]:  # Check top 3 results
            chunk = result.chunk
            
            self.assertIsNotNone(chunk.source_file, "Missing source file")
            self.assertIsNotNone(chunk.page_range, "Missing page range")
            
            # Check context header is present
            self.assertIn("Source:", chunk.content, "Missing source in context header")


class CoreFrameworkTests(FrameworkQueryTestCase):
    """Tests for core framework queries that MUST work for demo."""
    
    def test_value_equation_query(self):
        """Test: What's the value equation?"""
        query = "What's the value equation?"
        results = self.retriever.retrieve(query, top_k=5)
        
        # Must return complete Value Equation framework
        self.assert_framework_complete(
            results, 
            "Value Equation",
            expected_components=[
                "dream outcome",
                "perceived likelihood", 
                "time delay",
                "effort"
            ]
        )
        
        # Must have high relevance
        self.assert_high_relevance(results, min_score=0.8)
        
        # Must include proper citations
        self.assert_source_citation(results)
        
        # Must include the formula
        top_result = results[0]
        content = top_result.chunk.content_raw.lower()
        self.assertTrue(
            "value =" in content or "value equation" in content,
            "Value equation formula not found"
        )
        
        logger.info("✅ Value equation query test passed")
    
    def test_offer_creation_query(self):
        """Test: How do I create an irresistible offer for web design?"""
        query = "How do I create an irresistible offer for web design?"
        results = self.retriever.retrieve(query, top_k=5)
        
        # Must return Offer Creation Stack
        self.assert_framework_complete(
            results,
            "Offer Creation Stack",
            expected_components=[
                "identify dream outcome",
                "problems", 
                "solutions",
                "delivery"
            ]
        )
        
        # Must have high relevance for process query
        self.assert_high_relevance(results, min_score=0.7)
        
        # Should prefer process content type
        process_results = [
            r for r in results 
            if r.chunk.content_type.value == "process"
        ]
        self.assertGreater(
            len(process_results), 0,
            "No process-type content found for offer creation"
        )
        
        logger.info("✅ Offer creation query test passed")
    
    def test_guarantee_types_query(self):
        """Test: Give me examples of guarantees for service businesses"""
        query = "Give me examples of guarantees for service businesses"
        results = self.retriever.retrieve(query, top_k=5)
        
        # Must return Guarantee Framework
        self.assert_framework_complete(
            results,
            "Guarantee Framework",
            expected_components=[
                "unconditional",
                "conditional", 
                "guarantee"
            ]
        )
        
        # Must have high relevance
        self.assert_high_relevance(results, min_score=0.7)
        
        # Should include multiple guarantee types
        top_result = results[0]
        content = top_result.chunk.content_raw.lower()
        
        guarantee_types = ["unconditional", "conditional", "anti-guarantee", "implied"]
        found_types = [gt for gt in guarantee_types if gt in content]
        
        self.assertGreaterEqual(
            len(found_types), 2,
            f"Expected multiple guarantee types, found: {found_types}"
        )
        
        logger.info("✅ Guarantee types query test passed")
    
    def test_pricing_justification_query(self):
        """Test: How do I justify charging $10k instead of $5k?"""
        query = "How do I justify charging $10k instead of $5k?"
        results = self.retriever.retrieve(query, top_k=5)
        
        # Must include both Value Equation and Pricing Psychology
        framework_names = [
            r.chunk.framework_name for r in results 
            if r.chunk.framework_name
        ]
        
        self.assertTrue(
            any("value equation" in name.lower() for name in framework_names),
            "Value Equation not found in pricing query results"
        )
        
        self.assertTrue(
            any("pricing" in name.lower() for name in framework_names),
            "Pricing Psychology not found in pricing query results"
        )
        
        # Must have high relevance
        self.assert_high_relevance(results, min_score=0.7)
        
        # Should include pricing tactics
        combined_content = " ".join([r.chunk.content_raw.lower() for r in results[:3]])
        pricing_concepts = ["value", "anchor", "divergent", "premium"]
        
        found_concepts = [pc for pc in pricing_concepts if pc in combined_content]
        self.assertGreaterEqual(
            len(found_concepts), 2,
            f"Expected pricing concepts, found: {found_concepts}"
        )
        
        logger.info("✅ Pricing justification query test passed")


class FrameworkCompletenessTests(FrameworkQueryTestCase):
    """Tests to ensure frameworks are never split across chunks."""
    
    def test_value_equation_completeness(self):
        """Test that Value Equation is never split."""
        framework_results = self.retriever.get_framework("Value Equation")
        
        complete_frameworks = [
            r for r in framework_results 
            if r.chunk.is_complete_framework
        ]
        
        self.assertGreater(
            len(complete_frameworks), 0,
            "No complete Value Equation framework found"
        )
        
        # Check that complete framework has all components
        complete_framework = complete_frameworks[0]
        content = complete_framework.chunk.content_raw.lower()
        
        required_components = [
            "dream outcome",
            "perceived likelihood",
            "time delay", 
            "effort",
            "sacrifice"
        ]
        
        for component in required_components:
            self.assertIn(
                component, content,
                f"Missing component '{component}' in complete Value Equation"
            )
        
        logger.info("✅ Value Equation completeness test passed")
    
    def test_offer_stack_completeness(self):
        """Test that Offer Creation Stack is complete."""
        framework_results = self.retriever.get_framework("Offer Creation Stack")
        
        if not framework_results:
            self.skipTest("No Offer Creation Stack framework found")
        
        complete_frameworks = [
            r for r in framework_results 
            if r.chunk.is_complete_framework
        ]
        
        if complete_frameworks:
            complete_framework = complete_frameworks[0]
            content = complete_framework.chunk.content_raw.lower()
            
            # Check for step sequence
            steps_found = 0
            for i in range(1, 6):  # Steps 1-5
                if f"step {i}" in content or f"{i}." in content:
                    steps_found += 1
            
            self.assertGreaterEqual(
                steps_found, 3,
                f"Insufficient steps found in Offer Stack: {steps_found}"
            )
        
        logger.info("✅ Offer Stack completeness test passed")


class QueryIntentTests(FrameworkQueryTestCase):
    """Tests for different types of query intents."""
    
    def test_definition_queries(self):
        """Test definition-type queries."""
        queries = [
            "What is the value equation?",
            "Define dream outcome",
            "Explain perceived likelihood"
        ]
        
        for query in queries:
            results = self.retriever.retrieve(query, top_k=3)
            
            # Should prefer definition-type content
            definition_results = [
                r for r in results 
                if r.chunk.content_type.value == "definition"
            ]
            
            if definition_results:
                self.assertGreaterEqual(
                    definition_results[0].score,
                    results[0].score * 0.8,  # Should be among top results
                    f"Definition content not prioritized for: {query}"
                )
        
        logger.info("✅ Definition queries test passed")
    
    def test_process_queries(self):
        """Test process/how-to queries."""
        queries = [
            "How to create an offer",
            "Steps to build value",
            "Process for offer creation"
        ]
        
        for query in queries:
            results = self.retriever.retrieve(query, top_k=3)
            
            # Should prefer process-type content
            process_results = [
                r for r in results 
                if r.chunk.content_type.value == "process"
            ]
            
            self.assertGreater(
                len(process_results), 0,
                f"No process content found for: {query}"
            )
        
        logger.info("✅ Process queries test passed")


class PerformanceTests(FrameworkQueryTestCase):
    """Tests for retrieval performance and quality."""
    
    def test_response_time(self):
        """Test that queries complete within acceptable time."""
        import time
        
        query = "What is the value equation?"
        
        start_time = time.time()
        results = self.retriever.retrieve(query, top_k=5)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        self.assertLess(
            response_time, 3.0,  # Should complete within 3 seconds
            f"Query took too long: {response_time:.2f}s"
        )
        
        self.assertGreater(
            len(results), 0,
            "No results returned in performance test"
        )
        
        logger.info(f"✅ Response time test passed: {response_time:.2f}s")
    
    def test_relevance_scores(self):
        """Test that relevance scores are reasonable."""
        queries = [
            "value equation",
            "offer creation",
            "pricing psychology",
            "guarantee framework"
        ]
        
        for query in queries:
            results = self.retriever.retrieve(query, top_k=3)
            
            if results:
                # Top result should have high score
                self.assertGreaterEqual(
                    results[0].score, 0.5,
                    f"Top result score too low for '{query}': {results[0].score}"
                )
                
                # Scores should be in descending order
                for i in range(1, len(results)):
                    self.assertGreaterEqual(
                        results[i-1].score, results[i].score,
                        f"Results not sorted by relevance for: {query}"
                    )
        
        logger.info("✅ Relevance scores test passed")


def run_validation_suite():
    """Run the complete validation suite and return results."""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add core framework tests (critical for demo)
    suite.addTest(unittest.makeSuite(CoreFrameworkTests))
    
    # Add framework completeness tests
    suite.addTest(unittest.makeSuite(FrameworkCompletenessTests))
    
    # Add query intent tests
    suite.addTest(unittest.makeSuite(QueryIntentTests))
    
    # Add performance tests
    suite.addTest(unittest.makeSuite(PerformanceTests))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        buffer=True
    )
    
    result = runner.run(suite)
    
    # Return summary
    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "success": result.wasSuccessful(),
        "failure_details": [str(f[1]) for f in result.failures],
        "error_details": [str(e[1]) for e in result.errors]
    }


if __name__ == "__main__":
    # Run validation when called directly
    results = run_validation_suite()
    
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"Tests run: {results['tests_run']}")
    print(f"Failures: {results['failures']}")
    print(f"Errors: {results['errors']}")
    print(f"Success: {'✅ PASS' if results['success'] else '❌ FAIL'}")
    
    if not results['success']:
        print("\nFAILURES:")
        for failure in results['failure_details']:
            print(f"  - {failure}")
        
        print("\nERRORS:")
        for error in results['error_details']:
            print(f"  - {error}")
    
    print("="*60 + "\n")
    
    sys.exit(0 if results['success'] else 1)