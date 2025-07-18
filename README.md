<div align="center">

# 🚀 Personal MCP Server

*A unified Model Context Protocol server that bridges AI assistants with your development workflow*

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![MCP](https://img.shields.io/badge/MCP-Protocol-purple.svg)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](Dockerfile)

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [API](#-api-reference) • [Deployment](#-deployment) • [Contributing](#-contributing)

</div>

---

## ✨ Features

### 🤖 **MCP Protocol Support**
Perfect integration with AI assistants like Claude and Cline, providing:

- 🔧 **Git Operations** - Complete repository management with branch operations
- 📁 **File Management** - Read, write, search, and batch operations  
- 💾 **Context Storage** - Persistent memory with full-text search capabilities
- 🏗️ **Project Templates** - Quick scaffolding for Python, React, FastAPI, and more
- 🤖 **Automatic Context Logging** - Every interaction automatically logged and organized
- 🔍 **Project Discovery** - Automatic detection and cataloging of all your projects

### 🌐 **HTTP API Support**
RESTful endpoints for web applications:

- 📝 **Context Management** - Add, retrieve, and organize context streams
- 📊 **Repository Updates** - Specialized git workflow endpoints
- 🔍 **Health Monitoring** - Server status and performance metrics
- 🚀 **Production Ready** - CORS support, error handling, and comprehensive logging

### 🚢 **Deployment Ready**
Multiple deployment options with full configuration:

- 🐳 **Docker** - Production-ready containerization with health checks
- ☁️ **Cloud Platforms** - Heroku, Railway, Render, DigitalOcean, GCP, AWS
- 🔧 **Development** - Auto-reload, comprehensive testing, and debugging tools

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

### Development Installation

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .

# Type checking
mypy .
```

---

## 💡 Usage

### 🔌 **MCP Mode** (AI Assistant Integration)

Perfect for Claude, Cline and other MCP-compatible AI assistants:

```bash
python3 mcp_server.py
```

**Claude Desktop Configuration:**
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

- `list_git_repos` - Discover all repositories in common directories
- `get_repo_status` - Detailed repository information with status
- `git_command` - Execute any git command safely
- `git_branch` - Branch management (list, create, switch, delete)
- `git_diff` - View changes, diffs, and staged content
- `git_commit` - Create commits with automatic staging options

</details>

<details>
<summary><strong>📁 File Management</strong></summary>

- `read_file` - Read file contents with encoding detection
- `write_file` - Create or update files with directory creation
- `list_directory` - Browse directory contents with filtering
- `search_files` - Find files by name or content with regex support
- `batch_file_operation` - Bulk operations (copy, move, delete, rename)

</details>

<details>
<summary><strong>💾 Context & Memory</strong></summary>

- `add_context` - Store information in persistent context streams
- `get_context` - Retrieve stored context with optional limits
- `search_context` - Full-text search with date and stream filters
- **Automatic Logging** - Every tool interaction automatically logged
- **Session Tracking** - Unique session IDs for interaction history

</details>

<details>
<summary><strong>🏗️ Project Templates</strong></summary>

- `create_project_template` - Scaffold new projects with best practices
- **Supported Types**: Python, JavaScript, React, FastAPI, MCP Server
- **Features**: Git initialization, proper .gitignore, README templates
- **Smart Detection**: Automatic project type detection for existing projects

</details>

---

## 🤖 Automatic Context Features

### 📊 **Interaction Logging**
Every MCP tool call is automatically logged with:
- Tool name and sanitized arguments
- Execution time and success/failure status
- Result summaries (large content truncated)
- Error messages and debugging information

### 🔍 **Project Discovery**
On startup, the server automatically:
- Scans Documents and Desktop for git repositories
- Detects project types (Python, JavaScript, React, Vue, etc.)
- Catalogs technologies and configuration files
- Creates comprehensive project profiles

### 📋 **Context Streams**
Organized context storage:
- `session_[ID]` - Complete interaction history
- `project_[name]` - Individual project discoveries
- `tool_[name]` - Significant operations (commits, file writes)
- `system_overview` - Server initialization info
- `projects_overview` - All discovered projects summary

---

## 📡 API Reference

### Context Management
```http
POST   /add_context           # Store new context
GET    /get_context?target=ID # Retrieve context by stream ID
DELETE /delete_context?target=ID # Remove context stream
GET    /status                # Server health and statistics
```

### Repository Operations
```http
POST   /repos/update_context  # Repository-specific context updates
```

### System Information
```http
GET    /                      # Basic server information
GET    /status                # Detailed server status with metrics
```

**Example Status Response:**
```json
{
  "status": "ok",
  "stored_contexts": ["session_abc123", "project_my-app"],
  "total_items": 42,
  "server_uptime": "2:30:15",
  "mcp_tools": 15,
  "mcp_resources": 6
}
```

---

## 🚢 Deployment

### 🐳 **Docker Deployment**

```bash
# Build and run with Docker
docker build -t personal-mcp-server .
docker run -p 8000:8000 -v $(pwd)/context_data.json:/app/context_data.json personal-mcp-server

# Or use Docker Compose
docker-compose up --build

# Production with nginx
docker-compose --profile production up -d
```

### ☁️ **Cloud Deployment**

#### Heroku
```bash
heroku create your-mcp-server
git push heroku main
```

#### Railway
```bash
railway login
railway init
railway up
```

#### Render, DigitalOcean, GCP, AWS
See our comprehensive [Deployment Guide](DEPLOYMENT.md) for detailed instructions.

### 🔧 **Environment Variables**
- `PORT` - Server port (default: 8000)
- `PYTHONUNBUFFERED` - Enable immediate output
- `PYTHONDONTWRITEBYTECODE` - Prevent .pyc files

---

## 📁 Project Structure

```
Personal-MCP-Server/
├── 🚀 mcp_server.py           # MCP mode entry point
├── 🌐 unified_mcp_server.py   # Main server implementation
├── 📋 requirements.txt        # Python dependencies
├── 📦 setup.py               # Package configuration
├── 💾 context_data.json       # Persistent context storage
├── 🐳 Dockerfile             # Container configuration
├── 🚢 docker-compose.yml     # Multi-service setup
├── 📖 README.md              # This documentation
├── 🚀 DEPLOYMENT.md          # Deployment guide
├── 🤝 CONTRIBUTING.md        # Contribution guidelines
├── 📄 LICENSE                # MIT license
├── 📋 Procfile               # Heroku deployment config
├── 📚 UNIFIED_SERVER_GUIDE.md # Additional server documentation
└── 🧪 tests/                 # Test suite
    ├── __init__.py
    └── test_context_store.py
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_context_store.py

# Test with different Python versions
tox
```

---

## 🔧 Development

### Local Development
```bash
# Run with auto-reload
uvicorn unified_mcp_server:app --reload --host 0.0.0.0 --port 8000

# Run MCP mode with debugging
python3 mcp_server.py

# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

### Development Tools
- **Black** - Code formatting
- **flake8** - Linting
- **mypy** - Type checking
- **pytest** - Testing framework
- **coverage** - Test coverage reporting

---

## 📊 Monitoring & Health Checks

### Health Endpoint
```bash
curl http://localhost:8000/status
```

### Docker Health Checks
Built-in health checks monitor:
- Server responsiveness
- Context storage functionality
- MCP tool availability
- Resource accessibility

### Logging
Comprehensive logging with:
- Structured log format
- Error tracking and debugging
- Performance metrics
- Interaction history

---

## 🔒 Security & Best Practices

### Security Features
- **Content Sanitization** - Large content automatically truncated
- **Input Validation** - Pydantic models for all API inputs
- **Error Handling** - Graceful error responses without data leaks
- **CORS Configuration** - Configurable cross-origin policies

### Production Considerations
- Use environment variables for sensitive configuration
- Enable HTTPS in production deployments
- Configure appropriate CORS origins
- Set up monitoring and alerting
- Regular backups of context data

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contribution Steps
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run the test suite (`pytest`)
5. Format your code (`black .`)
6. Submit a pull request

### Development Setup
```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/personal-mcp-server.git
cd personal-mcp-server

# Install development dependencies
pip install -e ".[dev]"

# Run tests to ensure everything works
pytest
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **MCP Protocol** - [Model Context Protocol](https://modelcontextprotocol.io)
- **FastAPI** - Modern, fast web framework for building APIs
- **Claude & Cline** - AI assistants that inspired this integration
- **Contributors** - Everyone who has contributed to this project

---

<div align="center">

**Built with ❤️ by [Liad Matusovsky](https://github.com/LiadMatus)**

*Empowering AI assistants with powerful development tools*

⭐ **Star this repo if you find it useful!** ⭐

</div>
