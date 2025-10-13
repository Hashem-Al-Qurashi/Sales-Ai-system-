#!/bin/bash
# Create self-signed SSL certificate for MCP HTTPS server

# Create directory for SSL certificates
mkdir -p development/mcp_server/ssl

# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout development/mcp_server/ssl/key.pem -out development/mcp_server/ssl/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=localhost"

echo "✅ SSL certificate created for MCP HTTPS server"
echo "Files created:"
echo "  - development/mcp_server/ssl/cert.pem"
echo "  - development/mcp_server/ssl/key.pem"