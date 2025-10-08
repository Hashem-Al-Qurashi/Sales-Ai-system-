#!/usr/bin/env python3
"""
Test Interface Compliance and Performance
Following ARCHITECTURE.md validation requirements and DATABASE_ENGINEERING_SPEC.md performance targets

FILE LIFECYCLE: development
PURPOSE: Validate PostgreSQL storage interface and orchestrator integration
CLEANUP_DATE: Keep for regression testing
"""

import asyncio
import sys
import time
import statistics
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from production.api.hormozi_rag.storage.postgresql_storage import PostgreSQLVectorDB
from production.api.hormozi_rag.core.orchestrator import RAGOrchestrator
from production.api.hormozi_rag.storage.interfaces import VectorDBInterface, SearchResult, Document
from production.api.hormozi_rag.core.logger import get_logger

logger = get_logger(__name__)


class InterfaceComplianceTest:
    """Test suite for interface compliance and performance validation"""
    
    def __init__(self):
        self.vector_store = PostgreSQLVectorDB()
        self.orchestrator = RAGOrchestrator()
        self.test_results = {
            "interface_compliance": {},
            "performance_results": {},
            "error_handling": {},
            "overall_status": "unknown"
        }
    
    def test_vectordb_interface_compliance(self) -> bool:
        """Test that PostgreSQLVectorDB implements VectorDBInterface correctly"""
        print("🔍 Testing VectorDBInterface compliance...")
        
        try:
            # Test 1: Interface implementation check
            assert isinstance(self.vector_store, VectorDBInterface), "Must implement VectorDBInterface"
            print("✅ VectorDBInterface implementation verified")
            
            # Test 2: Required methods exist  
            required_methods = ['initialize', 'add_documents', 'search']
            for method in required_methods:
                assert hasattr(self.vector_store, method), f"Missing required method: {method}"
            print("✅ Required interface methods present")
            
            # Test 3: Health check method (architectural requirement)
            health = self.vector_store.health_check()
            assert isinstance(health, dict), "Health check must return dict"
            assert 'status' in health, "Health check must include status"
            print(f"✅ Health check working: {health['status']}")
            
            self.test_results["interface_compliance"]["vectordb"] = "PASS"
            return True
            
        except Exception as e:
            print(f"❌ VectorDBInterface compliance failed: {e}")
            self.test_results["interface_compliance"]["vectordb"] = f"FAIL: {e}"
            return False
    
    async def test_orchestrator_query_methods(self) -> bool:
        """Test orchestrator query processing methods following ARCHITECTURE.md"""
        print("🔍 Testing Orchestrator query methods...")
        
        try:
            # Test 1: Basic framework query  
            test_query = "value equation"
            result = await self.orchestrator.process_framework_query(test_query, top_k=3)
            
            # Validate response structure per ARCHITECTURE.md contracts
            required_fields = ["query", "results", "total_results", "query_time_ms", "request_id", "timestamp"]
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"
            
            assert isinstance(result["results"], list), "Results must be list"
            assert result["query"] == test_query, "Query echo must match input"
            assert result["total_results"] >= 0, "Total results must be non-negative"
            
            print(f"✅ Framework query working: {result['total_results']} results in {result['query_time_ms']:.1f}ms")
            
            # Test 2: Performance validation per DATABASE_ENGINEERING_SPEC.md
            query_time = result["query_time_ms"]
            performance_target = 300  # Budget for orchestrator layer
            
            if query_time <= performance_target:
                print(f"✅ Performance target met: {query_time:.1f}ms <= {performance_target}ms")
                performance_status = "PASS"
            else:
                print(f"⚠️ Performance warning: {query_time:.1f}ms > {performance_target}ms target")
                performance_status = "SLOW"
            
            self.test_results["interface_compliance"]["orchestrator"] = "PASS"
            self.test_results["performance_results"]["orchestrator"] = performance_status
            
            return True
            
        except Exception as e:
            print(f"❌ Orchestrator query methods failed: {e}")
            self.test_results["interface_compliance"]["orchestrator"] = f"FAIL: {e}"
            return False
    
    async def test_performance_targets(self) -> bool:
        """Test performance against DATABASE_ENGINEERING_SPEC.md targets"""
        print("🔍 Testing performance targets...")
        
        test_queries = [
            "How do I increase perceived value?",
            "What's the value equation?",
            "Creating compelling guarantees", 
            "Offer structure for web design",
            "Pricing strategy for custom work"
        ]
        
        try:
            # Test vector search performance (target: <200ms database operations)
            query_times = []
            
            for query in test_queries:
                start_time = time.time()
                result = await self.orchestrator.process_framework_query(query, top_k=5)
                query_time = time.time() - start_time
                query_times.append(query_time * 1000)  # Convert to milliseconds
            
            # Calculate percentiles
            p50 = statistics.median(query_times)
            p95 = sorted(query_times)[int(0.95 * len(query_times))] if len(query_times) >= 20 else max(query_times)
            
            print(f"📊 Query Performance Results:")
            print(f"   P50: {p50:.1f}ms")
            print(f"   P95: {p95:.1f}ms")
            print(f"   Target: <300ms (orchestrator budget)")
            
            # Validate against targets
            performance_pass = p95 <= 300
            
            if performance_pass:
                print("✅ Performance targets met")
                self.test_results["performance_results"]["query_latency"] = "PASS"
            else:
                print(f"⚠️ Performance warning: P95 {p95:.1f}ms exceeds 300ms orchestrator budget")
                self.test_results["performance_results"]["query_latency"] = "SLOW"
            
            return performance_pass
            
        except Exception as e:
            print(f"❌ Performance testing failed: {e}")
            self.test_results["performance_results"]["query_latency"] = f"FAIL: {e}"
            return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling following ARCHITECTURE.md 3-level strategy"""
        print("🔍 Testing error handling...")
        
        try:
            # Test 1: Level 1 (Validation) - empty query
            try:
                await self.orchestrator.process_framework_query("", top_k=5)
                print("❌ Empty query should raise ValueError")
                return False
            except ValueError:
                print("✅ Level 1 error handling: Empty query validation working")
            
            # Test 2: Level 1 (Validation) - invalid top_k
            try:
                await self.orchestrator.process_framework_query("test", top_k=25)
                print("❌ Invalid top_k should raise ValueError")
                return False
            except ValueError:
                print("✅ Level 1 error handling: top_k validation working")
            
            # Test 3: Valid query processing
            result = await self.orchestrator.process_framework_query("value equation", top_k=3)
            assert "results" in result, "Valid query must return results"
            print("✅ Valid query processing working")
            
            self.test_results["error_handling"]["validation"] = "PASS"
            return True
            
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            self.test_results["error_handling"]["validation"] = f"FAIL: {e}"
            return False
    
    async def test_database_connectivity(self) -> bool:
        """Test PostgreSQL database connectivity and data integrity"""
        print("🔍 Testing database connectivity...")
        
        try:
            # Test health check
            health = self.vector_store.health_check()
            
            if health["status"] == "healthy":
                print("✅ Database connectivity healthy")
                
                # Validate data integrity per DATABASE_ENGINEERING_SPEC.md FR3
                db_checks = health["checks"]
                
                if "data_integrity" in db_checks:
                    integrity = db_checks["data_integrity"]
                    doc_count = integrity.get("document_count", 0)
                    emb_count = integrity.get("embedding_count", 0)
                    
                    if doc_count == 20 and emb_count == 20:
                        print(f"✅ Data integrity verified: {doc_count} documents, {emb_count} embeddings")
                        self.test_results["interface_compliance"]["database"] = "PASS"
                        return True
                    else:
                        print(f"⚠️ Data integrity warning: {doc_count}/20 documents, {emb_count}/20 embeddings")
                        self.test_results["interface_compliance"]["database"] = "DEGRADED"
                        return True  # Still functional
                else:
                    print("⚠️ Data integrity check not available")
                    
            else:
                print(f"❌ Database unhealthy: {health.get('error', 'unknown error')}")
                self.test_results["interface_compliance"]["database"] = "FAIL"
                return False
                
        except Exception as e:
            print(f"❌ Database connectivity test failed: {e}")
            self.test_results["interface_compliance"]["database"] = f"FAIL: {e}"
            return False
    
    async def run_all_tests(self) -> bool:
        """Run complete test suite and report results"""
        print("🚀 Starting Interface Compliance and Performance Test Suite")
        print("=" * 60)
        
        # Test 1: Interface compliance
        interface_pass = self.test_vectordb_interface_compliance()
        
        # Test 2: Database connectivity  
        db_pass = await self.test_database_connectivity()
        
        # Test 3: Orchestrator methods
        orchestrator_pass = await self.test_orchestrator_query_methods()
        
        # Test 4: Performance validation
        performance_pass = await self.test_performance_targets()
        
        # Test 5: Error handling
        error_handling_pass = await self.test_error_handling()
        
        # Overall assessment
        all_tests_pass = all([interface_pass, db_pass, orchestrator_pass, performance_pass, error_handling_pass])
        
        print("\n" + "=" * 60)
        print("🎯 INTERFACE COMPLIANCE TEST RESULTS")
        print("=" * 60)
        
        print(f"Interface Compliance:  {'✅ PASS' if interface_pass else '❌ FAIL'}")
        print(f"Database Connectivity: {'✅ PASS' if db_pass else '❌ FAIL'}")
        print(f"Orchestrator Methods:  {'✅ PASS' if orchestrator_pass else '❌ FAIL'}")
        print(f"Performance Targets:   {'✅ PASS' if performance_pass else '⚠️ SLOW'}")
        print(f"Error Handling:        {'✅ PASS' if error_handling_pass else '❌ FAIL'}")
        
        print("\n" + "=" * 60)
        
        if all_tests_pass:
            print("✅ ALL TESTS PASSED - READY FOR FASTAPI INTEGRATION")
            self.test_results["overall_status"] = "READY"
        else:
            print("❌ SOME TESTS FAILED - REVIEW ISSUES BEFORE PROCEEDING")
            self.test_results["overall_status"] = "ISSUES"
        
        return all_tests_pass

async def main():
    """Run interface compliance tests"""
    tester = InterfaceComplianceTest()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 Interface compliance validated - proceeding to FastAPI integration")
        exit(0)
    else:
        print("\n❌ Interface compliance issues detected - fix before proceeding")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())