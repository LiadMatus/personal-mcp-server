#!/usr/bin/env python3
"""
Personal MCP Server with Git and File System Access
Provides tools and resources for managing git repositories and personal files
"""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime

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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("personal-mcp-server")

# Server instance
server = Server("personal-mcp-server")

# Configuration
HOME_DIR = Path.home()
PROJECTS_DIR = HOME_DIR / "Documents"  # Common location for projects
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

@server.list_resources()
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

@server.read_resource()
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

@server.list_tools()
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
        )
    ]

@server.call_tool()
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

async def main():
    """Main entry point for the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="personal-mcp-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
