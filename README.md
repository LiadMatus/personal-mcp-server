# 🧠 Personal MCP Server

This is a comprehensive **Model Context Protocol (MCP)** server that provides access to your git repositories and personal files. It includes both a FastAPI-based context storage server and a proper MCP server that integrates with Cline and other MCP clients.

> Think of it as your developer brain: access to all your projects, repositories, and files through a unified interface with powerful tools for git operations, file management, and context storage.

## 🎯 Two Server Options

### 1. **MCP Server** (Recommended for Cline)
- **File**: `mcp_server.py`
- **Purpose**: Direct integration with Cline via MCP protocol
- **Features**: Git repository access, file operations, directory browsing
- **Usage**: Connects directly to Cline as an MCP server

### 2. **FastAPI Context Server**
- **File**: `personal_mcp_server.py` 
- **Purpose**: HTTP API for context storage and retrieval
- **Features**: Persistent context storage, REST API endpoints
- **Usage**: Standalone web service for context management

---

## ⚙️ Features

- ✅ **Persistent Storage**: Context data survives server restarts via JSON file storage
- ✅ **Input Validation**: Robust validation with proper error handling
- ✅ **Comprehensive Logging**: Detailed logging for debugging and monitoring
- ✅ **CORS Support**: Cross-origin requests enabled for web integration
- ✅ **Context Management**: Add, retrieve, and delete context streams
- ✅ **Query Limits**: Retrieve recent items with configurable limits
- ✅ **Enhanced Status**: Detailed server status with uptime and statistics
- ✅ **OpenAPI Documentation**: Auto-generated API docs at `/docs`
- ✅ **Type Safety**: Full Pydantic models with proper type hints
- ✅ **Error Handling**: Graceful error responses with proper HTTP status codes

---

## 🚀 API Endpoints

### `POST /add_context`

Adds a context item to a memory stream with validation and persistence.

#### Request:
```json
{
  "id": "chat_context_live",
  "content": "Just refactored the auth service to use JWTs.",
  "metadata": {
    "type": "task",
    "source": "terminal",
    "priority": "high"
  }
}
```

#### Response:
```json
{
  "status": "added",
  "id": "chat_context_live",
  "total_items": 15
}
```

---

### `GET /get_context?target=ID&limit=N`

Retrieves context items for a given target ID with optional limiting.

#### Parameters:
- `target` (required): Context stream ID
- `limit` (optional): Maximum number of recent items to return (1-1000)

#### Response:
```json
{
  "messages": [
    {
      "timestamp": "2025-01-17T20:30:45.123456+00:00",
      "role": "system",
      "content": "Just refactored the auth service to use JWTs.",
      "metadata": {
        "type": "task",
        "source": "terminal",
        "priority": "high"
      }
    }
  ]
}
```

---

### `DELETE /delete_context?target=ID`

Deletes all context items for a given target ID.

#### Parameters:
- `target` (required): Context stream ID to delete

#### Response:
```json
{
  "status": "deleted",
  "id": "chat_context_live"
}
```

---

### `POST /repos/update_context`

Specialized endpoint to log repository-related updates with automatic prefixing.

#### Request:
```json
{
  "id": "diy-assistant-repo",
  "content": "Updated README and added Supabase client.",
  "metadata": {
    "branch": "main",
    "files": ["README.md", "supabase.ts"],
    "commit": "abc123"
  }
}
```

#### Response:
```json
{
  "status": "added",
  "id": "repo_diy-assistant-repo",
  "total_items": 8
}
```

---

### `GET /status`

Returns comprehensive server health check and context statistics.

#### Response:
```json
{
  "status": "ok",
  "stored_contexts": ["chat_context_live", "repo_diy-assistant-repo"],
  "total_items": 23,
  "server_uptime": "2:15:30"
}
```

---

### `GET /`

Root endpoint with basic server information and navigation links.

---

### `GET /docs`

Interactive OpenAPI documentation (Swagger UI) for testing endpoints.

---

## 🚀 Quick Setup for Cline Integration

### Automatic Setup (Recommended)

Run the setup script to automatically install dependencies and configure Cline:

```bash
python setup_mcp.py
```

This will:
- Install all required Python dependencies
- Test the MCP server functionality
- Automatically configure Cline to use the MCP server
- Provide next steps for usage

### Manual Setup

1. **Install Dependencies:**
```bash
pip install -r requirements.txt
```

2. **Test the MCP Server:**
```bash
python mcp_server.py
```

3. **Configure Cline:**
Add this configuration to your Cline MCP servers settings:
```json
{
  "mcpServers": {
    "personal-mcp-server": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "/Users/liadmatus/Documents/Personal-MCP-Server"
    }
  }
}
```

4. **Restart Cline/VSCode**

---

## 🔧 MCP Server Tools & Resources

### Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_git_repos` | List all git repositories in common directories | `search_path` (optional) |
| `get_repo_status` | Get detailed status of a specific git repository | `repo_name` (required) |
| `git_command` | Execute a git command in a specific repository | `repo_name`, `command` (required) |
| `read_file` | Read the contents of any file | `file_path` (required) |
| `write_file` | Write content to a file | `file_path`, `content` (required) |
| `list_directory` | List contents of a directory | `directory_path` (required), `include_hidden` (optional) |
| `search_files` | Search for files by name or content | `search_path`, `pattern` (required), `search_content` (optional) |

### Available Resources

| Resource | Description | URI Pattern |
|----------|-------------|-------------|
| Git Repositories | Information about your git repos | `git://repo/{repo_name}` |
| Documents Directory | Files in your Documents folder | `file://directory/documents` |
| Desktop Directory | Files in your Desktop folder | `file://directory/desktop` |
| Downloads Directory | Files in your Downloads folder | `file://directory/downloads` |

### Example Usage in Cline

Once connected, you can ask Cline to:

- **"List all my git repositories"** - Uses `list_git_repos` tool
- **"Show me the status of my project-name repository"** - Uses `get_repo_status` tool  
- **"Run git status in my project-name repo"** - Uses `git_command` tool
- **"Read the README file from /path/to/file"** - Uses `read_file` tool
- **"Search for Python files in my Documents"** - Uses `search_files` tool
- **"What files are in my Desktop?"** - Uses `list_directory` tool

---

## 🛠️ Local Development (FastAPI Server)

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the server:

```bash
uvicorn personal_mcp_server:app --reload
```

Or run directly:

```bash
python personal_mcp_server.py
```

The server will start on `http://localhost:8000` with:
- API documentation at `http://localhost:8000/docs`
- Status endpoint at `http://localhost:8000/status`

---

## ☁️ Deployment

### Railway / Fly.io

Deploy using the included configuration files:

- `personal_mcp_server.py` (main FastAPI app)
- `Procfile` (process configuration)
- `requirements.txt` (dependencies)

**Procfile:**
```txt
web: uvicorn personal_mcp_server:app --host 0.0.0.0 --port $PORT
```

### Environment Variables

- `PORT`: Server port (default: 8000)

### Data Persistence

Context data is automatically saved to `context_data.json` in the working directory. This file will be created on first use and updated on every context modification.

---

## 🧩 Use Cases

- **Real-time LLM assistant memory** with persistent context
- **Task/agent sync across sessions** with reliable storage
- **Developer journaling via CLI hooks** with structured logging
- **Personal LangChain-style runtime** with context management
- **Project documentation** with automatic timestamping
- **Code review context** with metadata tracking

---

## 🧠 Context Organization Tips

Structure your context streams with consistent naming:

```
chat_context_live          # Live chat sessions
repo_project_name          # Repository updates
task_2025_resume_refactor  # Specific tasks
project_agent_kernel       # Project-specific context
debug_auth_service         # Debugging sessions
meeting_2025_01_17         # Meeting notes
```

Use metadata for enhanced organization:
```json
{
  "type": "task|repo|chat|debug|meeting",
  "priority": "low|medium|high|urgent",
  "source": "terminal|ide|manual|webhook",
  "tags": ["backend", "auth", "refactor"]
}
```

---

## 📊 Monitoring & Debugging

### Logging

The server provides comprehensive logging:
- INFO: General operations and context additions
- ERROR: Failed operations and exceptions
- DEBUG: Detailed data operations

### Health Checks

Use the `/status` endpoint to monitor:
- Server uptime
- Number of active context streams
- Total stored items
- Overall system health

---

## 🔒 Security Considerations

**Current Implementation:**
- No authentication (suitable for local/private networks)
- CORS enabled for all origins
- Input validation and sanitization
- Error handling without sensitive data exposure

**For Production:**
- Add API key authentication
- Configure CORS for specific origins
- Implement rate limiting
- Use HTTPS
- Regular data backups

---

## 📡 Roadmap

### Planned Enhancements
- 🔐 **Authentication**: API key and JWT support
- 🗄️ **Database Backend**: PostgreSQL/SQLite integration
- 🔍 **Search & Filtering**: Full-text search and advanced filtering
- 📊 **Analytics Dashboard**: Web UI for context visualization
- 🔄 **Webhooks**: Real-time notifications for context updates
- 📦 **Backup/Export**: Data export and backup utilities
- 🏷️ **Tagging System**: Enhanced metadata and tagging
- 📈 **Metrics**: Performance monitoring and usage analytics

### Optional Integrations
- Supabase/Firebase backend
- Embedding & semantic search layer
- Slack/Discord notifications
- GitHub integration for automatic repo updates

---

## 🚀 Performance

- **Startup**: Fast initialization with automatic data loading
- **Storage**: Efficient JSON-based persistence
- **Memory**: Optimized in-memory operations
- **Scalability**: Suitable for personal to small team usage

---

Built to supercharge your personal coding workflow with enterprise-grade reliability.
