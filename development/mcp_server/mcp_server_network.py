#!/usr/bin/env python3
"""
Hormozi MCP Server - Network Service Mode
For Claude Desktop remote MCP server URL connection

FILE LIFECYCLE: development
PURPOSE: Run MCP server as network service for Claude Desktop remote connection
"""

import asyncio
import json
from aiohttp import web, ClientSession
from datetime import datetime
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from development.mcp_server.hormozi_mcp import HormoziMCPServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPNetworkServer:
    """MCP server running as network service for Claude Desktop remote connection"""
    
    def __init__(self, port: int = 8001):
        self.port = port
        self.mcp_server = HormoziMCPServer()
        self.app = web.Application()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup HTTP routes for MCP protocol"""
        self.app.router.add_post('/mcp', self.handle_mcp_request)
        self.app.router.add_get('/tools', self.get_tools)
        self.app.router.add_options('/{path:.*}', self.handle_cors)
        
        # Add CORS headers
        self.app.middlewares.append(self.cors_middleware)
    
    @web.middleware
    async def cors_middleware(self, request, handler):
        """Add CORS headers for Claude Desktop"""
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
    async def handle_cors(self, request):
        """Handle CORS preflight requests"""
        return web.Response(
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            }
        )
    
    async def get_tools(self, request):
        """Return available MCP tools"""
        tools = self.mcp_server.get_tools()
        tool_list = []
        
        for tool in tools:
            tool_list.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            })
        
        return web.json_response({"tools": tool_list})
    
    async def handle_mcp_request(self, request):
        """Handle MCP tool calls from Claude Desktop"""
        try:
            data = await request.json()
            
            tool_name = data.get('tool')
            parameters = data.get('parameters', {})
            
            logger.info(f"MCP tool call: {tool_name}", extra=parameters)
            
            if tool_name == 'search_hormozi_frameworks':
                query = parameters.get('query', '')
                client_context = parameters.get('client_context')
                
                result = await self.mcp_server.search_hormozi_frameworks(query, client_context)
                
                return web.json_response({
                    "result": result,
                    "tool": tool_name,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif tool_name == 'analyze_offer_structure':
                offer_description = parameters.get('offer_description', '')
                price = parameters.get('price', '')
                client_type = parameters.get('client_type')
                
                result = await self.mcp_server.analyze_offer_structure(offer_description, price, client_type)
                
                return web.json_response({
                    "result": result,
                    "tool": tool_name,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            else:
                return web.json_response(
                    {"error": f"Unknown tool: {tool_name}"},
                    status=400
                )
                
        except Exception as e:
            logger.error(f"MCP request failed: {e}")
            return web.json_response(
                {"error": f"Tool execution failed: {str(e)}"},
                status=500
            )

async def start_mcp_network_server():
    """Start MCP server as network service"""
    server = MCPNetworkServer(port=8001)
    
    print("🚀 Starting Hormozi MCP Network Server")
    print(f"📡 Server URL: http://localhost:8001")
    print("🔧 Available endpoints:")
    print("   - GET  /tools  (list available tools)")
    print("   - POST /mcp    (execute tool calls)")
    print()
    print("🎯 Use in Claude Desktop:")
    print("   Name: Hormozi Frameworks")
    print("   URL: http://localhost:8001")
    print()
    
    runner = web.AppRunner(server.app)
    await runner.setup()
    
    site = web.TCPSite(runner, 'localhost', 8001)
    await site.start()
    
    logger.info(f"MCP Network Server started on http://localhost:8001")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🔄 Shutting down MCP network server...")
        await server.mcp_server.close()
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(start_mcp_network_server())
    except Exception as e:
        print(f"❌ MCP network server failed: {e}")
        sys.exit(1)