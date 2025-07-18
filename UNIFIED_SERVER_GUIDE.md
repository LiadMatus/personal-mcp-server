# 🚀 Unified Personal MCP Server - Complete Guide

Your Personal MCP Server has been successfully merged into a single unified server that handles both MCP protocol for Cline integration and HTTP API for web applications.

## 📁 Project Structure

### Main Files:
- **`unified_mcp_server.py`** - ⭐ **Main unified server** (use this!)
- **`test_unified_mcp.py`** - Test suite for the unified server
- **`mcp_config.json`** - Configuration for Cline integration
- **`requirements.txt`** - All dependencies
- **`context_data.json`** - Persistent context storage

### Legacy Files (can be removed):
- `personal_mcp_server.py` - Old FastAPI-only server
- `mcp_server.py` - Old MCP-only server
- `test_mcp.py` - Old MCP test script

## 🎯 How to Use

### For Cline Integration (MCP Protocol):
```bash
python3 unified_mcp_server.py
```

### For Web Applications (HTTP API):
```bash
python3 unified_mcp_server.py --http
```
Then visit: http://localhost:8000/docs for API documentation

## 🔧 Cline Configuration

Add this to your Cline MCP settings:

```json
{
  "mcpServers": {
    "unified-personal-mcp-server": {
      "command": "python3",
      "args": ["unified_mcp_server.py"],
      "cwd": "/Users/liadmatus/Documents/Personal-MCP-Server"
    }
  }
}
```

## 🛠️ Available Tools (MCP)

### Core Tools:
| Tool | Description | Example Usage |
|------|-------------|---------------|
| `list_git_repos` | List all git repositories | "Show me all my git projects" |
| `get_repo_status` | Get detailed repo status | "What's the status of my Personal-MCP-Server repo?" |
| `git_command` | Execute git commands | "Run git log in my project" |
| `read_file` | Read file contents | "Read the README from my project" |
| `write_file` | Write/create files | "Create a new config file" |
| `list_directory` | List directory contents | "Show me what's in my Documents folder" |
| `search_files` | Search files by name/content | "Find all Python files in my projects" |
| `add_context` | Store context data | "Remember this information" |
| `get_context` | Retrieve stored context | "What did I save about this project?" |

### Advanced Git Tools:
| Tool | Description | Example Usage |
|------|-------------|---------------|
| `git_branch` | Branch operations (list, create, switch, delete) | "Create a new feature branch" |
| `git_diff` | Show git diff for files or commits | "Show me what changed in this file" |
| `git_commit` | Create commits with staged changes | "Commit my changes with a message" |

### Advanced File Tools:
| Tool | Description | Example Usage |
|------|-------------|---------------|
| `batch_file_operation` | Batch operations on multiple files | "Copy all .py files to backup folder" |
| `create_project_template` | Create new projects from templates | "Create a new React project" |

### Context Intelligence:
| Tool | Description | Example Usage |
|------|-------------|---------------|
| `search_context` | Search through stored context with filters | "Find all context about React projects" |

## 📚 Available Resources (MCP)

- **Git Repositories:** Access to all your git repos in Documents and Desktop
- **Documents Directory:** Browse your Documents folder
- **Desktop Directory:** Browse your Desktop
- **Downloads Directory:** Browse your Downloads folder

## 🌐 HTTP API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Server information |
| `/status` | GET | Server health and statistics |
| `/add_context` | POST | Add context to storage |
| `/get_context` | GET | Retrieve context |
| `/delete_context` | DELETE | Delete context stream |
| `/repos/update_context` | POST | Repository-specific context |
| `/docs` | GET | Interactive API documentation |

## 🧪 Testing

Run the comprehensive test suite:
```bash
python3 test_unified_mcp.py
```

This tests both MCP functionality and HTTP API endpoints.

## 📊 Current Status

✅ **3 Git Repositories Discovered:**
- Personal-MCP-Server
- my-diy-assistant
- mcp-server

✅ **15 MCP Tools Available** (Enhanced!)
✅ **6 MCP Resources Available**
✅ **Full HTTP API with FastAPI**
✅ **Persistent Context Storage**
✅ **Advanced Git Integration with GitPython**
✅ **File System Access with Security**
✅ **Project Template Generation**
✅ **Batch File Operations**
✅ **Context Search & Intelligence**

## 🔄 Migration from Old Servers

If you were using the old servers:

1. **Stop any running old servers**
2. **Update Cline configuration** to use `unified_mcp_server.py`
3. **Use the unified server** for all functionality
4. **Optional:** Remove old server files to avoid confusion

## 🚀 Next Steps

1. **Restart Cline/VSCode** to load the new unified server
2. **Test the connection** by asking Cline to list your repositories
3. **Explore the tools** - try different file and git operations
4. **Use HTTP API** for web integrations if needed

## 🔧 Customization

To modify search directories or add new functionality, edit `unified_mcp_server.py`:

- **Change search paths:** Modify `PROJECTS_DIR`, `DESKTOP_DIR`, `DOWNLOADS_DIR`
- **Add new tools:** Add to the `handle_list_tools()` function
- **Add new resources:** Add to the `handle_list_resources()` function
- **Modify ignore patterns:** Update `DEFAULT_IGNORE_PATTERNS`

## 📞 Troubleshooting

### Server Not Starting:
- Check that all dependencies are installed: `pip3 install -r requirements.txt`
- Verify Python 3.8+ is being used: `python3 --version`

### Cline Not Connecting:
- Ensure Cline is restarted after configuration changes
- Check that the path in configuration is correct
- Verify `python3` is available in your PATH

### HTTP API Issues:
- Check if port 8000 is available
- Look for error messages in the console output
- Try a different port: `PORT=8001 python3 unified_mcp_server.py --http`

---

🎉 **Your Unified Personal MCP Server is ready to supercharge your development workflow!**
