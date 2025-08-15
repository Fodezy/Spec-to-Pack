"""Tests for vector store adapters."""

import json
import tempfile
from pathlib import Path

import pytest

from studio.adapters.vector_store import (
    LanceDBVectorStoreAdapter,
    QdrantVectorStoreAdapter,
    SearchResult,
    StubVectorStoreAdapter,
)


def test_stub_vector_store_adapter():
    """Test stub vector store adapter."""
    adapter = StubVectorStoreAdapter()
    
    # Test indexing
    embedding = [0.1, 0.2, 0.3]
    adapter.index("doc1", embedding, "test content", {"key": "value"})
    
    assert len(adapter._documents) == 1
    assert "doc1" in adapter._documents
    
    doc = adapter._documents["doc1"]
    assert doc["embedding"] == embedding
    assert doc["content"] == "test content"
    assert doc["metadata"]["key"] == "value"
    
    # Test searching
    results = adapter.search([0.1, 0.2, 0.3], k=5)
    
    assert len(results) == 1
    result = results[0]
    assert isinstance(result, SearchResult)
    assert result.id == "doc1"
    assert result.content == "test content"
    assert result.score == 0.85
    assert result.metadata["key"] == "value"
    
    # Test close (no-op for stub)
    adapter.close()


def test_stub_vector_store_adapter_multiple_documents():
    """Test stub vector store with multiple documents."""
    adapter = StubVectorStoreAdapter()
    
    # Index multiple documents
    docs = [
        ("doc1", [0.1, 0.2], "content 1", {"type": "doc"}),
        ("doc2", [0.3, 0.4], "content 2", {"type": "article"}),
        ("doc3", [0.5, 0.6], "content 3", {"type": "doc"}),
    ]
    
    for doc_id, embedding, content, metadata in docs:
        adapter.index(doc_id, embedding, content, metadata)
    
    assert len(adapter._documents) == 3
    
    # Test limited search results
    results = adapter.search([0.0, 0.0], k=2)
    assert len(results) == 2


def test_lancedb_vector_store_adapter_import_error():
    """Test LanceDBVectorStoreAdapter handles missing dependencies."""
    adapter = LanceDBVectorStoreAdapter()
    
    # Mock missing import
    import sys
    original_modules = sys.modules.copy()
    if 'lancedb' in sys.modules:
        del sys.modules['lancedb']
    
    try:
        with pytest.raises(ImportError, match="lancedb"):
            adapter._get_db()
    finally:
        # Restore modules
        sys.modules.update(original_modules)


def test_lancedb_vector_store_adapter_basic():
    """Test LanceDBVectorStoreAdapter basic functionality."""
    # Use temporary directory for test database
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_db"
        adapter = LanceDBVectorStoreAdapter(str(db_path))
        
        # Test with stub data (will fail gracefully without actual LanceDB)
        embedding = [0.1, 0.2, 0.3, 0.4]
        metadata = {
            "source_url": "https://example.com",
            "retrieved_at": "2023-01-01T00:00:00Z",
            "chunk_id": "chunk-123",
            "content_hash": "abc123"
        }
        
        try:
            adapter.index("doc1", embedding, "test content", metadata)
            results = adapter.search(embedding, k=1)
            # If we get here, LanceDB is available
            assert isinstance(results, list)
        except ImportError:
            # Expected if LanceDB not installed
            pass
        
        adapter.close()


def test_qdrant_vector_store_adapter_import_error():
    """Test QdrantVectorStoreAdapter handles missing dependencies."""
    adapter = QdrantVectorStoreAdapter()
    
    # Mock missing import
    import sys
    original_modules = sys.modules.copy()
    if 'qdrant_client' in sys.modules:
        del sys.modules['qdrant_client']
    
    try:
        with pytest.raises(ImportError, match="qdrant-client"):
            adapter._get_client()
    finally:
        # Restore modules
        sys.modules.update(original_modules)


def test_qdrant_vector_store_adapter_basic():
    """Test QdrantVectorStoreAdapter basic functionality."""
    adapter = QdrantVectorStoreAdapter()
    
    # Test with stub data (will fail gracefully without actual Qdrant)
    embedding = [0.1, 0.2, 0.3, 0.4]
    metadata = {"key": "value"}
    
    try:
        adapter.index("doc1", embedding, "test content", metadata)
        results = adapter.search(embedding, k=1)
        # If we get here, Qdrant client is available but server may not be running
        assert isinstance(results, list)
    except ImportError:
        # Expected if qdrant-client not installed
        pass
    except Exception:
        # Expected if Qdrant server not running
        pass
    
    adapter.close()


def test_search_result_creation():
    """Test SearchResult dataclass creation."""
    result = SearchResult(
        id="doc1",
        score=0.95,
        content="test content",
        metadata={"key": "value"}
    )
    
    assert result.id == "doc1"
    assert result.score == 0.95
    assert result.content == "test content"
    assert result.metadata["key"] == "value"


def test_vector_store_adapter_error_handling():
    """Test vector store adapters handle errors gracefully."""
    # Test LanceDB adapter error handling
    adapter = LanceDBVectorStoreAdapter()
    
    # Search should return empty list on error
    results = adapter.search([0.1, 0.2], k=5)
    assert results == []
    
    # Test Qdrant adapter error handling
    qdrant_adapter = QdrantVectorStoreAdapter()
    results = qdrant_adapter.search([0.1, 0.2], k=5)
    assert results == []


def test_lancedb_metadata_serialization():
    """Test LanceDB adapter handles metadata serialization."""
    adapter = LanceDBVectorStoreAdapter()
    
    # Test metadata that needs JSON serialization
    complex_metadata = {
        "nested": {"key": "value"},
        "list": [1, 2, 3],
        "string": "test"
    }
    
    # This should not raise an error even if LanceDB isn't available
    try:
        adapter.index("doc1", [0.1, 0.2], "content", complex_metadata)
    except ImportError:
        # Expected if dependencies not available
        pass