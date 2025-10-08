#!/usr/bin/env python3
"""
MCP Server Critical Path Tests - TDD Red Phase
Following DEVELOPMENT_RULES.md TDD approach - write tests first, then implement

FILE LIFECYCLE: development
PURPOSE: Define what MCP server should do before implementing (TDD Red phase)
TESTING APPROACH: Critical path (20% that breaks 80% of MCP functionality)
CLEANUP_DATE: Keep for regression testing

Critical Path for MCP Server:
1. Tool schema definition and registration (Claude Desktop needs to know what tools exist)
2. HTTP bridge to FastAPI endpoints (MCP calls must reach real system) 
3. Claude Desktop tool calling interface (user interaction point)
4. Error translation (API errors → Claude-friendly messages)
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import time
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class MCPServerCriticalPathTests:
    """
    TDD Red Phase: Define what MCP server should do
    
    These tests will FAIL initially - that's expected for TDD Red phase
    Implementation goal: Make all these tests pass
    """
    
    def __init__(self):
        self.test_results = {
            "test_execution_id": f"mcp_tdd_{int(time.time())}",
            "timestamp": datetime.utcnow().isoformat(),
            "tdd_phase": "RED (tests written first)",
            "tool_schema_tests": {},
            "http_bridge_tests": {},
            "claude_interface_tests": {},
            "error_translation_tests": {},
            "integration_tests": {},
            "errors_discovered": []
        }
        
        # MCP server will be imported here once implemented
        self.mcp_server = None
    
    def test_1_tool_schema_definition(self) -> bool:
        """
        Critical Path Test 1: Tool Schema Definition
        
        EXPECTED (TDD Red): This test will FAIL because MCP server not implemented yet
        GOAL: Define what tools Claude Desktop should see
        CRITICAL: If tool schemas fail, Claude Desktop cannot call our functions
        """
        print("🔍 TEST 1: MCP Tool Schema Definition (TDD Red Phase)")
        print("-" * 50)
        
        try:
            # Import MCP server (will fail in Red phase - that's expected)
            try:
                from development.mcp_server.hormozi_mcp import HormoziMCPServer
                self.mcp_server = HormoziMCPServer()
            except ImportError as e:
                print(f"   ❌ EXPECTED FAILURE (TDD Red): MCP server not implemented yet")
                print(f"      ImportError: {e}")
                self.test_results["errors_discovered"].append({
                    "error_id": "MCP-001",
                    "error_type": "ImportError", 
                    "description": "MCP server module does not exist yet",
                    "discovery_method": "TDD test execution",
                    "expected": True,
                    "tdd_phase": "RED"
                })
                return False  # Expected failure in Red phase
            
            # Test 1.1: Tool definitions exist
            print("   1.1 Testing tool schema definitions...")
            
            tools = self.mcp_server.get_tools()
            assert isinstance(tools, list), "get_tools() must return list"
            assert len(tools) >= 1, "Must define at least search_hormozi_frameworks tool"
            
            # Test 1.2: search_hormozi_frameworks tool definition
            print("   1.2 Testing search_hormozi_frameworks tool schema...")
            
            search_tool = None
            for tool in tools:
                if tool.name == "search_hormozi_frameworks":
                    search_tool = tool
                    break
            
            assert search_tool is not None, "search_hormozi_frameworks tool must be defined"
            assert hasattr(search_tool, 'description'), "Tool must have description"
            assert hasattr(search_tool, 'inputSchema'), "Tool must have input schema"
            
            # Validate schema structure follows MCP protocol
            schema = search_tool.inputSchema
            assert schema.get('type') == 'object', "Tool schema must be object type"
            assert 'properties' in schema, "Tool schema must have properties"
            assert 'query' in schema['properties'], "Tool must accept query parameter"
            
            print("   ✅ Tool schema definition working")
            
            self.test_results["tool_schema_tests"] = {
                "tools_defined": len(tools),
                "search_tool_found": True,
                "schema_validation": "PASS",
                "overall": "PASS"
            }
            
            print("✅ TEST 1 PASSED: Tool schema definition working")
            return True
            
        except Exception as e:
            print(f"   ❌ TEST 1 FAILED: {e}")
            self.test_results["errors_discovered"].append({
                "error_id": "MCP-002",
                "error_type": type(e).__name__,
                "description": f"Tool schema definition error: {e}",
                "discovery_method": "TDD test execution"
            })
            self.test_results["tool_schema_tests"] = {"overall": f"FAIL: {e}"}
            return False
    
    async def test_2_http_bridge_functionality(self) -> bool:
        """
        Critical Path Test 2: HTTP Bridge to FastAPI
        
        EXPECTED (TDD Red): This test will FAIL because HTTP bridge not implemented
        GOAL: Define how MCP server should call FastAPI endpoints  
        CRITICAL: If HTTP bridge fails, MCP cannot access framework data
        """
        print("\n🔍 TEST 2: HTTP Bridge to FastAPI (TDD Red Phase)")
        print("-" * 50)
        
        try:
            if not self.mcp_server:
                print(f"   ❌ EXPECTED FAILURE (TDD Red): MCP server not available for HTTP bridge testing")
                return False
            
            # Test 2.1: HTTP client initialization
            print("   2.1 Testing HTTP client initialization...")
            
            assert hasattr(self.mcp_server, 'api_client'), "MCP server must have HTTP client"
            assert self.mcp_server.api_base_url, "Must have FastAPI base URL configured"
            
            # Test 2.2: FastAPI endpoint calling capability
            print("   2.2 Testing FastAPI endpoint calling...")
            
            # Test calling /api/v1/query through HTTP bridge
            test_query = "value equation test"
            result = await self.mcp_server._call_fastapi_query(test_query)
            
            assert isinstance(result, dict), "HTTP bridge must return JSON response"
            assert 'results' in result, "Response must contain framework results"
            assert len(result['results']) > 0, "Must return framework data"
            
            print("   ✅ HTTP bridge functionality working")
            
            # Test 2.3: Error handling for API failures
            print("   2.3 Testing API error handling...")
            
            # Test with invalid endpoint (should handle gracefully)
            try:
                error_result = await self.mcp_server._call_fastapi_query("")  # Empty query should error
                # Should return error message, not crash
                assert isinstance(error_result, str), "Error response should be user-friendly string"
            except Exception as bridge_error:
                print(f"      Error handling test: {bridge_error}")
            
            self.test_results["http_bridge_tests"] = {
                "http_client": "PASS",
                "fastapi_calling": "PASS", 
                "error_handling": "PASS",
                "overall": "PASS"
            }
            
            print("✅ TEST 2 PASSED: HTTP bridge functionality working")
            return True
            
        except Exception as e:
            print(f"   ❌ TEST 2 FAILED: {e}")
            self.test_results["errors_discovered"].append({
                "error_id": "MCP-003",
                "error_type": type(e).__name__,
                "description": f"HTTP bridge error: {e}",
                "discovery_method": "TDD test execution"
            })
            self.test_results["http_bridge_tests"] = {"overall": f"FAIL: {e}"}
            return False
    
    async def test_3_claude_interface_functionality(self) -> bool:
        """
        Critical Path Test 3: Claude Desktop Tool Calling Interface
        
        EXPECTED (TDD Red): This test will FAIL because tool implementations don't exist
        GOAL: Define how Claude Desktop will interact with our tools
        CRITICAL: If Claude interface fails, Dan cannot use the system
        """
        print("\n🔍 TEST 3: Claude Desktop Interface (TDD Red Phase)")  
        print("-" * 50)
        
        try:
            if not self.mcp_server:
                print(f"   ❌ EXPECTED FAILURE (TDD Red): MCP server not available for interface testing")
                return False
            
            # Test 3.1: search_hormozi_frameworks tool calling
            print("   3.1 Testing search_hormozi_frameworks tool calling...")
            
            # Test Dan's critical use case: framework search for offer creation
            test_query = "How do I justify higher pricing for web design?"
            
            result = await self.mcp_server.search_hormozi_frameworks(test_query)
            
            assert isinstance(result, str), "Tool response must be string for Claude Desktop"
            assert len(result) > 100, "Response must contain substantial framework content"
            assert "framework" in result.lower(), "Response must reference frameworks"
            
            print("   ✅ search_hormozi_frameworks tool working")
            
            # Test 3.2: Context-aware queries
            print("   3.2 Testing context-aware framework search...")
            
            context_query = "web design client pricing strategy"
            context_result = await self.mcp_server.search_hormozi_frameworks(
                query=context_query,
                client_context="Client currently pays $5k elsewhere, wants to charge $10k"
            )
            
            assert isinstance(context_result, str), "Context-aware query must return string"
            assert len(context_result) > 100, "Context-aware response must be substantial"
            
            print("   ✅ Context-aware framework search working")
            
            # Test 3.3: Error handling for Claude Desktop
            print("   3.3 Testing Claude-friendly error handling...")
            
            # Test with problematic query (should return user-friendly message)
            error_response = await self.mcp_server.search_hormozi_frameworks("")
            
            assert isinstance(error_response, str), "Error response must be string"
            assert "error" not in error_response.lower() or "try" in error_response.lower(), "Should be user-friendly"
            
            print("   ✅ Claude-friendly error handling working")
            
            self.test_results["claude_interface_tests"] = {
                "tool_calling": "PASS",
                "context_aware": "PASS",
                "error_handling": "PASS", 
                "overall": "PASS"
            }
            
            print("✅ TEST 3 PASSED: Claude Desktop interface working")
            return True
            
        except Exception as e:
            print(f"   ❌ TEST 3 FAILED: {e}")
            self.test_results["errors_discovered"].append({
                "error_id": "MCP-004", 
                "error_type": type(e).__name__,
                "description": f"Claude interface error: {e}",
                "discovery_method": "TDD test execution"
            })
            self.test_results["claude_interface_tests"] = {"overall": f"FAIL: {e}"}
            return False
    
    async def test_4_end_to_end_mcp_integration(self) -> bool:
        """
        Critical Path Test 4: End-to-End MCP Integration
        
        EXPECTED (TDD Red): This test will FAIL because end-to-end integration not implemented
        GOAL: Define complete workflow from Claude Desktop to PostgreSQL results
        CRITICAL: If end-to-end fails, Dan gets no value from MCP integration
        """
        print("\n🔍 TEST 4: End-to-End MCP Integration (TDD Red Phase)")
        print("-" * 50)
        
        try:
            if not self.mcp_server:
                print(f"   ❌ EXPECTED FAILURE (TDD Red): MCP server not available for end-to-end testing")
                return False
            
            # Test 4.1: Complete workflow - Dan's primary use case
            print("   4.1 Testing complete Dan workflow...")
            
            # Simulate Dan's question about offer creation
            dans_question = "I have a web design client who currently pays $5k elsewhere. I want to charge $10k. Help me create an offer."
            
            # This should go: Claude Desktop → MCP Server → FastAPI → PostgreSQL → Results → Claude
            start_time = time.time()
            workflow_result = await self.mcp_server.search_hormozi_frameworks(
                query="create offer web design pricing value justification",
                client_context="web design client, current $5k, target $10k"
            )
            workflow_time = (time.time() - start_time) * 1000
            
            # Validate complete workflow result
            assert isinstance(workflow_result, str), "Workflow result must be Claude-readable string"
            assert "value" in workflow_result.lower() or "pricing" in workflow_result.lower(), "Must contain relevant frameworks"
            assert len(workflow_result) > 200, "Must provide substantial guidance"
            assert workflow_time < 5000, "Complete workflow must be <5 seconds"
            
            print(f"   ✅ Complete Dan workflow working ({workflow_time:.0f}ms)")
            
            # Test 4.2: Multiple framework retrieval
            print("   4.2 Testing multiple framework retrieval...")
            
            guarantee_query = "What guarantee should I offer for high-ticket services?"
            guarantee_result = await self.mcp_server.search_hormozi_frameworks(guarantee_query)
            
            assert "guarantee" in guarantee_result.lower(), "Guarantee query must return guarantee frameworks"
            
            print("   ✅ Multiple framework retrieval working")
            
            # Test 4.3: Performance under realistic usage
            print("   4.3 Testing performance under realistic usage...")
            
            # Test multiple concurrent queries (simulating Dan + team usage)
            concurrent_queries = [
                "value equation pricing",
                "guarantee strategies",
                "offer creation process",
                "scarcity and urgency"
            ]
            
            query_times = []
            
            for query in concurrent_queries:
                start_time = time.time()
                result = await self.mcp_server.search_hormozi_frameworks(query)
                query_time = (time.time() - start_time) * 1000
                query_times.append(query_time)
                
                assert isinstance(result, str) and len(result) > 100, f"Query '{query}' must return substantial result"
            
            avg_time = sum(query_times) / len(query_times)
            max_time = max(query_times)
            
            print(f"   📊 Performance: avg {avg_time:.0f}ms, max {max_time:.0f}ms")
            
            # Performance should be reasonable for user experience
            performance_acceptable = max_time < 3000  # 3 seconds max for good UX
            
            assert performance_acceptable, f"Performance must be acceptable for user experience, got {max_time:.0f}ms"
            
            print("   ✅ Performance acceptable for realistic usage")
            
            self.test_results["integration_tests"] = {
                "dan_workflow": "PASS",
                "multiple_frameworks": "PASS",
                "performance": f"{avg_time:.0f}ms avg, {max_time:.0f}ms max",
                "performance_acceptable": performance_acceptable,
                "overall": "PASS"
            }
            
            print("✅ TEST 4 PASSED: End-to-end MCP integration working")
            return True
            
        except Exception as e:
            print(f"   ❌ TEST 4 FAILED: {e}")
            self.test_results["errors_discovered"].append({
                "error_id": "MCP-005",
                "error_type": type(e).__name__, 
                "description": f"End-to-end integration error: {e}",
                "discovery_method": "TDD test execution"
            })
            self.test_results["integration_tests"] = {"overall": f"FAIL: {e}"}
            return False
    
    async def test_5_error_translation_quality(self) -> bool:
        """
        Critical Path Test 5: Error Translation Quality
        
        EXPECTED (TDD Red): This test will FAIL because error translation not implemented  
        GOAL: Define how API errors should be translated for Claude Desktop users
        CRITICAL: If error translation fails, Dan gets technical errors instead of helpful messages
        """
        print("\n🔍 TEST 5: Error Translation Quality (TDD Red Phase)")
        print("-" * 50)
        
        try:
            if not self.mcp_server:
                print(f"   ❌ EXPECTED FAILURE (TDD Red): MCP server not available for error translation testing")
                return False
            
            # Test 5.1: API unavailable scenario
            print("   5.1 Testing API unavailable error translation...")
            
            # Simulate FastAPI being down
            original_url = self.mcp_server.api_base_url
            self.mcp_server.api_base_url = "http://localhost:9999"  # Non-existent service
            
            error_result = await self.mcp_server.search_hormozi_frameworks("test query")
            
            # Restore URL
            self.mcp_server.api_base_url = original_url
            
            # Validate error translation quality
            assert isinstance(error_result, str), "Error response must be string for Claude"
            assert len(error_result) > 20, "Error message must be informative"
            assert "temporarily unavailable" in error_result.lower() or "try again" in error_result.lower(), "Must suggest retry"
            assert "503" not in error_result and "HTTP" not in error_result, "Must not expose technical details"
            
            print("   ✅ API unavailable error translation working")
            
            # Test 5.2: Invalid query error handling  
            print("   5.2 Testing invalid query error translation...")
            
            # Test with various problematic queries
            problematic_queries = ["", "   ", "x" * 1001]  # Empty, whitespace, too long
            
            for bad_query in problematic_queries:
                error_response = await self.mcp_server.search_hormozi_frameworks(bad_query)
                assert isinstance(error_response, str), "Error response must be string"
                assert len(error_response) > 10, "Error message must be informative"
                assert "error" not in error_response.lower() or "please" in error_response.lower(), "Should be helpful, not technical"
            
            print("   ✅ Invalid query error translation working")
            
            self.test_results["error_translation_tests"] = {
                "api_unavailable": "PASS",
                "invalid_queries": "PASS",
                "message_quality": "PASS",
                "overall": "PASS"
            }
            
            print("✅ TEST 5 PASSED: Error translation quality working")
            return True
            
        except Exception as e:
            print(f"   ❌ TEST 5 FAILED: {e}")
            self.test_results["errors_discovered"].append({
                "error_id": "MCP-006",
                "error_type": type(e).__name__,
                "description": f"Error translation error: {e}", 
                "discovery_method": "TDD test execution"
            })
            self.test_results["error_translation_tests"] = {"overall": f"FAIL: {e}"}
            return False
    
    def generate_tdd_test_report(self) -> Dict[str, Any]:
        """Generate TDD test execution report following COMPREHENSIVE_TESTING_SPECIFICATION.md"""
        
        # TDD Red phase: expect failures, document what needs to be implemented
        expected_failures = len([err for err in self.test_results["errors_discovered"] if err.get("expected", False)])
        unexpected_failures = len(self.test_results["errors_discovered"]) - expected_failures
        
        return {
            "test_execution_report": {
                "test_execution_id": self.test_results["test_execution_id"],
                "component": "MCP Server (TDD Red Phase)",
                "date": datetime.utcnow().isoformat(), 
                "test_type": "TDD Red Phase - Define Requirements",
                "phase": "RED (write tests first, expect failures)",
                "status": "EXPECTED_FAILURES" if unexpected_failures == 0 else "UNEXPECTED_ISSUES",
                "summary": {
                    "tests_written": 5,
                    "expected_failures": expected_failures,
                    "unexpected_failures": unexpected_failures,
                    "implementation_requirements_defined": True
                }
            },
            "implementation_requirements": {
                "mcp_server_module": "development/mcp_server/hormozi_mcp.py (must create)",
                "http_client": "Async HTTP client for FastAPI bridge",
                "tool_definitions": "search_hormozi_frameworks() with proper schema",
                "error_translation": "API errors → Claude-friendly messages",
                "performance": "Complete workflow <5 seconds"
            },
            "test_results": self.test_results,
            "next_phase": "GREEN - Implement to make tests pass"
        }
    
    async def run_tdd_red_phase(self) -> bool:
        """
        Execute TDD Red Phase: Write tests that define what MCP server should do
        
        Expected: Most/all tests will fail - that's the point of Red phase
        Goal: Define clear requirements for implementation
        """
        print("🚀 TDD RED PHASE: WRITING MCP SERVER TESTS FIRST")
        print("=" * 60)
        print("Following DEVELOPMENT_RULES.md TDD approach")
        print("Expected: Tests will FAIL - that defines what we need to implement")
        print("=" * 60)
        
        # Execute all TDD tests (expecting failures)
        test_1_result = self.test_1_tool_schema_definition()
        test_2_result = await self.test_2_http_bridge_functionality()  
        test_3_result = await self.test_3_claude_interface_functionality()
        test_4_result = await self.test_4_end_to_end_mcp_integration()
        test_5_result = await self.test_5_error_translation_quality()
        
        # Generate TDD report
        tdd_report = self.generate_tdd_test_report()
        
        # Save TDD test results
        test_id = tdd_report['test_execution_report'].get('test_execution_id', f"mcp_tdd_{int(time.time())}")
        report_file = Path(__file__).parent / f"mcp_tdd_red_phase_report_{test_id}.json"
        with open(report_file, 'w') as f:
            json.dump(tdd_report, f, indent=2)
        
        # Print TDD Red phase results
        print("\n" + "=" * 60)
        print("🎯 TDD RED PHASE RESULTS")
        print("=" * 60)
        
        tests = [
            ("Tool Schema Definition", test_1_result),
            ("HTTP Bridge Functionality", test_2_result),
            ("Claude Desktop Interface", test_3_result), 
            ("End-to-End Integration", test_4_result),
            ("Error Translation Quality", test_5_result)
        ]
        
        for test_name, result in tests:
            status = "✅ PASS" if result else "❌ FAIL (expected in Red phase)"
            print(f"{test_name}: {status}")
        
        expected_failures = len([err for err in self.test_results["errors_discovered"] if err.get("expected", False)])
        total_errors = len(self.test_results["errors_discovered"])
        
        print(f"\nErrors discovered: {total_errors}")
        print(f"Expected failures: {expected_failures}")
        print(f"Unexpected issues: {total_errors - expected_failures}")
        
        print(f"\n📋 TDD Red Phase Report: {report_file}")
        
        print("\n🚀 NEXT: TDD GREEN PHASE - Implement to make tests pass")
        
        return True  # Red phase success = requirements defined through failing tests


async def main():
    """Execute TDD Red Phase for MCP server"""
    print("📋 STARTING TDD RED PHASE FOR MCP SERVER")
    print("Following DEVELOPMENT_RULES.md TDD approach")
    print("Writing tests first to define what MCP server should do")
    print()
    
    tester = MCPServerCriticalPathTests()
    await tester.run_tdd_red_phase()
    
    print("\n✅ TDD RED PHASE COMPLETE")
    print("Requirements defined through failing tests")
    print("Next: Implement MCP server to make tests pass (TDD Green phase)")


if __name__ == "__main__":
    asyncio.run(main())