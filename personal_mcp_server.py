import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Data persistence
DATA_FILE = Path("context_data.json")

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

# Global context store
context_store = ContextStore()

# Startup time for uptime calculation
startup_time = datetime.now(timezone.utc)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    logger.info("Personal MCP Server starting up...")
    yield
    logger.info("Personal MCP Server shutting down...")
    context_store.save_data()

# FastAPI app with lifespan management
app = FastAPI(
    title="Personal MCP Server",
    description="A lightweight FastAPI-based server that implements a Model Context Protocol (MCP) for streaming structured context",
    version="1.0.0",
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
        
        return StatusResponse(
            status="ok",
            stored_contexts=list(streams.keys()),
            total_items=total_items,
            server_uptime=str(uptime).split('.')[0]  # Remove microseconds
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
        "message": "Personal MCP Server",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "/status"
    }

if __name__ == "__main__":
    uvicorn.run(
        "personal_mcp_server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
