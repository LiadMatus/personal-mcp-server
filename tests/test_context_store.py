#!/usr/bin/env python3
"""
Tests for context storage functionality
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

# Import the classes we want to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unified_mcp_server import ContextStore, ContextItem


class TestContextStore:
    """Test cases for ContextStore class"""
    
    def setup_method(self):
        """Set up test fixtures before each test method"""
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        
        # Patch the DATA_FILE constant to use our temp file
        with patch('unified_mcp_server.DATA_FILE', Path(self.temp_file.name)):
            self.context_store = ContextStore()
    
    def teardown_method(self):
        """Clean up after each test method"""
        # Remove the temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_add_context_new_stream(self):
        """Test adding context to a new stream"""
        # Arrange
        item = ContextItem(
            id="test_stream",
            content="Test content",
            metadata={"type": "test"}
        )
        
        # Act
        result = self.context_store.add_context(item)
        
        # Assert
        assert result["status"] == "added"
        assert result["id"] == "test_stream"
        assert result["total_items"] == 1
        assert "test_stream" in self.context_store.data
        assert len(self.context_store.data["test_stream"]) == 1
        
        stored_item = self.context_store.data["test_stream"][0]
        assert stored_item["content"] == "Test content"
        assert stored_item["metadata"] == {"type": "test"}
        assert stored_item["role"] == "system"
        assert "timestamp" in stored_item
    
    def test_add_context_existing_stream(self):
        """Test adding context to an existing stream"""
        # Arrange
        item1 = ContextItem(id="stream1", content="First content")
        item2 = ContextItem(id="stream1", content="Second content")
        
        # Act
        self.context_store.add_context(item1)
        result = self.context_store.add_context(item2)
        
        # Assert
        assert result["total_items"] == 2
        assert len(self.context_store.data["stream1"]) == 2
        assert self.context_store.data["stream1"][0]["content"] == "First content"
        assert self.context_store.data["stream1"][1]["content"] == "Second content"
    
    def test_get_context_existing_stream(self):
        """Test retrieving context from an existing stream"""
        # Arrange
        item = ContextItem(id="test_stream", content="Test content")
        self.context_store.add_context(item)
        
        # Act
        result = self.context_store.get_context("test_stream")
        
        # Assert
        assert len(result) == 1
        assert result[0]["content"] == "Test content"
    
    def test_get_context_nonexistent_stream(self):
        """Test retrieving context from a non-existent stream"""
        # Act
        result = self.context_store.get_context("nonexistent")
        
        # Assert
        assert result == []
    
    def test_get_context_with_limit(self):
        """Test retrieving context with a limit"""
        # Arrange
        stream_id = "limited_stream"
        for i in range(5):
            item = ContextItem(id=stream_id, content=f"Content {i}")
            self.context_store.add_context(item)
        
        # Act
        result = self.context_store.get_context(stream_id, limit=3)
        
        # Assert
        assert len(result) == 3
        # Should get the last 3 items (most recent)
        assert result[0]["content"] == "Content 2"
        assert result[1]["content"] == "Content 3"
        assert result[2]["content"] == "Content 4"
    
    def test_delete_context_existing_stream(self):
        """Test deleting an existing context stream"""
        # Arrange
        item = ContextItem(id="delete_me", content="To be deleted")
        self.context_store.add_context(item)
        
        # Act
        result = self.context_store.delete_context("delete_me")
        
        # Assert
        assert result is True
        assert "delete_me" not in self.context_store.data
    
    def test_delete_context_nonexistent_stream(self):
        """Test deleting a non-existent context stream"""
        # Act
        result = self.context_store.delete_context("nonexistent")
        
        # Assert
        assert result is False
    
    def test_get_all_streams(self):
        """Test getting all context streams with their counts"""
        # Arrange
        item1 = ContextItem(id="stream1", content="Content 1")
        item2 = ContextItem(id="stream1", content="Content 2")
        item3 = ContextItem(id="stream2", content="Content 3")
        
        self.context_store.add_context(item1)
        self.context_store.add_context(item2)
        self.context_store.add_context(item3)
        
        # Act
        result = self.context_store.get_all_streams()
        
        # Assert
        assert result == {"stream1": 2, "stream2": 1}
    
    def test_load_data_file_exists(self):
        """Test loading data when file exists"""
        # Arrange
        test_data = {
            "test_stream": [
                {
                    "timestamp": "2025-01-01T00:00:00Z",
                    "role": "system",
                    "content": "Test content",
                    "metadata": {}
                }
            ]
        }
        
        # Write test data to temp file
        with open(self.temp_file.name, 'w') as f:
            json.dump(test_data, f)
        
        # Act
        with patch('unified_mcp_server.DATA_FILE', Path(self.temp_file.name)):
            store = ContextStore()
        
        # Assert
        assert store.data == test_data
    
    def test_load_data_file_not_exists(self):
        """Test loading data when file doesn't exist"""
        # Arrange - remove the temp file
        os.unlink(self.temp_file.name)
        
        # Act
        with patch('unified_mcp_server.DATA_FILE', Path(self.temp_file.name)):
            store = ContextStore()
        
        # Assert
        assert store.data == {}
    
    def test_save_data(self):
        """Test saving data to file"""
        # Arrange
        item = ContextItem(id="save_test", content="Save me")
        self.context_store.add_context(item)
        
        # Act
        self.context_store.save_data()
        
        # Assert
        with open(self.temp_file.name, 'r') as f:
            saved_data = json.load(f)
        
        assert "save_test" in saved_data
        assert saved_data["save_test"][0]["content"] == "Save me"


class TestContextItem:
    """Test cases for ContextItem Pydantic model"""
    
    def test_valid_context_item(self):
        """Test creating a valid ContextItem"""
        # Act
        item = ContextItem(
            id="test_id",
            content="Test content",
            metadata={"key": "value"}
        )
        
        # Assert
        assert item.id == "test_id"
        assert item.content == "Test content"
        assert item.metadata == {"key": "value"}
    
    def test_context_item_default_metadata(self):
        """Test ContextItem with default metadata"""
        # Act
        item = ContextItem(id="test", content="content")
        
        # Assert
        assert item.metadata == {}
    
    def test_context_item_validation_empty_id(self):
        """Test ContextItem validation with empty ID"""
        # Act & Assert
        with pytest.raises(ValueError, match="ID cannot be empty"):
            ContextItem(id="", content="content")
    
    def test_context_item_validation_whitespace_id(self):
        """Test ContextItem validation with whitespace-only ID"""
        # Act & Assert
        with pytest.raises(ValueError, match="ID cannot be empty"):
            ContextItem(id="   ", content="content")
    
    def test_context_item_validation_empty_content(self):
        """Test ContextItem validation with empty content"""
        # Act & Assert
        with pytest.raises(ValueError, match="Content cannot be empty"):
            ContextItem(id="test", content="")
    
    def test_context_item_validation_whitespace_content(self):
        """Test ContextItem validation with whitespace-only content"""
        # Act & Assert
        with pytest.raises(ValueError, match="Content cannot be empty"):
            ContextItem(id="test", content="   ")


if __name__ == "__main__":
    pytest.main([__file__])
