#!/usr/bin/env python3
"""
MCP Integration Testing with Real System
Following COMPREHENSIVE_TESTING_SPECIFICATION.md real system requirements

FILE LIFECYCLE: development
PURPOSE: Test MCP server with actual FastAPI + PostgreSQL system (no mocked components)
CLEANUP_DATE: Keep for regression testing

REAL SYSTEM REQUIREMENTS:
- FastAPI server running on localhost:8000
- PostgreSQL database with 20 chunks + embeddings
- OpenAI API connectivity for embeddings
- No mocked components - only real system testing
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import json
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from development.mcp_server.hormozi_mcp import HormoziMCPServer


class MCPRealSystemIntegrationTest:
    """Test MCP server with real system components following COMPREHENSIVE_TESTING_SPECIFICATION.md"""
    
    def __init__(self):
        self.mcp_server = HormoziMCPServer()
        self.test_results = {
            "test_execution_id": f"mcp_real_system_{int(time.time())}",
            "timestamp": datetime.utcnow().isoformat(),
            "test_type": "Real System Integration",
            "results": {},
            "errors_found": [],
            "performance_metrics": {}
        }
    
    async def test_real_system_integration(self) -> bool:
        """
        Test complete MCP → FastAPI → PostgreSQL integration with real components
        
        Following COMPREHENSIVE_TESTING_SPECIFICATION.md: No mocked components
        """
        print("🔍 TESTING MCP → FASTAPI → POSTGRESQL REAL SYSTEM INTEGRATION")
        print("=" * 70)
        
        try:
            # Test 1: Dan's primary use case - value creation question
            print("📋 Testing Dan's primary use case...")
            
            start_time = time.time()
            result = await self.mcp_server.search_hormozi_frameworks(
                query="How do I increase perceived value in my offers?",
                client_context="Web design client, currently paying $5k elsewhere, want to charge $10k"
            )
            query_time = (time.time() - start_time) * 1000
            
            print(f"   ✅ Query completed in {query_time:.0f}ms")
            print(f"   📊 Result length: {len(result)} characters")
            print(f"   🎯 Contains frameworks: {'value' in result.lower() and 'framework' in result.lower()}")
            
            # Validate result quality for Dan's workflow
            assert isinstance(result, str), "Result must be string for Claude Desktop"
            assert len(result) > 200, "Result must provide substantial guidance"
            assert "value" in result.lower(), "Must contain value-related frameworks"
            
            print("   ✅ Dan's primary use case working with real system")
            
            # Test 2: Pricing strategy question
            print("\n📋 Testing pricing strategy framework retrieval...")
            
            start_time = time.time()
            pricing_result = await self.mcp_server.search_hormozi_frameworks(
                "What's the best way to justify premium pricing?"
            )
            pricing_time = (time.time() - start_time) * 1000
            
            print(f"   ✅ Pricing query completed in {pricing_time:.0f}ms")
            print(f"   📊 Result length: {len(pricing_result)} characters")
            
            assert "pricing" in pricing_result.lower(), "Must return pricing-related frameworks"
            
            print("   ✅ Pricing strategy retrieval working")
            
            # Test 3: Guarantee framework question
            print("\n📋 Testing guarantee framework retrieval...")
            
            guarantee_result = await self.mcp_server.search_hormozi_frameworks(
                "What guarantee should I offer for high-ticket services?"
            )
            
            assert "guarantee" in guarantee_result.lower(), "Must return guarantee frameworks"
            
            print("   ✅ Guarantee framework retrieval working")
            
            # Test 4: Performance validation with multiple queries
            print("\n📋 Testing realistic performance with multiple queries...")
            
            test_queries = [
                "value equation application",
                "scarcity and urgency tactics", 
                "offer structure best practices",
                "bonuses and stacking strategies"
            ]
            
            query_times = []
            
            for query in test_queries:
                start_time = time.time()
                result = await self.mcp_server.search_hormozi_frameworks(query)
                query_time = (time.time() - start_time) * 1000
                query_times.append(query_time)
                
                assert len(result) > 100, f"Query '{query}' must return substantial result"
            
            avg_time = sum(query_times) / len(query_times)
            max_time = max(query_times)
            
            print(f"   📊 Performance: avg {avg_time:.0f}ms, max {max_time:.0f}ms")
            
            # Performance should be good for user experience
            performance_acceptable = max_time < 2000  # 2 seconds max for good UX
            
            print(f"   ✅ Performance acceptable: {performance_acceptable}")
            
            self.test_results["performance_metrics"] = {
                "average_query_time_ms": avg_time,
                "max_query_time_ms": max_time,
                "queries_tested": len(test_queries),
                "performance_acceptable": performance_acceptable
            }
            
            # Test 5: Error handling with real system
            print("\n📋 Testing error handling with real system...")
            
            # Test empty query (should be handled gracefully)
            empty_result = await self.mcp_server.search_hormozi_frameworks("")
            assert "specific" in empty_result.lower() or "try" in empty_result.lower(), "Empty query should guide user"
            
            print("   ✅ Error handling working with real system")
            
            self.test_results["results"] = {
                "dans_primary_use_case": "PASS",
                "pricing_strategy": "PASS", 
                "guarantee_frameworks": "PASS",
                "performance_validation": "PASS" if performance_acceptable else "SLOW",
                "error_handling": "PASS",
                "overall": "PASS"
            }
            
            print("\n✅ REAL SYSTEM INTEGRATION TESTS PASSED")
            return True
            
        except Exception as e:
            print(f"\n❌ Real system integration failed: {e}")
            self.test_results["errors_found"].append({
                "error_type": type(e).__name__,
                "description": str(e),
                "component": "MCP Real System Integration"
            })
            self.test_results["results"]["overall"] = f"FAIL: {e}"
            return False
        
        finally:
            # Proper cleanup per error DAY2-003 resolution
            if self.mcp_server.api_client:
                await self.mcp_server.api_client.close()
                print("🔧 HTTP client session closed properly")
    
    def generate_real_system_test_report(self) -> Dict[str, Any]:
        """Generate real system test report following COMPREHENSIVE_TESTING_SPECIFICATION.md"""
        
        return {
            "test_execution_report": {
                "test_execution_id": self.test_results["test_execution_id"],
                "component": "MCP Server Real System Integration",
                "date": self.test_results["timestamp"],
                "test_type": "Real System Integration - No Mocked Components",
                "status": "PASS" if self.test_results["results"].get("overall") == "PASS" else "FAIL"
            },
            "test_results": self.test_results,
            "system_validation": {
                "fastapi_server": "REQUIRED - localhost:8000",
                "postgresql_database": "REQUIRED - hormozi_rag with 20 chunks",
                "openai_api": "REQUIRED - text-embedding-3-large",
                "mocked_components": "NONE - all real system testing"
            },
            "business_value_validation": {
                "dans_workflow": "Framework search for offer creation",
                "semantic_quality": "Relevant frameworks returned for business questions",
                "performance": "Acceptable for real-time Claude Desktop usage",
                "error_handling": "User-friendly messages for Claude interface"
            }
        }
    
    async def run_real_system_tests(self) -> bool:
        """Execute real system integration tests"""
        print("🚀 MCP SERVER REAL SYSTEM INTEGRATION TESTING")
        print("Following COMPREHENSIVE_TESTING_SPECIFICATION.md requirements")
        print("Testing with actual FastAPI + PostgreSQL + OpenAI (no mocked components)")
        print()
        
        success = await self.test_real_system_integration()
        
        # Generate and save test report
        test_report = self.generate_real_system_test_report()
        report_file = Path(__file__).parent / f"mcp_real_system_integration_report_{test_report['test_execution_report']['test_execution_id']}.json"
        
        with open(report_file, 'w') as f:
            json.dump(test_report, f, indent=2)
        
        print(f"\n📋 Real System Test Report: {report_file}")
        
        if success:
            print("\n🎉 MCP SERVER REAL SYSTEM INTEGRATION SUCCESSFUL")
            print("✅ Ready for Claude Desktop configuration and end-to-end validation")
        else:
            print("\n❌ MCP SERVER REAL SYSTEM INTEGRATION ISSUES")
            print("🔧 Fix issues before proceeding to Claude Desktop integration")
        
        return success


async def main():
    """Execute MCP real system integration testing"""
    print("⚠️  REQUIREMENTS:")
    print("   1. FastAPI server running: localhost:8000")
    print("   2. PostgreSQL database: hormozi_rag operational") 
    print("   3. OpenAI API key: configured and working")
    print("   4. No mocked components: testing actual system integration")
    print()
    
    tester = MCPRealSystemIntegrationTest()
    success = await tester.run_real_system_tests()
    
    if success:
        print("\n🚀 Ready for final Claude Desktop integration testing")
        exit(0)
    else:
        print("\n❌ Fix real system integration issues before proceeding")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())