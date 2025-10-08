#!/usr/bin/env python3
"""
Hormozi MCP Server for Claude Desktop Integration
Following ARCHITECTURE.md HTTP bridge pattern and DEVELOPMENT_RULES.md MCP integration rules

FILE LIFECYCLE: development (moving to production when stable)
PURPOSE: Bridge Claude Desktop to FastAPI service using MCP protocol
REPLACES: Direct Claude Desktop database access
CLEANUP_DATE: Move to production/ when integration tests pass

ARCHITECTURE COMPLIANCE:
- Single Responsibility: Claude Desktop bridge only (no business logic)
- HTTP Communication: All database access through FastAPI endpoints (no direct PostgreSQL)
- Error Translation: Technical errors → User-friendly Claude messages
- State Management: Stateless MCP tools (no session storage)
"""

import asyncio
import aiohttp
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import sys
from pathlib import Path

# Configure logging for MCP server
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """MCP tool definition following Anthropic MCP protocol"""
    name: str
    description: str
    inputSchema: Dict[str, Any]


class HormoziMCPServer:
    """
    MCP Server for Hormozi framework access via Claude Desktop
    
    ARCHITECTURE COMPLIANCE:
    - Single Responsibility: Claude Desktop bridge only
    - HTTP Bridge Pattern: All API access through FastAPI HTTP endpoints
    - Error Translation: Technical errors → Claude-friendly messages per DEVELOPMENT_RULES.md
    - Stateless Design: No session storage, delegate to FastAPI/PostgreSQL
    """
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """
        Initialize MCP server following ARCHITECTURE.md HTTP bridge pattern
        
        Args:
            api_base_url: FastAPI service URL (no direct database access allowed)
        """
        self.api_base_url = api_base_url
        self.api_client = None  # Will be initialized when needed
        
        logger.info(f"Hormozi MCP Server initialized", extra={
            "api_base_url": api_base_url,
            "bridge_pattern": "HTTP only (no direct database)",
            "architecture_compliance": "DEVELOPMENT_RULES.md HTTP bridge"
        })
    
    def get_tools(self) -> List[MCPTool]:
        """
        Define available MCP tools for Claude Desktop following MCP protocol
        
        Returns:
            List of tool definitions that Claude Desktop will see
            
        Following DEVELOPMENT_RULES.md MCP tool definition requirements
        """
        return [
            MCPTool(
                name="search_hormozi_frameworks",
                description="Find relevant Hormozi frameworks for business questions, offer creation, and pricing strategy. Perfect for Dan's workflow: creating offers, pricing guidance, framework application.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Business question or context (e.g., 'How do I justify $10k pricing for web design?', 'Create compelling offer for consulting', 'Value equation application')",
                            "minLength": 1,
                            "maxLength": 1000
                        },
                        "client_context": {
                            "type": "string",
                            "description": "Optional client details (industry, current pricing, specific situation) to personalize framework recommendations",
                            "maxLength": 500
                        }
                    },
                    "required": ["query"]
                }
            ),
            
            MCPTool(
                name="analyze_offer_structure",
                description="Analyze a proposed offer against Hormozi's Grand Slam Offer principles. Returns framework-based analysis with improvement recommendations.",
                inputSchema={
                    "type": "object", 
                    "properties": {
                        "offer_description": {
                            "type": "string",
                            "description": "Description of what you're offering (deliverables, timeline, process, etc.)",
                            "minLength": 10,
                            "maxLength": 2000
                        },
                        "price": {
                            "type": "string", 
                            "description": "Proposed price (e.g., '$10,000', '$5k per month')",
                            "minLength": 1,
                            "maxLength": 100
                        },
                        "client_type": {
                            "type": "string",
                            "description": "Type of client/industry (e.g., 'web design', 'consulting', 'SaaS', 'ecommerce')",
                            "maxLength": 100
                        }
                    },
                    "required": ["offer_description", "price"]
                }
            )
        ]
    
    async def _get_http_client(self):
        """Get async HTTP client for FastAPI communication following ARCHITECTURE.md"""
        if not self.api_client:
            # Create HTTP client with proper timeout and error handling
            timeout = aiohttp.ClientTimeout(total=30, connect=5)
            self.api_client = aiohttp.ClientSession(
                base_url=self.api_base_url,
                timeout=timeout,
                headers={"Content-Type": "application/json"}
            )
        return self.api_client
    
    async def _call_fastapi_query(self, query: str, search_type: str = "vector", top_k: int = 5) -> Dict[str, Any]:
        """
        Call FastAPI /api/v1/query endpoint following DEVELOPMENT_RULES.md HTTP bridge pattern
        
        Args:
            query: User's framework search query
            search_type: "vector" or "hybrid" search
            top_k: Maximum results to return
            
        Returns:
            FastAPI JSON response or raises exception
            
        Following ARCHITECTURE.md: No direct database access, HTTP only
        """
        try:
            http_client = await self._get_http_client()
            
            # Call FastAPI endpoint (HTTP bridge per ARCHITECTURE.md)
            async with http_client.post("/api/v1/query", json={
                "query": query,
                "top_k": top_k,
                "search_type": search_type
            }) as response:
                
                # Log HTTP bridge activity
                logger.info(f"FastAPI HTTP call", extra={
                    "endpoint": "/api/v1/query",
                    "query_length": len(query),
                    "search_type": search_type,
                    "status_code": response.status
                })
                
                if response.status == 200:
                    return await response.json()
                else:
                    # Raise exception for error handling
                    error_text = await response.text()
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=error_text
                    )
                    
        except Exception as e:
            logger.error(f"FastAPI call failed: {e}", extra={
                "query": query,
                "api_base_url": self.api_base_url
            })
            raise
    
    async def search_hormozi_frameworks(self, query: str, client_context: Optional[str] = None) -> str:
        """
        Search Hormozi frameworks tool for Claude Desktop following DEVELOPMENT_RULES.md tool pattern
        
        Args:
            query: User's business question (Dan's queries)
            client_context: Optional client details for personalized results
            
        Returns:
            Formatted string response for Claude Desktop consumption
            
        Error Handling: Technical errors → Claude-friendly messages per DEVELOPMENT_RULES.md
        """
        try:
            # Input validation per ARCHITECTURE.md fail fast principle
            if not query or not query.strip():
                return "I need a specific business question to search the Hormozi frameworks. Please try asking something like 'How do I justify higher pricing?' or 'What's the value equation?'"
            
            if len(query) > 1000:
                return "That question is quite long. Could you please ask a more focused question about Hormozi frameworks or offer creation?"
            
            # Enhance query with client context if provided
            enhanced_query = query.strip()
            if client_context:
                enhanced_query = f"Client context: {client_context.strip()}. Business question: {query.strip()}"
            
            logger.info(f"Processing framework search", extra={
                "query_length": len(query),
                "has_client_context": bool(client_context),
                "enhanced_query_length": len(enhanced_query)
            })
            
            # Call FastAPI through HTTP bridge (no direct database access per ARCHITECTURE.md)
            try:
                api_response = await self._call_fastapi_query(enhanced_query, search_type="vector", top_k=5)
            except aiohttp.ClientResponseError as e:
                # Error translation per DEVELOPMENT_RULES.md
                if e.status == 503:
                    return "The Hormozi framework system is temporarily unavailable. Please try again in a moment."
                elif e.status == 429:
                    return "Too many requests. Please wait a moment before asking another question."
                elif e.status >= 500:
                    return "I'm experiencing a technical issue accessing the Hormozi frameworks. Please try rephrasing your question or try again later."
                else:
                    return f"I had trouble understanding your request. Please try asking a more specific question about Hormozi frameworks, pricing strategy, or offer creation."
            except Exception as e:
                # Catch-all error translation
                return "I encountered an issue while searching the Hormozi frameworks. Please try rephrasing your question or asking about a specific framework like the 'value equation' or 'pricing strategies'."
            
            # Format response for Claude Desktop consumption
            try:
                formatted_response = self._format_frameworks_for_claude(api_response, query)
                return formatted_response
                
            except Exception as e:
                logger.error(f"Response formatting failed: {e}", extra={"api_response_keys": list(api_response.keys())})
                return "I found relevant Hormozi frameworks but had trouble formatting the response. Please try asking your question again."
            
        except Exception as e:
            # Final error handling per DEVELOPMENT_RULES.md error translation
            logger.error(f"Framework search failed: {e}", extra={"query": query})
            return "I encountered an unexpected issue while searching the Hormozi frameworks. Please try asking your question again, or ask about a specific topic like 'value creation' or 'pricing strategy'."
    
    def _format_frameworks_for_claude(self, api_response: Dict[str, Any], original_query: str) -> str:
        """
        Format FastAPI response for Claude Desktop consumption
        
        Args:
            api_response: JSON response from FastAPI /api/v1/query endpoint
            original_query: User's original query for context
            
        Returns:
            Formatted string that Claude Desktop can present to user
        """
        try:
            results = api_response.get("results", [])
            total_results = api_response.get("total_results", 0)
            query_time = api_response.get("query_time_ms", 0)
            
            if not results:
                return f"I couldn't find specific Hormozi frameworks for '{original_query}'. Try asking about topics like 'value equation', 'pricing strategy', 'guarantees', or 'offer creation'."
            
            # Format framework results for Claude Desktop
            formatted_response = f"**Found {total_results} relevant Hormozi frameworks for your question:**\n\n"
            
            for i, framework in enumerate(results[:3], 1):  # Show top 3 results
                framework_name = framework.get("framework_name", "Unknown Framework")
                section = framework.get("section", "Unknown Section")
                content_snippet = framework.get("content_snippet", "")
                similarity_score = framework.get("similarity_score", 0)
                
                # Clean up framework name for display
                display_name = framework_name.replace("_", " ").title()
                
                formatted_response += f"**{i}. {display_name}**\n"
                formatted_response += f"*From*: {section}\n"
                formatted_response += f"*Relevance*: {abs(similarity_score):.2f}\n\n"
                
                # Include framework content (truncated for readability)
                if content_snippet:
                    # Take first 200 chars for Claude readability
                    snippet = content_snippet[:200].strip()
                    if len(content_snippet) > 200:
                        snippet += "..."
                    formatted_response += f"*Framework Content*: {snippet}\n\n"
                
            # Add usage guidance
            formatted_response += f"*Found in {query_time:.0f}ms. You can ask follow-up questions about any of these frameworks or request specific implementation guidance.*"
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Response formatting error: {e}")
            return f"I found {len(results)} relevant frameworks but had trouble formatting the response. The frameworks relate to your question about '{original_query}'."
    
    async def analyze_offer_structure(self, offer_description: str, price: str, client_type: Optional[str] = None) -> str:
        """
        Analyze offer against Hormozi frameworks (future endpoint - using search for now)
        
        Args:
            offer_description: What's being offered
            price: Proposed price
            client_type: Type of client/industry
            
        Returns:
            Framework-based analysis for Claude Desktop
        """
        try:
            # For MVP, use framework search to find relevant analysis frameworks
            analysis_query = f"offer analysis pricing strategy evaluation {client_type or ''}"
            
            try:
                api_response = await self._call_fastapi_query(analysis_query, search_type="vector", top_k=3)
            except Exception as e:
                return "I'm currently unable to analyze offers against the Hormozi frameworks. Please try asking for specific frameworks like 'value equation' or 'guarantee strategies' to manually analyze your offer."
            
            # Format analysis response for Claude Desktop
            analysis = f"**Offer Analysis Using Hormozi Frameworks:**\n\n"
            analysis += f"*Your Offer*: {offer_description}\n"
            analysis += f"*Price*: {price}\n"
            analysis += f"*Client Type*: {client_type or 'General'}\n\n"
            analysis += "**Relevant Analysis Frameworks:**\n\n"
            
            results = api_response.get("results", [])
            
            for i, framework in enumerate(results[:3], 1):
                framework_name = framework.get("framework_name", "").replace("_", " ").title()
                content = framework.get("content_snippet", "")
                
                analysis += f"**{i}. {framework_name}**: "
                analysis += f"{content[:150]}...\n\n" if len(content) > 150 else f"{content}\n\n"
            
            analysis += "*Use these frameworks to evaluate and improve your offer structure, pricing justification, and value proposition.*"
            
            return analysis
            
        except Exception as e:
            logger.error(f"Offer analysis failed: {e}")
            return f"I encountered an issue analyzing your offer. You can manually apply Hormozi frameworks by asking about 'value equation', 'pricing strategy', or 'guarantee structures' for your {client_type or 'business'} offer."
    
    async def close(self):
        """Close HTTP client when MCP server shuts down"""
        if self.api_client:
            await self.api_client.close()
            logger.info("HTTP client closed")


# MCP Server Protocol Implementation (Basic Framework)
async def run_mcp_server():
    """
    Run MCP server following Anthropic MCP protocol
    
    Note: This is a basic implementation for testing. Full MCP protocol
    implementation would require MCP library integration.
    """
    server = HormoziMCPServer()
    
    try:
        logger.info("Starting Hormozi MCP Server for Claude Desktop integration")
        
        # For testing purposes, demonstrate tool availability
        tools = server.get_tools()
        logger.info(f"MCP Tools available: {[tool.name for tool in tools]}")
        
        # In full implementation, this would start MCP protocol server
        # For now, this validates the server can be instantiated and tools defined
        
        print("🚀 Hormozi MCP Server ready for Claude Desktop integration")
        print(f"📋 Available tools: {[tool.name for tool in tools]}")
        print("💡 Integration: Configure Claude Desktop MCP settings to connect")
        
        return server
        
    except Exception as e:
        logger.error(f"MCP server startup failed: {e}")
        raise


if __name__ == "__main__":
    """
    MCP server standalone execution for testing and development
    
    Usage:
    1. Start FastAPI server: cd production && [env_vars] python3 -m uvicorn api.hormozi_rag.api.app:app
    2. Run MCP server: python3 development/mcp_server/hormozi_mcp.py
    3. Configure Claude Desktop to use this MCP server
    """
    
    print("🔧 Hormozi MCP Server - Development Mode")
    print("Following ARCHITECTURE.md HTTP bridge pattern")
    print()
    
    try:
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        print("\n🔄 MCP server stopped")
    except Exception as e:
        print(f"\n❌ MCP server failed: {e}")
        sys.exit(1)