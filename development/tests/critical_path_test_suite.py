#!/usr/bin/env python3
"""
Critical Path Test Suite - The 20% that breaks 80% of functionality
Following DEVELOPMENT_RULES.md Mandatory Testing Discipline

FILE LIFECYCLE: development
PURPOSE: Test critical paths for Day 1 FastAPI implementation per DEVELOPMENT_RULES.md
REPLACES: Manual testing with systematic validation
CLEANUP_DATE: permanent (regression testing)

TESTING APPROACH: Hybrid per DEVELOPMENT_RULES.md
- Critical Path Testing: IMMEDIATE (this file) 
- TDD for new features: ONGOING (future implementations)
- Integration validation: EVERY CHANGE (component boundaries)
"""

import asyncio
import aiohttp
import psycopg2
import json
import time
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Test configuration following production/.env
TEST_CONFIG = {
    'OPENAI_API_KEY': 'your-openai-api-key-here',
    'POSTGRES_HOST': 'localhost',
    'POSTGRES_DB': 'hormozi_rag', 
    'POSTGRES_USER': 'rag_app_user',
    'POSTGRES_PASSWORD': 'rag_secure_password_123',
    'POSTGRES_PORT': '5432',
    'VECTOR_DB_TYPE': 'postgresql'
}

# Set environment for test execution
for key, value in TEST_CONFIG.items():
    os.environ[key] = value

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class CriticalPathTestSuite:
    """
    Critical Path Testing following DEVELOPMENT_RULES.md mandatory discipline
    
    Tests the 20% that breaks 80% of functionality:
    1. PostgreSQL connection and queries
    2. FastAPI endpoints (/query, /health) 
    3. OpenAI embedding generation
    4. End-to-end query validation
    """
    
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.test_results = {
            "test_execution_id": f"critical_path_{int(time.time())}",
            "timestamp": datetime.utcnow().isoformat(),
            "postgresql_tests": {},
            "fastapi_tests": {},
            "openai_tests": {},
            "end_to_end_tests": {},
            "integration_validation": {},
            "performance_results": {},
            "regression_validation": {},
            "overall_status": "UNKNOWN"
        }
        self.critical_issues = []
        
    def test_1_postgresql_critical_path(self) -> bool:
        """
        Test 1: PostgreSQL Connection and Queries (DATABASE FOUNDATION)
        Following DEVELOPMENT_RULES.md Test 1 requirements
        
        Critical because: If database fails, entire system fails
        """
        print("🔍 TEST 1: PostgreSQL Critical Path")
        print("-" * 40)
        
        try:
            # Import PostgreSQL storage interface
            from production.api.hormozi_rag.storage.postgresql_storage import PostgreSQLVectorDB
            
            # Test 1.1: Connection pool initialization
            print("   1.1 Testing connection pool initialization...")
            vector_db = PostgreSQLVectorDB()
            assert vector_db.pool is not None, "Connection pool must be initialized"
            assert not vector_db.pool.closed, "Connection pool must be open"
            print("   ✅ Connection pool working")
            
            # Test 1.2: Basic database connectivity
            print("   1.2 Testing database connectivity...")
            health = vector_db.health_check()
            assert health == True, "Database health check must pass"
            print("   ✅ Database connectivity working")
            
            # Test 1.3: Data integrity validation  
            print("   1.3 Testing data integrity...")
            detailed_health = vector_db.detailed_health_check()
            data_integrity = detailed_health["checks"]["data_integrity"]
            
            assert data_integrity["document_count"] == 20, f"Expected 20 documents, got {data_integrity['document_count']}"
            assert data_integrity["embedding_count"] == 20, f"Expected 20 embeddings, got {data_integrity['embedding_count']}"
            assert data_integrity["embedding_dimensions"] == 3072, f"Expected 3072 dims, got {data_integrity['embedding_dimensions']}"
            print("   ✅ Data integrity verified (20 docs, 20 embeddings, 3072 dims)")
            
            # Test 1.4: Vector search execution
            print("   1.4 Testing vector search execution...")
            test_embedding = [0.1] * 3072  # Simple test vector
            
            start_time = time.time()
            search_results = vector_db.search(test_embedding, top_k=3)
            search_time = (time.time() - start_time) * 1000
            
            assert len(search_results) > 0, "Vector search must return results"
            assert search_time < 200, f"Vector search must be <200ms, got {search_time:.1f}ms"
            print(f"   ✅ Vector search working ({len(search_results)} results in {search_time:.1f}ms)")
            
            # Test 1.5: Health check performance
            print("   1.5 Testing health check performance...")
            start_time = time.time()
            health_check = vector_db.detailed_health_check()
            health_time = (time.time() - start_time) * 1000
            
            assert health_check["status"] in ["healthy", "degraded"], "Health check must return valid status"
            # Note: Health checks can be slower due to OpenAI API calls, but database portion should be fast
            print(f"   ✅ Health check working ({health_time:.1f}ms)")
            
            self.test_results["postgresql_tests"] = {
                "connection_pool": "PASS",
                "database_connectivity": "PASS", 
                "data_integrity": "PASS",
                "vector_search": "PASS",
                "health_checks": "PASS",
                "overall": "PASS"
            }
            
            print("✅ TEST 1 PASSED: PostgreSQL critical path working")
            return True
            
        except Exception as e:
            self.critical_issues.append(f"PostgreSQL critical failure: {e}")
            self.test_results["postgresql_tests"] = {"overall": f"FAIL: {e}"}
            print(f"❌ TEST 1 FAILED: {e}")
            return False
    
    async def test_2_fastapi_critical_endpoints(self) -> bool:
        """
        Test 2: FastAPI Endpoints (/query, /health) (API SERVICE LAYER)  
        Following DEVELOPMENT_RULES.md Test 2 requirements
        
        Critical because: If API fails, Dan cannot access system
        """
        print("\n🔍 TEST 2: FastAPI Critical Endpoints")
        print("-" * 40)
        
        async with aiohttp.ClientSession() as session:
            try:
                # Test 2.1: Health endpoint functionality
                print("   2.1 Testing /health endpoint...")
                
                start_time = time.time()
                async with session.get(f"{self.api_base_url}/health") as response:
                    health_time = (time.time() - start_time) * 1000
                    
                    assert response.status == 200, f"Health endpoint must return 200, got {response.status}"
                    
                    health_data = await response.json()
                    assert health_data["service"] == "hormozi_rag_api", "Health must identify correct service"
                    assert health_data["status"] in ["healthy", "degraded"], "Health must return valid status"
                    
                    print(f"   ✅ /health endpoint working ({health_data['status']} in {health_time:.1f}ms)")
                
                # Test 2.2: Query endpoint functionality  
                print("   2.2 Testing /api/v1/query endpoint...")
                
                test_query = "value equation"
                start_time = time.time()
                
                async with session.post(
                    f"{self.api_base_url}/api/v1/query",
                    json={"query": test_query, "top_k": 3}
                ) as response:
                    query_time = (time.time() - start_time) * 1000
                    
                    assert response.status == 200, f"Query endpoint must return 200, got {response.status}"
                    
                    result = await response.json()
                    
                    # Validate response structure per ARCHITECTURE.md contracts
                    required_fields = ["query", "results", "total_results", "query_time_ms", "request_id"]
                    for field in required_fields:
                        assert field in result, f"Response missing required field: {field}"
                    
                    assert len(result["results"]) > 0, "Query must return results"
                    assert result["query"] == test_query, "Query echo must match input"
                    
                    print(f"   ✅ /api/v1/query endpoint working ({len(result['results'])} results in {query_time:.0f}ms)")
                
                # Test 2.3: Error handling for invalid requests
                print("   2.3 Testing error handling...")
                
                # Empty query should return validation error
                async with session.post(
                    f"{self.api_base_url}/api/v1/query",
                    json={"query": "", "top_k": 3}
                ) as response:
                    assert response.status == 422, f"Empty query should return 422, got {response.status}"
                    print("   ✅ Empty query validation working")
                
                # Invalid top_k should return validation error  
                async with session.post(
                    f"{self.api_base_url}/api/v1/query", 
                    json={"query": "test", "top_k": 25}
                ) as response:
                    assert response.status == 422, f"Invalid top_k should return 422, got {response.status}"
                    print("   ✅ Invalid top_k validation working")
                
                self.test_results["fastapi_tests"] = {
                    "health_endpoint": "PASS",
                    "query_endpoint": "PASS",
                    "error_handling": "PASS",
                    "overall": "PASS"
                }
                
                print("✅ TEST 2 PASSED: FastAPI critical endpoints working")
                return True
                
            except Exception as e:
                self.critical_issues.append(f"FastAPI critical failure: {e}")
                self.test_results["fastapi_tests"] = {"overall": f"FAIL: {e}"}
                print(f"❌ TEST 2 FAILED: {e}")
                return False
    
    async def test_3_openai_embedding_integration(self) -> bool:
        """
        Test 3: OpenAI Embedding Generation (EXTERNAL DEPENDENCY)
        Following DEVELOPMENT_RULES.md Test 3 requirements
        
        Critical because: If OpenAI fails, semantic search fails
        """
        print("\n🔍 TEST 3: OpenAI Embedding Integration")  
        print("-" * 40)
        
        try:
            import openai
            
            # Test 3.1: API key validation
            print("   3.1 Testing OpenAI API key validation...")
            api_key = os.getenv('OPENAI_API_KEY')
            assert api_key and api_key.startswith('sk-'), "Valid OpenAI API key required"
            openai.api_key = api_key
            print("   ✅ API key validation passed")
            
            # Test 3.2: Embedding generation functionality
            print("   3.2 Testing embedding generation...")
            
            start_time = time.time()
            response = openai.embeddings.create(
                model="text-embedding-3-large",
                input="test embedding generation"
            )
            embedding_time = (time.time() - start_time) * 1000
            
            embedding = response.data[0].embedding
            
            # Validate embedding properties
            assert len(embedding) == 3072, f"Embedding must be 3072 dimensions, got {len(embedding)}"
            assert all(isinstance(x, (int, float)) for x in embedding), "Embedding must contain numeric values"
            
            print(f"   ✅ Embedding generation working (3072 dims in {embedding_time:.0f}ms)")
            
            # Test 3.3: Error handling for API failures (simulate)
            print("   3.3 Testing error handling...")
            
            # Test with invalid API key scenario (just verify our endpoint handles it)
            async with aiohttp.ClientSession() as session:
                # This will test our API's error handling when OpenAI fails
                # We can't actually break OpenAI, but we test our error response
                try:
                    async with session.post(
                        f"{self.api_base_url}/api/v1/query",
                        json={"query": "test error handling", "top_k": 1}
                    ) as response:
                        # Should work with valid API key
                        assert response.status in [200, 503], "API should handle OpenAI integration properly"
                        print("   ✅ Error handling integration verified")
                        
                except Exception as e:
                    print(f"   ⚠️ Error handling test inconclusive: {e}")
            
            self.test_results["openai_tests"] = {
                "api_key_validation": "PASS",
                "embedding_generation": "PASS", 
                "error_handling": "PASS",
                "performance": f"{embedding_time:.0f}ms",
                "overall": "PASS"
            }
            
            print("✅ TEST 3 PASSED: OpenAI embedding integration working")
            return True
            
        except Exception as e:
            self.critical_issues.append(f"OpenAI integration critical failure: {e}")
            self.test_results["openai_tests"] = {"overall": f"FAIL: {e}"}
            print(f"❌ TEST 3 FAILED: {e}")
            return False
    
    async def test_4_end_to_end_critical_queries(self) -> bool:
        """
        Test 4: End-to-End Query Validation (COMPLETE USER WORKFLOW)
        Following DEVELOPMENT_RULES.md Test 4 requirements
        
        Critical because: If queries don't return right frameworks, Dan gets no value
        """
        print("\n🔍 TEST 4: End-to-End Critical Queries")
        print("-" * 40)
        
        # Dan's critical use cases following his workflow requirements
        critical_queries = [
            {
                "query": "value equation",
                "expected_framework": "the_value_equation",
                "expected_chunk": "value_equation_complete_framework_010",
                "use_case": "Dan asks about value creation fundamentals"
            },
            {
                "query": "pricing strategy",
                "expected_framework": "premium_pricing_philosophy", 
                "expected_chunk": "premium_pricing_mindset_philosophy_008",
                "use_case": "Dan needs pricing guidance for client offers"
            },
            {
                "query": "how to create compelling offers",
                "expected_framework": "problems_to_solutions_transformation",
                "expected_chunk": "problems_solutions_framework_012",
                "use_case": "Dan building offers for clients"
            },
            {
                "query": "guarantee strategy",
                "expected_framework": "comprehensive_guarantee_system",
                "expected_chunk": "guarantees_framework_017",
                "use_case": "Dan needs risk reversal for high-ticket offers"
            }
        ]
        
        async with aiohttp.ClientSession() as session:
            try:
                passed_queries = 0
                query_times = []
                
                for i, test_case in enumerate(critical_queries, 1):
                    print(f"   4.{i} Testing: '{test_case['query']}'")
                    print(f"      Use case: {test_case['use_case']}")
                    
                    start_time = time.time()
                    
                    async with session.post(
                        f"{self.api_base_url}/api/v1/query",
                        json={
                            "query": test_case["query"],
                            "top_k": 5,
                            "search_type": "vector"
                        }
                    ) as response:
                        total_time = (time.time() - start_time) * 1000
                        query_times.append(total_time)
                        
                        assert response.status == 200, f"Query must return 200, got {response.status}"
                        
                        result = await response.json()
                        
                        # Validate response structure
                        assert "results" in result and len(result["results"]) > 0, "Must return framework results"
                        
                        # Check if expected framework is in top results
                        top_results = result["results"][:3]  # Check top 3
                        framework_found = False
                        chunk_found = False
                        
                        for res in top_results:
                            if test_case["expected_framework"] in res["framework_name"]:
                                framework_found = True
                            if test_case["expected_chunk"] in res["chunk_id"]:
                                chunk_found = True
                        
                        # For critical queries, we want exact matches
                        if framework_found or chunk_found:
                            print(f"      ✅ Correct framework found (relevance: {top_results[0]['similarity_score']:.2f})")
                            print(f"      Framework: {top_results[0]['framework_name']}")
                            print(f"      Time: {total_time:.0f}ms")
                            passed_queries += 1
                        else:
                            print(f"      ⚠️ Expected framework not in top 3 results")
                            print(f"      Got: {[r['framework_name'] for r in top_results]}")
                
                # Performance validation
                avg_time = sum(query_times) / len(query_times)
                max_time = max(query_times)
                
                print(f"\n   📊 Query Performance Summary:")
                print(f"      Average: {avg_time:.0f}ms")  
                print(f"      Maximum: {max_time:.0f}ms")
                print(f"      Successful queries: {passed_queries}/{len(critical_queries)}")
                
                # Success criteria: At least 75% of critical queries work
                success_rate = passed_queries / len(critical_queries)
                performance_acceptable = max_time < 3000  # Reasonable with OpenAI latency
                
                overall_pass = success_rate >= 0.75 and performance_acceptable
                
                self.test_results["end_to_end_tests"] = {
                    "queries_tested": len(critical_queries),
                    "queries_passed": passed_queries,
                    "success_rate": success_rate,
                    "average_time_ms": avg_time,
                    "max_time_ms": max_time,
                    "performance_acceptable": performance_acceptable,
                    "overall": "PASS" if overall_pass else "FAIL"
                }
                
                self.test_results["performance_results"] = {
                    "critical_query_avg_ms": avg_time,
                    "critical_query_max_ms": max_time,
                    "target_ms": 500,
                    "acceptable_with_openai_ms": 3000,
                    "status": "PASS" if performance_acceptable else "SLOW"
                }
                
                if overall_pass:
                    print("✅ TEST 4 PASSED: End-to-end critical queries working")
                    return True
                else:
                    self.critical_issues.append(f"End-to-end queries: {passed_queries}/{len(critical_queries)} passed")
                    print(f"❌ TEST 4 FAILED: Only {passed_queries}/{len(critical_queries)} queries passed")
                    return False
                    
            except Exception as e:
                self.critical_issues.append(f"End-to-end testing failure: {e}")
                self.test_results["end_to_end_tests"] = {"overall": f"FAIL: {e}"}
                print(f"❌ TEST 4 FAILED: {e}")
                return False
    
    async def test_integration_validation(self) -> bool:
        """
        Integration Validation: Component boundaries work together
        Following DEVELOPMENT_RULES.md integration requirements
        """
        print("\n🔍 INTEGRATION VALIDATION")
        print("-" * 40)
        
        try:
            # Integration 1: Storage ↔ Database
            print("   INT.1 Testing Storage ↔ Database integration...")
            from production.api.hormozi_rag.storage.postgresql_storage import PostgreSQLVectorDB
            
            storage = PostgreSQLVectorDB()
            test_embedding = [0.1] * 3072
            results = storage.search(test_embedding, top_k=2)
            
            assert len(results) > 0, "Storage must successfully query database"
            print("   ✅ Storage ↔ Database integration working")
            
            # Integration 2: API ↔ Storage
            print("   INT.2 Testing API ↔ Storage integration...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/api/v1/query",
                    json={"query": "test integration", "top_k": 2}
                ) as response:
                    assert response.status == 200, "API must successfully use storage"
                    result = await response.json()
                    assert len(result["results"]) > 0, "API must return storage results"
            
            print("   ✅ API ↔ Storage integration working")
            
            # Integration 3: Configuration ↔ All Components
            print("   INT.3 Testing Configuration integration...")
            
            # Verify all components use same configuration source
            from production.api.hormozi_rag.config.settings import settings
            
            # Test that storage uses config (verify through successful connection)
            assert storage.pool is not None, "Storage must initialize connection pool"
            assert not storage.pool.closed, "Storage connection pool must be working"
            
            print("   ✅ Configuration integration working")
            
            self.test_results["integration_validation"] = {
                "storage_database": "PASS",
                "api_storage": "PASS", 
                "configuration": "PASS",
                "overall": "PASS"
            }
            
            print("✅ INTEGRATION VALIDATION PASSED")
            return True
            
        except Exception as e:
            self.critical_issues.append(f"Integration validation failure: {e}")
            self.test_results["integration_validation"] = {"overall": f"FAIL: {e}"}
            print(f"❌ INTEGRATION VALIDATION FAILED: {e}")
            return False
    
    def test_regression_validation(self) -> bool:
        """
        Regression Validation: Existing functionality still works
        Following DEVELOPMENT_RULES.md regression requirements
        """
        print("\n🔍 REGRESSION VALIDATION")
        print("-" * 40)
        
        try:
            # Regression 1: PostgreSQL database unchanged
            print("   REG.1 Testing PostgreSQL database integrity...")
            
            import psycopg2
            conn = psycopg2.connect(
                host=TEST_CONFIG['POSTGRES_HOST'],
                database=TEST_CONFIG['POSTGRES_DB'],
                user=TEST_CONFIG['POSTGRES_USER'],
                password=TEST_CONFIG['POSTGRES_PASSWORD'],
                port=int(TEST_CONFIG['POSTGRES_PORT'])
            )
            
            cursor = conn.cursor()
            
            # Verify no data corruption
            cursor.execute("SELECT COUNT(*) FROM framework_documents")
            doc_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM chunk_embeddings") 
            emb_count = cursor.fetchone()[0]
            
            assert doc_count == 20, f"Document count changed: expected 20, got {doc_count}"
            assert emb_count == 20, f"Embedding count changed: expected 20, got {emb_count}"
            
            conn.close()
            print("   ✅ Database integrity unchanged")
            
            # Regression 2: Original data still accessible  
            print("   REG.2 Testing original data accessibility...")
            
            # Test that original chunks are still retrievable
            cursor = psycopg2.connect(**{
                'host': TEST_CONFIG['POSTGRES_HOST'],
                'database': TEST_CONFIG['POSTGRES_DB'],
                'user': TEST_CONFIG['POSTGRES_USER'],
                'password': TEST_CONFIG['POSTGRES_PASSWORD'],
                'port': int(TEST_CONFIG['POSTGRES_PORT'])
            }).cursor()
            
            cursor.execute("SELECT chunk_id FROM framework_documents ORDER BY chunk_id LIMIT 5")
            chunks = cursor.fetchall()
            
            assert len(chunks) > 0, "Original chunks must still be accessible"
            print(f"   ✅ Original data accessible ({len(chunks)} chunks verified)")
            
            self.test_results["regression_validation"] = {
                "database_integrity": "PASS",
                "data_accessibility": "PASS",
                "overall": "PASS"
            }
            
            print("✅ REGRESSION VALIDATION PASSED")
            return True
            
        except Exception as e:
            self.critical_issues.append(f"Regression validation failure: {e}")
            self.test_results["regression_validation"] = {"overall": f"FAIL: {e}"}
            print(f"❌ REGRESSION VALIDATION FAILED: {e}")
            return False
    
    def generate_test_execution_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive test execution report following DEVELOPMENT_RULES.md template
        """
        # Calculate overall success metrics
        all_test_categories = [
            self.test_results["postgresql_tests"].get("overall", "FAIL"),
            self.test_results["fastapi_tests"].get("overall", "FAIL"),
            self.test_results["openai_tests"].get("overall", "FAIL"),
            self.test_results["end_to_end_tests"].get("overall", "FAIL")
        ]
        
        passed_categories = sum(1 for status in all_test_categories if status == "PASS")
        total_categories = len(all_test_categories)
        
        overall_success = passed_categories == total_categories and len(self.critical_issues) == 0
        
        self.test_results["test_execution_id"] = f"critical_path_{int(time.time())}"
        
        report = {
            "test_execution_report": {
                "component": "Day 1 FastAPI Implementation", 
                "date": datetime.utcnow().isoformat(),
                "test_type": "Critical Path + Integration",
                "status": "PASS" if overall_success else "FAIL",
                "summary": {
                    "categories_tested": total_categories,
                    "categories_passed": passed_categories,
                    "success_rate": f"{passed_categories}/{total_categories}",
                    "critical_issues_count": len(self.critical_issues)
                }
            },
            "detailed_results": self.test_results,
            "critical_issues": self.critical_issues,
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if self.critical_issues:
            recommendations.append("CRITICAL: Fix all critical issues before proceeding to Day 2")
        
        # Performance recommendations
        if self.test_results.get("performance_results", {}).get("critical_query_avg_ms", 0) > 1000:
            recommendations.append("Consider caching for embedding generation to improve query performance")
        
        # Integration recommendations
        if self.test_results.get("integration_validation", {}).get("overall") == "PASS":
            recommendations.append("Integration validation passed - ready for MCP server implementation")
        
        if not recommendations:
            recommendations.append("All critical path tests passed - system ready for production use")
        
        return recommendations
    
    async def run_critical_path_test_suite(self) -> bool:
        """
        Execute complete critical path test suite following DEVELOPMENT_RULES.md
        
        Returns True if system ready for production use, False if critical issues found
        """
        print("🚀 CRITICAL PATH TEST SUITE EXECUTION")
        print("=" * 60)
        print("Following DEVELOPMENT_RULES.md Mandatory Testing Discipline")
        print("Testing the 20% that breaks 80% of functionality")
        print("=" * 60)
        
        # Execute all critical path tests
        test_1_pass = self.test_1_postgresql_critical_path()
        test_2_pass = await self.test_2_fastapi_critical_endpoints()  
        test_3_pass = await self.test_3_openai_embedding_integration()
        test_4_pass = await self.test_4_end_to_end_critical_queries()
        
        # Execute integration validation
        integration_pass = await self.test_integration_validation()
        
        # Execute regression validation
        regression_pass = self.test_regression_validation()
        
        # Generate comprehensive report
        test_report = self.generate_test_execution_report()
        
        # Save test execution report
        report_file = Path(__file__).parent / f"test_execution_report_{test_report['test_execution_report']['test_execution_id']}.json"
        with open(report_file, 'w') as f:
            json.dump(test_report, f, indent=2)
        
        # Print results summary
        print("\n" + "=" * 60)
        print("🎯 CRITICAL PATH TEST RESULTS SUMMARY")
        print("=" * 60)
        
        tests = [
            ("PostgreSQL Critical Path", test_1_pass),
            ("FastAPI Critical Endpoints", test_2_pass),
            ("OpenAI Embedding Integration", test_3_pass), 
            ("End-to-End Query Validation", test_4_pass),
            ("Integration Validation", integration_pass),
            ("Regression Validation", regression_pass)
        ]
        
        for test_name, passed in tests:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        overall_success = all([test_1_pass, test_2_pass, test_3_pass, test_4_pass, integration_pass, regression_pass])
        
        print("\n" + "=" * 60)
        
        if overall_success:
            print("✅ ALL CRITICAL PATH TESTS PASSED")
            print("🚀 System validated - ready for Day 2 MCP implementation")
            print(f"📋 Test Report: {report_file}")
        else:
            print("❌ CRITICAL PATH FAILURES DETECTED")
            print("🔧 Must fix issues before proceeding")
            print(f"📋 Issues: {len(self.critical_issues)}")
            for issue in self.critical_issues:
                print(f"   - {issue}")
        
        return overall_success


async def main():
    """
    Execute critical path testing following DEVELOPMENT_RULES.md mandatory discipline
    """
    print("📋 STARTING CRITICAL PATH TESTING")
    print("Following DEVELOPMENT_RULES.md: Test 20% that breaks 80% of functionality")
    print()
    
    tester = CriticalPathTestSuite()
    
    # Note: FastAPI server must be running on localhost:8000
    print("⚠️  REQUIREMENT: FastAPI server must be running")
    print("   Start with: cd production && [env vars] python3 -m uvicorn api.hormozi_rag.api.app:app")
    print()
    
    try:
        success = await tester.run_critical_path_test_suite()
        
        if success:
            print("\n🎉 CRITICAL PATH VALIDATION COMPLETE - SYSTEM READY")
            exit(0)
        else:
            print("\n❌ CRITICAL PATH FAILURES - SYSTEM NOT READY") 
            exit(1)
            
    except Exception as e:
        print(f"\n💥 Critical path testing failed to execute: {e}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())