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
        ),
        Tool(
            name="git_branch",
            description="Git branch operations (list, create, switch, delete)",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Name of the repository"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["list", "create", "switch", "delete"],
                        "description": "Branch operation to perform"
                    },
                    "branch_name": {
                        "type": "string",
                        "description": "Branch name (required for create, switch, delete)"
                    }
                },
                "required": ["repo_name", "action"]
            }
        ),
        Tool(
            name="git_diff",
            description="Show git diff for files or commits",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Name of the repository"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Optional specific file to diff"
                    },
                    "commit_range": {
                        "type": "string",
                        "description": "Optional commit range (e.g., 'HEAD~1..HEAD')"
                    },
                    "staged": {
                        "type": "boolean",
                        "description": "Show staged changes",
                        "default": False
                    }
                },
                "required": ["repo_name"]
            }
        ),
        Tool(
            name="git_commit",
            description="Create a git commit with staged changes",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "Name of the repository"
                    },
                    "message": {
                        "type": "string",
                        "description": "Commit message"
                    },
                    "add_all": {
                        "type": "boolean",
                        "description": "Add all changes before committing",
                        "default": False
                    }
                },
                "required": ["repo_name", "message"]
            }
        ),
        Tool(
            name="batch_file_operation",
            description="Perform batch operations on multiple files",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["copy", "move", "delete", "rename"],
                        "description": "Operation to perform"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination path (for copy/move operations)"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Rename pattern with {name} placeholder"
                    }
                },
                "required": ["operation", "files"]
            }
        ),
        Tool(
            name="search_context",
            description="Search through stored context with filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "stream_filter": {
                        "type": "string",
                        "description": "Filter by specific stream ID"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Filter from date (ISO format)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Filter to date (ISO format)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 50,
                        "maximum": 200
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="create_project_template",
            description="Create a new project from template",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_type": {
                        "type": "string",
                        "enum": ["python", "javascript", "react", "fastapi", "mcp-server"],
                        "description": "Type of project template"
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Name of the new project"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination directory"
                    },
                    "git_init": {
                        "type": "boolean",
                        "description": "Initialize git repository",
                        "default": True
                    }
                },
                "required": ["template_type", "project_name", "destination"]
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
        
        elif name == "git_branch":
            repo_name = arguments["repo_name"]
            action = arguments["action"]
            branch_name = arguments.get("branch_name")
            
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
                repo = Repo(repo_path)
                
                if action == "list":
                    branches = []
                    for branch in repo.branches:
                        branches.append({
                            "name": branch.name,
                            "is_current": branch == repo.active_branch,
                            "commit": branch.commit.hexsha[:8],
                            "message": branch.commit.message.strip()
                        })
                    
                    return [TextContent(
                        type="text",
                        text=json.dumps({"branches": branches}, indent=2)
                    )]
                
                elif action == "create":
                    if not branch_name:
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": "branch_name required for create action"})
                        )]
                    
                    new_branch = repo.create_head(branch_name)
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "action": "created",
                            "branch": branch_name,
                            "commit": new_branch.commit.hexsha[:8]
                        }, indent=2)
                    )]
                
                elif action == "switch":
                    if not branch_name:
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": "branch_name required for switch action"})
                        )]
                    
                    repo.heads[branch_name].checkout()
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "action": "switched",
                            "branch": branch_name,
                            "commit": repo.active_branch.commit.hexsha[:8]
                        }, indent=2)
                    )]
                
                elif action == "delete":
                    if not branch_name:
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": "branch_name required for delete action"})
                        )]
                    
                    repo.delete_head(branch_name)
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "action": "deleted",
                            "branch": branch_name
                        }, indent=2)
                    )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Git branch operation failed: {e}"})
                )]
        
        elif name == "git_diff":
            repo_name = arguments["repo_name"]
            file_path = arguments.get("file_path")
            commit_range = arguments.get("commit_range")
            staged = arguments.get("staged", False)
            
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
                cmd_parts = ["git", "diff"]
                
                if staged:
                    cmd_parts.append("--staged")
                
                if commit_range:
                    cmd_parts.append(commit_range)
                
                if file_path:
                    cmd_parts.append("--")
                    cmd_parts.append(file_path)
                
                result = subprocess.run(
                    cmd_parts,
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "diff": result.stdout,
                        "file_path": file_path,
                        "commit_range": commit_range,
                        "staged": staged
                    }, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Git diff failed: {e}"})
                )]
        
        elif name == "git_commit":
            repo_name = arguments["repo_name"]
            message = arguments["message"]
            add_all = arguments.get("add_all", False)
            
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
                repo = Repo(repo_path)
                
                if add_all:
                    repo.git.add(A=True)
                
                commit = repo.index.commit(message)
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "commit_hash": commit.hexsha[:8],
                        "message": message,
                        "author": str(commit.author),
                        "files_changed": len(commit.stats.files)
                    }, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Git commit failed: {e}"})
                )]
        
        elif name == "batch_file_operation":
            operation = arguments["operation"]
            files = arguments["files"]
            destination = arguments.get("destination")
            pattern = arguments.get("pattern")
            
            try:
                import shutil
                results = []
                
                for file_path in files:
                    file_obj = Path(file_path)
                    
                    if not file_obj.exists():
                        results.append({"file": file_path, "status": "error", "message": "File not found"})
                        continue
                    
                    try:
                        if operation == "copy":
                            if not destination:
                                results.append({"file": file_path, "status": "error", "message": "Destination required"})
                                continue
                            dest_path = Path(destination) / file_obj.name
                            shutil.copy2(file_obj, dest_path)
                            results.append({"file": file_path, "status": "success", "destination": str(dest_path)})
                        
                        elif operation == "move":
                            if not destination:
                                results.append({"file": file_path, "status": "error", "message": "Destination required"})
                                continue
                            dest_path = Path(destination) / file_obj.name
                            shutil.move(str(file_obj), str(dest_path))
                            results.append({"file": file_path, "status": "success", "destination": str(dest_path)})
                        
                        elif operation == "delete":
                            if file_obj.is_file():
                                file_obj.unlink()
                            else:
                                shutil.rmtree(file_obj)
                            results.append({"file": file_path, "status": "success", "message": "Deleted"})
                        
                        elif operation == "rename":
                            if not pattern:
                                results.append({"file": file_path, "status": "error", "message": "Pattern required"})
                                continue
                            new_name = pattern.replace("{name}", file_obj.stem)
                            new_path = file_obj.parent / (new_name + file_obj.suffix)
                            file_obj.rename(new_path)
                            results.append({"file": file_path, "status": "success", "new_name": str(new_path)})
                    
                    except Exception as e:
                        results.append({"file": file_path, "status": "error", "message": str(e)})
                
                return [TextContent(
                    type="text",
                    text=json.dumps({"operation": operation, "results": results}, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Batch operation failed: {e}"})
                )]
        
        elif name == "search_context":
            query = arguments["query"]
            stream_filter = arguments.get("stream_filter")
            date_from = arguments.get("date_from")
            date_to = arguments.get("date_to")
            limit = arguments.get("limit", 50)
            
            try:
                from datetime import datetime
                results = []
                
                for stream_id, messages in context_store.data.items():
                    if stream_filter and stream_id != stream_filter:
                        continue
                    
                    for message in messages:
                        # Date filtering
                        if date_from or date_to:
                            msg_date = datetime.fromisoformat(message["timestamp"].replace('Z', '+00:00'))
                            if date_from and msg_date < datetime.fromisoformat(date_from):
                                continue
                            if date_to and msg_date > datetime.fromisoformat(date_to):
                                continue
                        
                        # Text search
                        if query.lower() in message["content"].lower():
                            results.append({
                                "stream_id": stream_id,
                                "timestamp": message["timestamp"],
                                "content": message["content"],
                                "metadata": message.get("metadata", {}),
                                "match_score": message["content"].lower().count(query.lower())
                            })
                
                # Sort by relevance (match score) and date
                results.sort(key=lambda x: (x["match_score"], x["timestamp"]), reverse=True)
                results = results[:limit]
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "query": query,
                        "total_results": len(results),
                        "results": results
                    }, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Context search failed: {e}"})
                )]
        
        elif name == "create_project_template":
            template_type = arguments["template_type"]
            project_name = arguments["project_name"]
            destination = arguments["destination"]
            git_init = arguments.get("git_init", True)
            
            try:
                project_path = Path(destination) / project_name
                project_path.mkdir(parents=True, exist_ok=True)
                
                # Template configurations
                templates = {
                    "python": {
                        "files": {
                            "main.py": "#!/usr/bin/env python3\n\ndef main():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    main()\n",
                            "requirements.txt": "# Add your dependencies here\n",
                            "README.md": f"# {project_name}\n\nA Python project.\n\n## Installation\n\n```bash\npip install -r requirements.txt\n```\n\n## Usage\n\n```bash\npython main.py\n```\n",
                            ".gitignore": "__pycache__/\n*.pyc\n*.pyo\n*.pyd\n.Python\nbuild/\ndevelop-eggs/\ndist/\ndownloads/\neggs/\n.eggs/\nlib/\nlib64/\nparts/\nsdist/\nvar/\nwheels/\n*.egg-info/\n.installed.cfg\n*.egg\n"
                        }
                    },
                    "javascript": {
                        "files": {
                            "index.js": "console.log('Hello, World!');\n",
                            "package.json": f'{{\n  "name": "{project_name}",\n  "version": "1.0.0",\n  "description": "",\n  "main": "index.js",\n  "scripts": {{\n    "start": "node index.js"\n  }},\n  "keywords": [],\n  "author": "",\n  "license": "ISC"\n}}\n',
                            "README.md": f"# {project_name}\n\nA JavaScript project.\n\n## Installation\n\n```bash\nnpm install\n```\n\n## Usage\n\n```bash\nnpm start\n```\n",
                            ".gitignore": "node_modules/\nnpm-debug.log*\nyarn-debug.log*\nyarn-error.log*\n.env\n"
                        }
                    },
                    "react": {
                        "files": {
                            "package.json": f'{{\n  "name": "{project_name}",\n  "version": "0.1.0",\n  "private": true,\n  "dependencies": {{\n    "react": "^18.2.0",\n    "react-dom": "^18.2.0",\n    "react-scripts": "5.0.1"\n  }},\n  "scripts": {{\n    "start": "react-scripts start",\n    "build": "react-scripts build",\n    "test": "react-scripts test",\n    "eject": "react-scripts eject"\n  }}\n}}\n',
                            "public/index.html": f'<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="utf-8" />\n    <meta name="viewport" content="width=device-width, initial-scale=1" />\n    <title>{project_name}</title>\n</head>\n<body>\n    <div id="root"></div>\n</body>\n</html>\n',
                            "src/App.js": f'import React from \'react\';\n\nfunction App() {{\n  return (\n    <div>\n      <h1>Welcome to {project_name}</h1>\n      <p>Your React app is ready!</p>\n    </div>\n  );\n}}\n\nexport default App;\n',
                            "src/index.js": "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\n\nconst root = ReactDOM.createRoot(document.getElementById('root'));\nroot.render(<App />);\n",
                            "README.md": f"# {project_name}\n\nA React application.\n\n## Installation\n\n```bash\nnpm install\n```\n\n## Usage\n\n```bash\nnpm start\n```\n",
                            ".gitignore": "node_modules/\nbuild/\n.env\nnpm-debug.log*\nyarn-debug.log*\nyarn-error.log*\n"
                        }
                    },
                    "fastapi": {
                        "files": {
                            "main.py": f'from fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\n\napp = FastAPI(title="{project_name}", version="1.0.0")\n\napp.add_middleware(\n    CORSMiddleware,\n    allow_origins=["*"],\n    allow_credentials=True,\n    allow_methods=["*"],\n    allow_headers=["*"],\n)\n\n@app.get("/")\nasync def root():\n    return {{"message": "Hello from {project_name}!"}}\n\n@app.get("/health")\nasync def health():\n    return {{"status": "healthy"}}\n\nif __name__ == "__main__":\n    import uvicorn\n    uvicorn.run(app, host="0.0.0.0", port=8000)\n',
                            "requirements.txt": "fastapi>=0.104.0\nuvicorn[standard]>=0.24.0\npydantic>=2.0.0\n",
                            "README.md": f"# {project_name}\n\nA FastAPI application.\n\n## Installation\n\n```bash\npip install -r requirements.txt\n```\n\n## Usage\n\n```bash\npython main.py\n```\n\nAPI docs available at: http://localhost:8000/docs\n",
                            ".gitignore": "__pycache__/\n*.pyc\n.env\n.venv/\nvenv/\n"
                        }
                    },
                    "mcp-server": {
                        "files": {
                            "server.py": f'#!/usr/bin/env python3\n"""\n{project_name} MCP Server\n"""\n\nimport asyncio\nimport json\nfrom mcp.server import Server\nfrom mcp.server.models import InitializationOptions\nfrom mcp.server.stdio import stdio_server\nfrom mcp.types import Resource, Tool, TextContent\n\nserver = Server("{project_name.lower().replace(" ", "-")}")\n\n@server.list_tools()\nasync def handle_list_tools():\n    return [\n        Tool(\n            name="hello",\n            description="Say hello",\n            inputSchema={{\n                "type": "object",\n                "properties": {{\n                    "name": {{\n                        "type": "string",\n                        "description": "Name to greet"\n                    }}\n                }},\n                "required": ["name"]\n            }}\n        )\n    ]\n\n@server.call_tool()\nasync def handle_call_tool(name: str, arguments: dict):\n    if name == "hello":\n        name_arg = arguments.get("name", "World")\n        return [TextContent(\n            type="text",\n            text=f"Hello, {{name_arg}}!"\n        )]\n    else:\n        raise ValueError(f"Unknown tool: {{name}}")\n\nasync def main():\n    async with stdio_server() as (read_stream, write_stream):\n        await server.run(\n            read_stream,\n            write_stream,\n            InitializationOptions(\n                server_name="{project_name.lower().replace(" ", "-")}",\n                server_version="1.0.0",\n                capabilities=server.get_capabilities(\n                    notification_options=None,\n                    experimental_capabilities=None,\n                )\n            )\n        )\n\nif __name__ == "__main__":\n    asyncio.run(main())\n',
                            "requirements.txt": "mcp>=1.0.0\n",
                            "README.md": f"# {project_name}\n\nAn MCP (Model Context Protocol) server.\n\n## Installation\n\n```bash\npip install -r requirements.txt\n```\n\n## Usage\n\n```bash\npython server.py\n```\n\n## Configuration\n\nAdd to your MCP client configuration:\n\n```json\n{{\n  \"mcpServers\": {{\n    \"{project_name.lower().replace(' ', '-')}\": {{\n      \"command\": \"python3\",\n      \"args\": [\"server.py\"],\n      \"cwd\": \"{project_path}\"\n    }}\n  }}\n}}\n```\n",
                            ".gitignore": "__pycache__/\n*.pyc\n.env\n.venv/\nvenv/\n"
                        }
                    }
                }
                
                if template_type not in templates:
                    return [TextContent(
                        type="text",
                        text=json.dumps({"error": f"Unknown template type: {template_type}"})
                    )]
                
                template = templates[template_type]
                created_files = []
                
                # Create files
                for file_path, content in template["files"].items():
                    full_path = project_path / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    created_files.append(str(full_path))
                
                # Initialize git repository
                if git_init:
                    try:
                        repo = Repo.init(project_path)
                        repo.index.add(created_files)
                        repo.index.commit("Initial commit")
                        created_files.append(".git (repository)")
                    except Exception as e:
                        logger.warning(f"Git init failed: {e}")
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "project_name": project_name,
                        "template_type": template_type,
                        "project_path": str(project_path),
                        "created_files": created_files,
                        "git_initialized": git_init
                    }, indent=2)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Project creation failed: {e}"})
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
    from mcp.types import ServerCapabilities, ToolsCapability, ResourcesCapability
    
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="unified-personal-mcp-server",
                server_version="2.0.0",
                capabilities=ServerCapabilities(
                    tools=ToolsCapability(listChanged=False),
                    resources=ResourcesCapability(listChanged=False)
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
