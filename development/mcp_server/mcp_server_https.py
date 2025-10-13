#!/usr/bin/env python3
"""
Hormozi MCP Server - HTTPS Network Service
For Claude Desktop remote MCP server HTTPS URL connection

FILE LIFECYCLE: development
PURPOSE: Run MCP server as HTTPS network service for Claude Desktop remote connection
"""

import asyncio
import json
import ssl
from aiohttp import web
from datetime import datetime
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from development.mcp_server.hormozi_mcp import HormoziMCPServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPHTTPSServer:
    """HTTPS MCP server for Claude Desktop remote connection"""
    
    def __init__(self, port: int = 8443):
        self.port = port
        self.mcp_server = HormoziMCPServer()
        self.app = web.Application()
        self._setup_routes()
        self.ssl_context = self._create_ssl_context()
    
    def _create_ssl_context(self):
        """Create SSL context for HTTPS server"""
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            certfile='development/mcp_server/ssl/cert.pem',
            keyfile='development/mcp_server/ssl/key.pem'
        )
        return ssl_context
    
    def _setup_routes(self):
        """Setup HTTP routes for MCP protocol"""
        self.app.router.add_post('/mcp', self.handle_mcp_request)
        self.app.router.add_get('/tools', self.get_tools)
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_options('/{path:.*}', self.handle_cors)
        
        # Add CORS middleware
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
    
    async def health_check(self, request):
        """Health check for MCP server"""
        return web.json_response({
            "service": "hormozi_mcp_server",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "tools_available": len(self.mcp_server.get_tools())
        })
    
    async def get_tools(self, request):
        """Return available MCP tools for Claude Desktop"""
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
            
            logger.info(f"MCP HTTPS tool call: {tool_name}", extra=parameters)
            
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
            logger.error(f"MCP HTTPS request failed: {e}")
            return web.json_response(
                {"error": f"Tool execution failed: {str(e)}"},
                status=500
            )

async def start_mcp_https_server():
    """Start MCP server as HTTPS network service"""
    server = MCPHTTPSServer(port=8443)
    
    print("🚀 Starting Hormozi MCP HTTPS Server")
    print(f"🔒 HTTPS Server URL: https://localhost:8443")
    print("🔧 Available endpoints:")
    print("   - GET  /tools  (list available tools)")
    print("   - POST /mcp    (execute tool calls)")
    print("   - GET  /health (server health)")
    print()
    print("🎯 Use in Claude Desktop:")
    print("   Name: Hormozi Frameworks")
    print("   URL: https://localhost:8443")
    print()
    
    runner = web.AppRunner(server.app)
    await runner.setup()
    
    site = web.TCPSite(runner, 'localhost', 8443, ssl_context=server.ssl_context)
    await site.start()
    
    logger.info(f"MCP HTTPS Server started on https://localhost:8443")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🔄 Shutting down MCP HTTPS server...")
        await server.mcp_server.close()
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(start_mcp_https_server())
    except Exception as e:
        print(f"❌ MCP HTTPS server failed: {e}")
        sys.exit(1)