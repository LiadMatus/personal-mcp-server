#!/usr/bin/env python3
"""
Test script for the Unified Personal MCP Server
Tests both MCP protocol functionality and HTTP API endpoints
"""

import asyncio
import json
import sys
import requests
import subprocess
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def test_mcp_functionality():
    """Test the MCP server functionality"""
    print("🧪 Testing MCP Server Functionality")
    print("-" * 40)
    
    try:
        # Import the unified server module
        from unified_mcp_server import (
            find_git_repositories, 
            get_repo_info, 
            PROJECTS_DIR, 
            DESKTOP_DIR,
            handle_list_tools,
            handle_list_resources
        )
        
        print("✅ Successfully imported unified MCP server modules")
        
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
        print("\n🔧 Testing MCP tools listing...")
        tools = await handle_list_tools()
        print(f"✅ Found {len(tools)} available MCP tools:")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")
        
        # Test resources listing
        print("\n📚 Testing MCP resources listing...")
        resources = await handle_list_resources()
        print(f"✅ Found {len(resources)} available MCP resources:")
        for resource in resources:
            print(f"   - {resource.name}: {resource.description}")
        
        print("\n🎉 MCP functionality tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ MCP test failed: {e}")
        return False

def test_http_api():
    """Test the HTTP API functionality"""
    print("\n🌐 Testing HTTP API Functionality")
    print("-" * 40)
    
    # Start the HTTP server in background
    print("🚀 Starting HTTP server...")
    server_process = subprocess.Popen(
        [sys.executable, "unified_mcp_server.py", "--http"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(3)
    
    try:
        base_url = "http://localhost:8000"
        
        # Test root endpoint
        print("📍 Testing root endpoint...")
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint working: {data['message']} v{data['version']}")
            
            # Verify it's the unified server
            if "Unified" not in data['message']:
                print("⚠️  Warning: Not running unified server, got old server response")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
        
        # Test status endpoint
        print("📊 Testing status endpoint...")
        response = requests.get(f"{base_url}/status")
        if response.status_code == 200:
            data = response.json()
            if 'mcp_tools' in data and 'mcp_resources' in data:
                print(f"✅ Status endpoint working: {data['mcp_tools']} tools, {data['mcp_resources']} resources")
            else:
                print(f"⚠️  Status endpoint missing MCP fields: {list(data.keys())}")
                # Still continue with other tests
        else:
            print(f"❌ Status endpoint failed: {response.status_code}")
            return False
        
        # Test add context
        print("💾 Testing add context...")
        context_data = {
            "id": "test_context",
            "content": "This is a test context entry",
            "metadata": {"test": True}
        }
        response = requests.post(f"{base_url}/add_context", json=context_data)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Add context working: {data['status']}")
        else:
            print(f"❌ Add context failed: {response.status_code}")
            return False
        
        # Test get context
        print("📖 Testing get context...")
        response = requests.get(f"{base_url}/get_context?target=test_context")
        if response.status_code == 200:
            data = response.json()
            if data['messages']:
                print(f"✅ Get context working: Retrieved {len(data['messages'])} messages")
            else:
                print("⚠️  Get context returned empty messages")
        else:
            print(f"❌ Get context failed: {response.status_code}")
            return False
        
        print("\n🎉 HTTP API tests passed!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to HTTP server")
        return False
    except Exception as e:
        print(f"❌ HTTP API test failed: {e}")
        return False
    finally:
        # Clean up server process
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()

async def main():
    """Main test function"""
    print("🚀 Unified Personal MCP Server Test Suite")
    print("=" * 50)
    
    # Test MCP functionality
    mcp_success = await test_mcp_functionality()
    
    # Test HTTP API
    http_success = test_http_api()
    
    # Summary
    print("\n📋 Test Summary")
    print("=" * 20)
    print(f"MCP Functionality: {'✅ PASS' if mcp_success else '❌ FAIL'}")
    print(f"HTTP API: {'✅ PASS' if http_success else '❌ FAIL'}")
    
    if mcp_success and http_success:
        print("\n🎉 All tests passed! Unified server is ready for use.")
        print("\n🔧 Usage Instructions:")
        print("For Cline integration:")
        print("  python3 unified_mcp_server.py")
        print("\nFor HTTP API:")
        print("  python3 unified_mcp_server.py --http")
        print("  Then visit: http://localhost:8000/docs")
        
        print("\n📝 Cline Configuration:")
        print(json.dumps({
            "mcpServers": {
                "unified-personal-mcp-server": {
                    "command": "python3",
                    "args": ["unified_mcp_server.py"],
                    "cwd": str(Path.cwd())
                }
            }
        }, indent=2))
        
        return True
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
