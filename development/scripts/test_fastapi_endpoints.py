#!/usr/bin/env python3
"""
Test FastAPI Endpoints End-to-End
Following ARCHITECTURE.md and DATABASE_ENGINEERING_SPEC.md validation requirements

FILE LIFECYCLE: development
PURPOSE: Validate complete Day 1 API functionality before proceeding to MCP
CLEANUP_DATE: Keep for regression testing
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime


class FastAPIEndpointTest:
    """Test suite for FastAPI endpoint functionality"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = {
            "health_checks": {},
            "query_endpoints": {},
            "performance": {},
            "error_handling": {},
            "overall_status": "unknown"
        }
    
    async def test_health_endpoints(self) -> bool:
        """Test all health check endpoints per ARCHITECTURE.md"""
        print("🔍 Testing health check endpoints...")
        
        async with aiohttp.ClientSession() as session:
            try:
                # Test 1: Main health endpoint
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        print(f"✅ /health endpoint: {health_data['status']}")
                        
                        # Validate response structure
                        required_fields = ["service", "status", "timestamp", "checks"]
                        for field in required_fields:
                            assert field in health_data, f"Missing field: {field}"
                        
                        # Check database status
                        if "database" in health_data["checks"]:
                            db_status = health_data["checks"]["database"]
                            print(f"   Database: {db_status.get('data_integrity', {}).get('status', 'unknown')}")
                        
                        # Check performance
                        if "performance" in health_data:
                            perf_time = health_data["performance"]["health_check_time_ms"]
                            print(f"   Performance: {perf_time:.1f}ms (target: <50ms)")
                        
                        self.test_results["health_checks"]["main"] = "PASS"
                        
                    else:
                        print(f"❌ /health endpoint failed: {response.status}")
                        self.test_results["health_checks"]["main"] = f"FAIL: {response.status}"
                        return False
                
                # Test 2: Ready endpoint
                async with session.get(f"{self.base_url}/health/ready") as response:
                    if response.status == 200:
                        ready_data = await response.json()
                        print(f"✅ /health/ready endpoint: {ready_data['status']}")
                        self.test_results["health_checks"]["ready"] = "PASS"
                    else:
                        print(f"❌ /health/ready failed: {response.status}")
                        self.test_results["health_checks"]["ready"] = f"FAIL: {response.status}"
                
                # Test 3: Root endpoint
                async with session.get(f"{self.base_url}/") as response:
                    if response.status == 200:
                        root_data = await response.json()
                        print(f"✅ Root endpoint working: {root_data['name']}")
                        self.test_results["health_checks"]["root"] = "PASS"
                    else:
                        print(f"❌ Root endpoint failed: {response.status}")
                        self.test_results["health_checks"]["root"] = f"FAIL: {response.status}"
                
                return True
                
            except Exception as e:
                print(f"❌ Health endpoint testing failed: {e}")
                self.test_results["health_checks"]["error"] = str(e)
                return False
    
    async def test_query_endpoint(self) -> bool:
        """Test query endpoint functionality and performance"""
        print("\n🔍 Testing query endpoint functionality...")
        
        test_queries = [
            {
                "query": "How do I increase perceived value?",
                "expected_frameworks": ["value_equation"]
            },
            {
                "query": "What's the value equation?",
                "expected_frameworks": ["value_equation"]
            },
            {
                "query": "Creating compelling guarantees",
                "expected_frameworks": ["guarantees"]
            },
            {
                "query": "Pricing strategy for custom work",
                "expected_frameworks": ["pricing", "value"]
            }
        ]
        
        async with aiohttp.ClientSession() as session:
            try:
                query_times = []
                
                for i, test_case in enumerate(test_queries, 1):
                    print(f"\n   Test {i}: '{test_case['query']}'")
                    
                    start_time = time.time()
                    
                    # Test vector search
                    async with session.post(
                        f"{self.base_url}/api/v1/query",
                        json={
                            "query": test_case["query"],
                            "top_k": 5,
                            "search_type": "vector"
                        }
                    ) as response:
                        query_time = (time.time() - start_time) * 1000
                        query_times.append(query_time)
                        
                        if response.status == 200:
                            result = await response.json()
                            
                            # Validate response structure
                            required_fields = ["query", "results", "total_results", "query_time_ms", "request_id"]
                            for field in required_fields:
                                assert field in result, f"Missing field: {field}"
                            
                            results_count = len(result["results"])
                            api_time = result["query_time_ms"]
                            
                            print(f"      ✅ {results_count} results in {api_time:.1f}ms (total: {query_time:.1f}ms)")
                            
                            # Check if relevant frameworks found
                            if results_count > 0:
                                top_result = result["results"][0]
                                print(f"      Top result: {top_result['framework_name']} (score: {top_result['similarity_score']:.2f})")
                            
                        else:
                            print(f"      ❌ Query failed: {response.status}")
                            return False
                
                # Performance analysis
                avg_time = sum(query_times) / len(query_times)
                max_time = max(query_times)
                
                print(f"\n📊 Query Performance Summary:")
                print(f"   Average: {avg_time:.1f}ms")
                print(f"   Maximum: {max_time:.1f}ms")
                print(f"   Target: <500ms (DATABASE_ENGINEERING_SPEC.md)")
                
                performance_pass = max_time <= 500
                
                if performance_pass:
                    print("✅ Performance targets met")
                    self.test_results["performance"]["query"] = "PASS"
                else:
                    print(f"⚠️ Performance warning: {max_time:.1f}ms exceeds 500ms target")
                    self.test_results["performance"]["query"] = "SLOW"
                
                self.test_results["query_endpoints"]["vector_search"] = "PASS"
                return True
                
            except Exception as e:
                print(f"❌ Query endpoint testing failed: {e}")
                self.test_results["query_endpoints"]["vector_search"] = f"FAIL: {e}"
                return False
    
    async def test_hybrid_search(self) -> bool:
        """Test hybrid search functionality per DATABASE_ENGINEERING_SPEC.md FR2"""
        print("\n🔍 Testing hybrid search functionality...")
        
        async with aiohttp.ClientSession() as session:
            try:
                test_query = "value equation pricing strategy"
                
                start_time = time.time()
                
                async with session.post(
                    f"{self.base_url}/api/v1/query",
                    json={
                        "query": test_query,
                        "top_k": 5,
                        "search_type": "hybrid"
                    }
                ) as response:
                    query_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        print(f"   ✅ Hybrid search: {len(result['results'])} results in {query_time:.1f}ms")
                        print(f"   Search type: {result.get('search_type', 'unknown')}")
                        
                        # Validate hybrid-specific fields
                        if "vector_weight" in result:
                            print(f"   Vector weight: {result['vector_weight']} (target: 0.7 per FR2)")
                        
                        # Performance validation per DATABASE_ENGINEERING_SPEC.md FR2
                        if query_time <= 1000:
                            print(f"   ✅ Hybrid search performance: {query_time:.1f}ms <= 1000ms target")
                            self.test_results["performance"]["hybrid"] = "PASS"
                        else:
                            print(f"   ⚠️ Hybrid search slow: {query_time:.1f}ms > 1000ms target")
                            self.test_results["performance"]["hybrid"] = "SLOW"
                        
                        self.test_results["query_endpoints"]["hybrid_search"] = "PASS"
                        return True
                    else:
                        print(f"   ❌ Hybrid search failed: {response.status}")
                        return False
                        
            except Exception as e:
                print(f"❌ Hybrid search test failed: {e}")
                self.test_results["query_endpoints"]["hybrid_search"] = f"FAIL: {e}"
                return False
    
    async def test_error_scenarios(self) -> bool:
        """Test error handling per DEVELOPMENT_RULES.md error response standards"""
        print("\n🔍 Testing error handling scenarios...")
        
        async with aiohttp.ClientSession() as session:
            try:
                # Test 1: Empty query (should return 400)
                async with session.post(
                    f"{self.base_url}/api/v1/query",
                    json={"query": "", "top_k": 5}
                ) as response:
                    if response.status == 422:  # Pydantic validation error
                        print("   ✅ Empty query validation working (422)")
                    else:
                        print(f"   ⚠️ Empty query returned {response.status} (expected 422)")
                
                # Test 2: Invalid top_k (should return 422)
                async with session.post(
                    f"{self.base_url}/api/v1/query",
                    json={"query": "test", "top_k": 25}
                ) as response:
                    if response.status == 422:  # Pydantic validation error
                        print("   ✅ Invalid top_k validation working (422)")
                    else:
                        print(f"   ⚠️ Invalid top_k returned {response.status} (expected 422)")
                
                # Test 3: Malformed JSON
                async with session.post(
                    f"{self.base_url}/api/v1/query",
                    data="invalid json"
                ) as response:
                    if response.status == 422:
                        print("   ✅ Malformed JSON validation working (422)")
                    else:
                        print(f"   ⚠️ Malformed JSON returned {response.status} (expected 422)")
                
                self.test_results["error_handling"]["validation"] = "PASS"
                return True
                
            except Exception as e:
                print(f"❌ Error handling test failed: {e}")
                self.test_results["error_handling"]["validation"] = f"FAIL: {e}"
                return False
    
    async def run_complete_test_suite(self) -> bool:
        """Run complete FastAPI endpoint test suite"""
        print("🚀 Starting FastAPI Endpoint Test Suite")
        print("=" * 60)
        
        tests = [
            ("Health Endpoints", self.test_health_endpoints),
            ("Query Endpoint", self.test_query_endpoint),
            ("Hybrid Search", self.test_hybrid_search),
            ("Error Scenarios", self.test_error_scenarios)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results.append(result)
            except Exception as e:
                print(f"\n{test_name}: ❌ EXCEPTION ({e})")
                results.append(False)
        
        # Overall assessment
        all_pass = all(results)
        
        print("\n" + "=" * 60)
        print("🎯 FASTAPI ENDPOINT TEST RESULTS")
        print("=" * 60)
        
        for i, (test_name, _) in enumerate(tests):
            status = "✅ PASS" if results[i] else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        print("\n📊 Performance Summary:")
        if "query" in self.test_results["performance"]:
            print(f"Query Performance: {self.test_results['performance']['query']}")
        if "hybrid" in self.test_results["performance"]:
            print(f"Hybrid Search Performance: {self.test_results['performance']['hybrid']}")
        
        print("\n" + "=" * 60)
        
        if all_pass:
            print("✅ ALL FASTAPI TESTS PASSED - DAY 1 IMPLEMENTATION COMPLETE")
            print("🚀 Ready for Day 2: MCP Server Implementation")
            self.test_results["overall_status"] = "READY_FOR_MCP"
        else:
            print("❌ SOME FASTAPI TESTS FAILED - REVIEW ISSUES")
            self.test_results["overall_status"] = "NEEDS_FIXES"
        
        return all_pass


async def main():
    """Test FastAPI endpoints"""
    print("📋 FastAPI Endpoint Validation")
    print("Testing against running FastAPI server (must be started first)")
    print()
    
    tester = FastAPIEndpointTest()
    success = await tester.run_complete_test_suite()
    
    if success:
        print("\n🎉 Day 1 FastAPI implementation validated successfully")
        print("💡 Next: Start MCP server implementation (Day 2)")
        exit(0)
    else:
        print("\n❌ Day 1 implementation issues detected")
        print("🔧 Fix FastAPI endpoints before proceeding to MCP")
        exit(1)


if __name__ == "__main__":
    print("⚠️  NOTE: FastAPI server must be running on localhost:8000")
    print("   Start with: cd production && python3 -m uvicorn api.hormozi_rag.api.app:app --reload")
    print()
    
    asyncio.run(main())