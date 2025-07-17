#!/usr/bin/env python3
"""
Test script for the Personal MCP Server
Tests basic functionality without requiring full MCP client setup
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def test_mcp_server():
    """Test the MCP server functionality"""
    print("🧪 Testing Personal MCP Server")
    print("=" * 40)
    
    try:
        # Import the server module
        from mcp_server import (
            find_git_repositories, 
            get_repo_info, 
            PROJECTS_DIR, 
            DESKTOP_DIR,
            handle_list_tools,
            handle_list_resources
        )
        
        print("✅ Successfully imported MCP server modules")
        
        # Test git repository discovery
        print("\n🔍 Testing git repository discovery...")
        repos = []
        for search_dir in [PROJECTS_DIR, DESKTOP_DIR]:
            if search_dir.exists():
                found_repos = find_git_repositories(search_dir)
                repos.extend(found_repos)
        
        if repos:
            print(f"✅ Found {len(repos)} git repositories:")
            for repo in repos[:5]:  # Show first 5
                print(f"   - {repo.name} ({repo})")
                
                # Test getting repo info
                repo_info = get_repo_info(repo)
                if "error" not in repo_info:
                    print(f"     ✅ Successfully read repo info")
                else:
                    print(f"     ⚠️  Repo info error: {repo_info['error']}")
        else:
            print("⚠️  No git repositories found in search directories")
        
        # Test tools listing
        print("\n🔧 Testing tools listing...")
        tools = await handle_list_tools()
        print(f"✅ Found {len(tools)} available tools:")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")
        
        # Test resources listing
        print("\n📚 Testing resources listing...")
        resources = await handle_list_resources()
        print(f"✅ Found {len(resources)} available resources:")
        for resource in resources:
            print(f"   - {resource.name}: {resource.description}")
        
        print("\n🎉 All tests passed! MCP server is working correctly.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all dependencies are installed: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def main():
    """Main test function"""
    success = await test_mcp_server()
    
    if success:
        print("\n✅ MCP Server is ready for use!")
        print("\nTo connect to Cline:")
        print("1. Add this configuration to your Cline MCP settings:")
        print(json.dumps({
            "mcpServers": {
                "personal-mcp-server": {
                    "command": "python3",
                    "args": ["mcp_server.py"],
                    "cwd": str(Path.cwd())
                }
            }
        }, indent=2))
        print("\n2. Restart Cline/VSCode")
        print("3. The server should appear in your available MCP servers")
    else:
        print("\n❌ MCP Server has issues. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
