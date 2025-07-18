#!/bin/bash

echo "🔄 Restarting Claude Desktop to apply MCP configuration..."

# Kill Claude Desktop processes
pkill -f "Claude" 2>/dev/null || true

# Wait a moment
sleep 2

# Clear any remaining cache files
find ~/Library/Logs/Claude -type f -delete 2>/dev/null || true
find ~/Library/Caches/Claude -type f -delete 2>/dev/null || true

echo "✅ Claude Desktop processes stopped and cache cleared"
echo "📱 Please manually restart Claude Desktop now"
echo ""
echo "🔍 To verify the MCP server is working:"
echo "   1. Open Claude Desktop"
echo "   2. Look for the MCP server connection indicator"
echo "   3. Try asking: 'List my git repositories'"
echo ""
echo "📋 Current MCP Configuration:"
echo "   Server: personal-mcp-server"
echo "   Command: /Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
echo "   Script: /Users/liadmatus/Documents/Personal-MCP-Server/mcp_server.py (absolute path)"
echo "   ✅ Fixed: Using absolute path instead of working directory"
