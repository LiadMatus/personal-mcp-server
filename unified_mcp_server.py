#!/usr/bin/env python3
"""
Unified Personal MCP Server
Combines MCP protocol support for Cline with FastAPI HTTP endpoints for web integrations
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from contextlib import asynccontextmanager

# FastAPI imports
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
import uvicorn

# MCP imports
import git
from git import Repo, InvalidGitRepositoryError
import pathspec
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("unified-personal-mcp-server")

# =============================================================================
# SHARED CONFIGURATION AND UTILITIES
# =============================================================================

# Data persistence
DATA_FILE = Path("context_data.json")

# MCP Server configuration
HOME_DIR = Path.home()
PROJECTS_DIR = HOME_DIR / "Documents"
DESKTOP_DIR = HOME_DIR / "Desktop"
DOWNLOADS_DIR = HOME_DIR / "Downloads"

# Common ignore patterns for file operations
DEFAULT_IGNORE_PATTERNS = [
    ".git/",
    ".DS_Store",
    "*.pyc",
    "__pycache__/",
    "node_modules/",
    ".env",
    "*.log",
    ".vscode/",
    ".idea/",
    "*.tmp",
    "*.temp"
]

# =============================================================================
# FASTAPI MODELS AND CONTEXT STORAGE
# =============================================================================

class ContextItem(BaseModel):
    id: str = Field(..., min_length=1, max_length=100, description="Unique identifier for the context stream")
    content: str = Field(..., min_length=1, max_length=10000, description="The context content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        if not v.strip():
            raise ValueError('ID cannot be empty or whitespace')
        return v.strip()
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Content cannot be empty or whitespace')
        return v.strip()

class ContextResponse(BaseModel):
    timestamp: str
    role: str = "system"
    content: str
    metadata: Dict[str, Any]

class StatusResponse(BaseModel):
    status: str
    stored_contexts: List[str]
    total_items: int
    server_uptime: str
    mcp_tools: int
    mcp_resources: int

class ContextStore:
    def __init__(self):
        self.data: Dict[str, List[Dict]] = {}
        self.load_data()
    
    def load_data(self):
        """Load context data from file if it exists"""
        try:
            if DATA_FILE.exists():
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                logger.info(f"Loaded {len(self.data)} context streams from {DATA_FILE}")
            else:
                logger.info("No existing data file found, starting with empty store")
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            self.data = {}
    
    def save_data(self):
        """Save context data to file"""
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            logger.debug("Data saved successfully")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    def add_context(self, item: ContextItem) -> Dict[str, Any]:
        """Add a context item to the store"""
        if item.id not in self.data:
            self.data[item.id] = []
        
        context_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": "system",
            "content": item.content,
            "metadata": item.metadata
        }
        
        self.data[item.id].append(context_entry)
        self.save_data()
        
        logger.info(f"Added context to stream '{item.id}': {item.content[:50]}...")
        return {"status": "added", "id": item.id, "total_items": len(self.data[item.id])}
    
    def get_context(self, target: str, limit: Optional[int] = None) -> List[Dict]:
        """Get context items for a target"""
        items = self.data.get(target, [])
        if limit:
            items = items[-limit:]  # Get most recent items
        return items
    
    def delete_context(self, target: str) -> bool:
        """Delete all context for a target"""
        if target in self.data:
            del self.data[target]
            self.save_data()
            logger.info(f"Deleted context stream '{target}'")
            return True
        return False
    
    def get_all_streams(self) -> Dict[str, int]:
        """Get all context streams with their item counts"""
        return {stream_id: len(items) for stream_id, items in self.data.items()}

# =============================================================================
# GIT AND FILE UTILITIES
# =============================================================================

def load_gitignore_patterns(repo_path: Path) -> List[str]:
    """Load .gitignore patterns from a repository"""
    gitignore_path = repo_path / ".gitignore"
    patterns = []
    
    if gitignore_path.exists():
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
        except Exception as e:
            logger.warning(f"Could not read .gitignore: {e}")
    
    return patterns

def should_ignore_file(file_path: Path, ignore_patterns: List[str]) -> bool:
    """Check if a file should be ignored based on patterns"""
    try:
        spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)
        return spec.match_file(str(file_path))
    except Exception:
        return False

def find_git_repositories(search_path: Path, max_depth: int = 3) -> List[Path]:
    """Find all git repositories in a directory tree"""
    repos = []
    
    def _search_recursive(path: Path, current_depth: int):
        if current_depth > max_depth:
            return
            
        try:
            if (path / ".git").exists():
                repos.append(path)
                return  # Don't search inside git repos
                
            for item in path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    _search_recursive(item, current_depth + 1)
        except (PermissionError, OSError):
            pass
    
    _search_recursive(search_path, 0)
    return repos

def get_repo_info(repo_path: Path) -> Dict[str, Any]:
    """Get detailed information about a git repository"""
    try:
        repo = Repo(repo_path)
        
        # Get current branch
        try:
            current_branch = repo.active_branch.name
        except:
            current_branch = "detached HEAD"
        
        # Get remote URLs
        remotes = {remote.name: list(remote.urls) for remote in repo.remotes}
        
        # Get recent commits
        commits = []
        try:
            for commit in repo.iter_commits(max_count=5):
                commits.append({
                    "hash": commit.hexsha[:8],
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat()
                })
        except:
            pass
        
        # Get status
        status = {
            "modified": [item.a_path for item in repo.index.diff(None)],
            "staged": [item.a_path for item in repo.index.diff("HEAD")],
            "untracked": repo.untracked_files
        }
        
        return {
            "path": str(repo_path),
            "name": repo_path.name,
            "current_branch": current_branch,
            "remotes": remotes,
            "recent_commits": commits,
            "status": status,
            "is_dirty": repo.is_dirty()
        }
    except Exception as e:
        return {
            "path": str(repo_path),
            "name": repo_path.name,
            "error": str(e)
        }

# =============================================================================
# MCP SERVER SETUP
# =============================================================================

# MCP Server instance
mcp_server = Server("unified-personal-mcp-server")

@mcp_server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available resources"""
    resources = []
    
    # Git repositories
    for search_dir in [PROJECTS_DIR, DESKTOP_DIR]:
        if search_dir.exists():
            repos = find_git_repositories(search_dir)
            for repo_path in repos:
                resources.append(Resource(
                    uri=f"git://repo/{repo_path.name}",
                    name=f"Git Repository: {repo_path.name}",
                    description=f"Git repository at {repo_path}",
                    mimeType="application/json"
                ))
    
    # Personal directories
    for dir_name, dir_path in [
        ("Documents", PROJECTS_DIR),
        ("Desktop", DESKTOP_DIR),
        ("Downloads", DOWNLOADS_DIR)
    ]:
        if dir_path.exists():
            resources.append(Resource(
                uri=f"file://directory/{dir_name.lower()}",
                name=f"{dir_name} Directory",
                description=f"Files in {dir_path}",
                mimeType="application/json"
            ))
    
    return resources

@mcp_server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read a specific resource"""
    try:
        if uri.startswith("git://repo/"):
            repo_name = uri.replace("git://repo/", "")
            
            # Find the repository
            for search_dir in [PROJECTS_DIR, DESKTOP_DIR]:
                if search_dir.exists():
                    repos = find_git_repositories(search_dir)
                    for repo_path in repos:
                        if repo_path.name == repo_name:
                            repo_info = get_repo_info(repo_path)
                            return json.dumps(repo_info, indent=2)
            
            return json.dumps({"error": f"Repository '{repo_name}' not found"})
        
        elif uri.startswith("file://directory/"):
            dir_name = uri.replace("file://directory/", "")
            
            dir_map = {
                "documents": PROJECTS_DIR,
                "desktop": DESKTOP_DIR,
                "downloads": DOWNLOADS_DIR
            }
            
            if dir_name in dir_map:
                dir_path = dir_map[dir_name]
                if dir_path.exists():
                    files = []
                    for item in dir_path.iterdir():
                        if not should_ignore_file(item, DEFAULT_IGNORE_PATTERNS):
                            files.append({
                                "name": item.name,
                                "path": str(item),
                                "type": "directory" if item.is_dir() else "file",
                                "size": item.stat().st_size if item.is_file() else None,
                                "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                            })
                    
                    return json.dumps({
                        "directory": str(dir_path),
                        "files": sorted(files, key=lambda x: (x["type"] == "file", x["name"]))
                    }, indent=2)
            
            return json.dumps({"error": f"Directory '{dir_name}' not found"})
        
        else:
            return json.dumps({"error": f"Unknown resource URI: {uri}"})
    
    except Exception as e:
        logger.error(f"Error reading resource {uri}: {e}")
        return json.dumps({"error": str(e)})

@mcp_server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="list_git_repos",
            description="List all git repositories in common directories",
            inputSchema={
                "type": "object",
                "properties": {
                    "search_path": {
                        "type": "string",
                        "description": "Optional custom path to search for repositories"
                    }
                }
            }
        ),
        Tool(
            name="get_repo_status",
            description="Get detailed status of a specific git repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Name of the repository"
                    }
                },
                "required": ["repo_name"]
            }
        ),
        Tool(
            name="git_command",
            description="Execute a git command in a specific repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Name of the repository"
                    },
                    "command": {
                        "type": "string",
                        "description": "Git command to execute (without 'git' prefix)"
                    }
                },
                "required": ["repo_name", "command"]
            }
        ),
        Tool(
            name="read_file",
            description="Read the contents of a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="write_file",
            description="Write content to a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["file_path", "content"]
            }
        ),
        Tool(
            name="list_directory",
            description="List contents of a directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Path to the directory to list"
                    },
                    "include_hidden": {
                        "type": "boolean",
                        "description": "Whether to include hidden files",
                        "default": False
                    }
                },
                "required": ["directory_path"]
            }
        ),
        Tool(
            name="search_files",
            description="Search for files by name or content",
            inputSchema={
                "type": "object",
                "properties": {
                    "search_path": {
                        "type": "string",
                        "description": "Directory to search in"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (filename or content)"
                    },
                    "search_content": {
                        "type": "boolean",
                        "description": "Whether to search file contents",
                        "default": False
                    }
                },
                "required": ["search_path", "pattern"]
            }
        ),
        Tool(
            name="add_context",
            description="Add context to the persistent storage",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Context stream ID"
                    },
                    "content": {
                        "type": "string",
                        "description": "Context content to store"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata",
                        "default": {}
                    }
                },
                "required": ["id", "content"]
            }
        ),
        Tool(
            name="get_context",
            description="Retrieve context from persistent storage",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Context stream ID to retrieve"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of recent items to return",
                        "minimum": 1,
                        "maximum": 1000
                    }
                },
                "required": ["target"]
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    try:
        if name == "list_git_repos":
            search_path = arguments.get("search_path")
            if search_path:
                search_dirs = [Path(search_path)]
            else:
                search_dirs = [PROJECTS_DIR, DESKTOP_DIR]
            
            all_repos = []
            for search_dir in search_dirs:
                if search_dir.exists():
                    repos = find_git_repositories(search_dir)
                    for repo_path in repos:
                        repo_info = get_repo_info(repo_path)
                        all_repos.append(repo_info)
            
            return [TextContent(
                type="text",
                text=json.dumps(all_repos, indent=2)
            )]
        
        elif name == "get_repo_status":
            repo_name = arguments["repo_name"]
            
            # Find the repository
            for search_dir in [PROJECTS_DIR, DESKTOP_DIR]:
                if search_dir.exists():
                    repos = find_git_repositories(search_dir)
                    for repo_path in repos:
                        if repo_path.name == repo_name:
                            repo_info = get_repo_info(repo_path)
                            return [TextContent(
                                type="text",
                                text=json.dumps(repo_info, indent=2)
                            )]
            
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Repository '{repo_name}' not found"})
            )]
        
        elif name == "git_command":
            repo_name = arguments["repo_name"]
            command = arguments["command"]
            
            # Find the repository
            repo_path = None
            for search_dir in [PROJECTS_DIR, DESKTOP_DIR]:
                if search_dir.exists():
                    repos = find_git_repositories(search_dir)
                    for rp in repos:
                        if rp.name == repo_name:
                            repo_path = rp
                            break
                if repo_path:
                    break
            
            if not repo_path:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Repository '{repo_name}' not found"})
                )]
            
            try:
                result = subprocess.run(
                    f"git {command}",
                    shell=True,
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "command": f"git {command}",
                        "returncode": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }, indent=2)
                )]
            except subprocess.TimeoutExpired:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "Command timed out"})
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)})
                )]
        
        elif name == "read_file":
            file_path = Path(arguments["file_path"])
            
            if not file_path.exists():
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"File not found: {file_path}"})
                )]
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "file_path": str(file_path),
                        "content": content,
                        "size": len(content)
                    }, indent=2)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Could not read file: {e}"})
                )]
        
        elif name == "write_file":
            file_path = Path(arguments["file_path"])
            content = arguments["content"]
            
            try:
                # Create parent directories if they don't exist
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "file_path": str(file_path),
                        "bytes_written": len(content.encode('utf-8')),
                        "status": "success"
                    }, indent=2)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Could not write file: {e}"})
                )]
        
        elif name == "list_directory":
            directory_path = Path(arguments["directory_path"])
            include_hidden = arguments.get("include_hidden", False)
            
            if not directory_path.exists():
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Directory not found: {directory_path}"})
                )]
            
            if not directory_path.is_dir():
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Path is not a directory: {directory_path}"})
                )]
            
            try:
                files = []
                for item in directory_path.iterdir():
                    if not include_hidden and item.name.startswith('.'):
                        continue
                    
                    if not should_ignore_file(item, DEFAULT_IGNORE_PATTERNS):
                        files.append({
                            "name": item.name,
                            "path": str(item),
                            "type": "directory" if item.is_dir() else "file",
                            "size": item.stat().st_size if item.is_file() else None,
                            "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                        })
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "directory": str(directory_path),
                        "files": sorted(files, key=lambda x: (x["type"] == "file", x["name"]))
                    }, indent=2)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Could not list directory: {e}"})
                )]
        
        elif name == "search_files":
            search_path = Path(arguments["search_path"])
            pattern = arguments["pattern"]
            search_content = arguments.get("search_content", False)
            
            if not search_path.exists():
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Search path not found: {search_path}"})
                )]
            
            try:
                matches = []
                
                def search_recursive(path: Path):
                    try:
                        for item in path.iterdir():
                            if should_ignore_file(item, DEFAULT_IGNORE_PATTERNS):
                                continue
                            
                            if item.is_file():
                                # Check filename
                                if pattern.lower() in item.name.lower():
                                    matches.append({
                                        "path": str(item),
                                        "name": item.name,
                                        "match_type": "filename",
                                        "size": item.stat().st_size,
                                        "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                                    })
                                
                                # Check content if requested
                                if search_content and item.suffix in ['.txt', '.py', '.js', '.html', '.css', '.md', '.json', '.yaml', '.yml']:
                                    try:
                                        with open(item, 'r', encoding='utf-8') as f:
                                            content = f.read()
                                            if pattern.lower() in content.lower():
                                                matches.append({
                                                    "path": str(item),
                                                    "name": item.name,
                                                    "match_type": "content",
                                                    "size": item.stat().st_size,
                                                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                                                })
                                    except:
                                        pass
                            
                            elif item.is_dir():
                                search_recursive(item)
                    except (PermissionError, OSError):
                        pass
                
                search_recursive(search_path)
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "search_path": str(search_path),
                        "pattern": pattern,
                        "search_content": search_content,
                        "matches": matches[:50]  # Limit results
                    }, indent=2)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Search failed: {e}"})
                )]
        
        elif name == "add_context":
            item = ContextItem(
                id=arguments["id"],
                content=arguments["content"],
                metadata=arguments.get("metadata", {})
            )
            result = context_store.add_context(item)
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "get_context":
            target = arguments["target"]
            limit = arguments.get("limit")
            messages = context_store.get_context(target, limit)
            return [TextContent(
                type="text",
                text=json.dumps({"messages": messages}, indent=2)
            )]
        
        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"})
            )]
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)})
        )]

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

# Global context store
context_store = ContextStore()

# Startup time for uptime calculation
startup_time = datetime.now(timezone.utc)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    logger.info("Unified Personal MCP Server starting up...")
    yield
    logger.info("Unified Personal MCP Server shutting down...")
    context_store.save_data()

# FastAPI app with lifespan management
app = FastAPI(
    title="Unified Personal MCP Server",
    description="A comprehensive server that implements both MCP protocol for Cline integration and HTTP API for web applications",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

@app.post("/add_context", response_model=Dict[str, Any])
async def add_context(item: ContextItem):
    """
    Add a context item to a memory stream.
    
    - **id**: Unique identifier for the context stream
    - **content**: The context content to store
    - **metadata**: Optional metadata dictionary
    """
    try:
        result = context_store.add_context(item)
        return result
    except Exception as e:
        logger.error(f"Error adding context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add context"
        )

@app.get("/get_context", response_model=Dict[str, List[ContextResponse]])
async def get_context(
    target: str = Query(..., description="Target context stream ID"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of items to return (most recent)")
):
    """
    Retrieve all context items for a given target ID.
    
    - **target**: The context stream ID to retrieve
    - **limit**: Optional limit on number of items returned (most recent first)
    """
    try:
        messages = context_store.get_context(target, limit)
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Error getting context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve context"
        )

@app.delete("/delete_context")
async def delete_context(target: str = Query(..., description="Target context stream ID to delete")):
    """
    Delete all context items for a given target ID.
    
    - **target**: The context stream ID to delete
    """
    try:
        if context_store.delete_context(target):
            return {"status": "deleted", "id": target}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Context stream '{target}' not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete context"
        )

@app.post("/repos/update_context", response_model=Dict[str, Any])
async def update_repo_context(data: ContextItem):
    """
    Specialized endpoint to log repository-related updates.
    
    Automatically prefixes the ID with 'repo_' and adds repo_update metadata.
    """
    try:
        repo_item = ContextItem(
            id=f"repo_{data.id}",
            content=data.content,
            metadata={"type": "repo_update", **data.metadata}
        )
        result = context_store.add_context(repo_item)
        return result
    except Exception as e:
        logger.error(f"Error updating repo context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update repository context"
        )

@app.get("/status", response_model=StatusResponse)
async def status():
    """
    Returns server health check and current context streams information.
    """
    try:
        streams = context_store.get_all_streams()
        total_items = sum(streams.values())
        uptime = datetime.now(timezone.utc) - startup_time
        
        # Count MCP tools and resources
        tools = await handle_list_tools()
        resources = await handle_list_resources()
        
        return StatusResponse(
            status="ok",
            stored_contexts=list(streams.keys()),
            total_items=total_items,
            server_uptime=str(uptime).split('.')[0],  # Remove microseconds
            mcp_tools=len(tools),
            mcp_resources=len(resources)
        )
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get server status"
        )

@app.get("/")
async def root():
    """Root endpoint with basic server information"""
    return {
        "message": "Unified Personal MCP Server",
        "version": "2.0.0",
        "features": ["MCP Protocol", "HTTP API", "Git Integration", "File Management"],
        "docs": "/docs",
        "status": "/status"
    }

# =============================================================================
# MCP SERVER ENTRY POINT
# =============================================================================

async def run_mcp_server():
    """Run the MCP server via stdio"""
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="unified-personal-mcp-server",
                server_version="2.0.0",
                capabilities=mcp_server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                )
            )
        )

# =============================================================================
# MAIN ENTRY POINTS
# =============================================================================

def main():
    """Main entry point - determines whether to run MCP or HTTP server"""
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        # Run FastAPI HTTP server
        logger.info("Starting Unified Personal MCP Server in HTTP mode...")
        uvicorn.run(
            "unified_mcp_server:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8000)),
            reload=True
        )
    else:
        # Run MCP server via stdio (default for Cline integration)
        logger.info("Starting Unified Personal MCP Server in MCP mode...")
        asyncio.run(run_mcp_server())

if __name__ == "__main__":
    main()
