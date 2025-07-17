#!/usr/bin/env python3
"""
Setup script for Personal MCP Server
Installs dependencies and helps configure the server for use with Cline
"""

import json
import os
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    # Check if pip is available
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("❌ pip is not available. Please install pip first.")
        return False
    
    # Install requirements
    return run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing requirements"
    )

def test_mcp_server():
    """Test if the MCP server can start"""
    print("🧪 Testing MCP server...")
    
    try:
        # Try to import the required modules
        import mcp
        import git
        import pathspec
        print("✅ All required modules are available")
        
        # Try to run the server for a few seconds
        process = subprocess.Popen(
            [sys.executable, "mcp_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit and then terminate
        import time
        time.sleep(2)
        process.terminate()
        
        stdout, stderr = process.communicate(timeout=5)
        
        if "personal-mcp-server" in stderr or "personal-mcp-server" in stdout:
            print("✅ MCP server starts successfully")
            return True
        else:
            print("⚠️  MCP server may have issues:")
            if stderr:
                print(f"   stderr: {stderr[:200]}...")
            return False
            
    except ImportError as e:
        print(f"❌ Missing required module: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False

def find_cline_config():
    """Find Cline configuration directory"""
    possible_paths = [
        Path.home() / ".config" / "cline",
        Path.home() / "Library" / "Application Support" / "Cline",
        Path.home() / "AppData" / "Roaming" / "Cline",
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None

def setup_cline_config():
    """Setup Cline MCP configuration"""
    print("🔧 Setting up Cline MCP configuration...")
    
    cline_config_dir = find_cline_config()
    
    if not cline_config_dir:
        print("⚠️  Could not find Cline configuration directory.")
        print("   Please manually add the MCP server configuration to Cline.")
        print("   Configuration to add:")
        print(json.dumps({
            "mcpServers": {
                "personal-mcp-server": {
                    "command": "python",
                    "args": ["mcp_server.py"],
                    "cwd": str(Path.cwd())
                }
            }
        }, indent=2))
        return False
    
    config_file = cline_config_dir / "mcp_servers.json"
    current_dir = str(Path.cwd())
    
    # Load existing config or create new one
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except:
            config = {"mcpServers": {}}
    else:
        config = {"mcpServers": {}}
    
    # Add our server
    config["mcpServers"]["personal-mcp-server"] = {
        "command": "python3",
        "args": ["mcp_server.py"],
        "cwd": current_dir
    }
    
    # Save config
    try:
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ MCP server configuration added to {config_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to write configuration: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Personal MCP Server Setup")
    print("=" * 40)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Test server
    if not test_mcp_server():
        print("⚠️  Server test had issues, but continuing...")
    
    # Setup Cline config
    setup_cline_config()
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Restart Cline/VSCode")
    print("2. The 'personal-mcp-server' should appear in your available MCP servers")
    print("3. You can now use tools like:")
    print("   - list_git_repos: List all your git repositories")
    print("   - get_repo_status: Get status of a specific repository")
    print("   - git_command: Execute git commands")
    print("   - read_file: Read any file on your system")
    print("   - write_file: Write files")
    print("   - list_directory: List directory contents")
    print("   - search_files: Search for files by name or content")
    print("\n📚 Resources available:")
    print("   - Git repositories in Documents and Desktop")
    print("   - Directory listings for Documents, Desktop, Downloads")

if __name__ == "__main__":
    main()
