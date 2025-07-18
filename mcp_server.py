#!/usr/bin/env python3
"""
MCP Server Entry Point
This is a simple wrapper that runs the unified MCP server in MCP mode.
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the unified server
from unified_mcp_server import main

if __name__ == "__main__":
    main()
