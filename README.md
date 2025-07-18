<div align="center">

# 🚀 Personal MCP Server

*A unified Model Context Protocol server that bridges AI assistants with your development workflow*

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![MCP](https://img.shields.io/badge/MCP-Protocol-purple.svg)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [API](#-api-reference) • [Contributing](#-contributing)

</div>

---

## ✨ Features

### 🤖 **MCP Protocol Support**
Perfect integration with AI assistants like Cline, providing:

- 🔧 **Git Operations** - Complete repository management
- 📁 **File Management** - Read, write, search, and batch operations  
- 💾 **Context Storage** - Persistent memory with search capabilities
- 🏗️ **Project Templates** - Quick scaffolding for new projects

### 🌐 **HTTP API Support**
RESTful endpoints for web applications:

- 📝 **Context Management** - Add, retrieve, and organize context
- 📊 **Repository Updates** - Specialized git workflow endpoints
- 🔍 **Health Monitoring** - Server status and performance metrics

---

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- Git (for repository operations)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/LiadMatus/personal-mcp-server.git
cd personal-mcp-server

# Install dependencies
pip install -r requirements.txt

# Run in MCP mode (for AI assistants)
python3 mcp_server.py

# Or run in HTTP mode (for web applications)
python3 unified_mcp_server.py --http
```

---

## 💡 Usage

### 🔌 **MCP Mode** (AI Assistant Integration)

Perfect for Cline and other MCP-compatible AI assistants:

```bash
python3 mcp_server.py
```

**Cline Configuration:**
```json
{
  "mcpServers": {
    "personal-mcp-server": {
      "command": "python3",
      "args": ["mcp_server.py"],
      "cwd": "/path/to/Personal-MCP-Server",
      "type": "stdio"
    }
  }
}
```

### 🌐 **HTTP Mode** (Web API)

For web applications and direct API access:

```bash
python3 unified_mcp_server.py --http
```

- 🔗 **API Base**: `http://localhost:8000`
- 📚 **Interactive Docs**: `http://localhost:8000/docs`
- 🔍 **Health Check**: `http://localhost:8000/status`

---

## 🛠️ Available Tools

<details>
<summary><strong>🔧 Git Operations</strong></summary>

- `list_git_repos` - Discover all repositories
- `get_repo_status` - Detailed repository information
- `git_command` - Execute any git command
- `git_branch` - Branch management (create, switch, delete)
- `git_diff` - View changes and diffs
- `git_commit` - Create commits with messages

</details>

<details>
<summary><strong>📁 File Management</strong></summary>

- `read_file` - Read file contents
- `write_file` - Create or update files
- `list_directory` - Browse directory contents
- `search_files` - Find files by name or content
- `batch_file_operation` - Bulk file operations

</details>

<details>
<summary><strong>💾 Context & Memory</strong></summary>

- `add_context` - Store information persistently
- `get_context` - Retrieve stored context
- `search_context` - Full-text search with filters

</details>

<details>
<summary><strong>🏗️ Project Templates</strong></summary>

- `create_project_template` - Scaffold new projects
- **Supported**: Python, JavaScript, React, FastAPI, MCP Server

</details>

---

## 📡 API Reference

### Context Management
```http
POST   /add_context      # Store new context
GET    /get_context      # Retrieve context by ID
DELETE /delete_context   # Remove context stream
```

### Repository Operations
```http
POST   /repos/update_context  # Repository-specific updates
```

### System
```http
GET    /status          # Server health and statistics
GET    /               # Basic server information
```

---

## 📁 Project Structure

```
Personal-MCP-Server/
├── 🚀 mcp_server.py           # MCP mode entry point
├── 🌐 unified_mcp_server.py   # Main server implementation
├── 📋 requirements.txt        # Python dependencies
├── 💾 context_data.json       # Persistent storage
├── 📖 README.md              # This documentation
├── 🚢 Procfile               # Deployment config
└── 📚 UNIFIED_SERVER_GUIDE.md # Detailed guide
```

---

## 🔧 Development

### Local Development
```bash
# Run with auto-reload
python3 unified_mcp_server.py --http

# The server will automatically reload on code changes
```

### Environment Variables
- `PORT` - Server port (default: 8000)
- `DEBUG` - Enable debug mode

---

## 🚀 Deployment

### Heroku
The project includes a `Procfile` for easy Heroku deployment:

```bash
git push heroku main
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "unified_mcp_server.py", "--http"]
```

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ by [Liad Matusovsky](https://github.com/LiadMatus)**

*Empowering AI assistants with powerful development tools*

</div>
