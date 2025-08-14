"""Tests for embeddings adapters."""

import hashlib

import pytest

from studio.adapters.embeddings import (
    BGEEmbeddingsAdapter,
    CachedEmbeddingsAdapter,
    StubEmbeddingsAdapter,
)


def test_stub_embeddings_adapter():
    """Test stub embeddings adapter."""
    adapter = StubEmbeddingsAdapter(dimension=128)
    
    # Test single encoding
    text = "test text"
    embedding = adapter.encode(text)
    
    assert len(embedding) == 128
    assert all(isinstance(val, float) for val in embedding)
    assert all(-1.0 <= val <= 1.0 for val in embedding)
    
    # Test deterministic behavior
    embedding2 = adapter.encode(text)
    assert embedding == embedding2
    
    # Test different text produces different embedding
    embedding3 = adapter.encode("different text")
    assert embedding != embedding3
    
    assert adapter.dimension == 128


def test_stub_embeddings_adapter_batch():
    """Test stub embeddings adapter batch encoding."""
    adapter = StubEmbeddingsAdapter(dimension=64)
    
    texts = ["text one", "text two", "text three"]
    embeddings = adapter.encode_batch(texts)
    
    assert len(embeddings) == 3
    assert all(len(emb) == 64 for emb in embeddings)
    
    # Each should be different
    assert embeddings[0] != embeddings[1]
    assert embeddings[1] != embeddings[2]


def test_bge_embeddings_adapter_import_error():
    """Test BGEEmbeddingsAdapter handles missing dependencies."""
    adapter = BGEEmbeddingsAdapter()
    
    # Mock missing import
    import sys
    original_modules = sys.modules.copy()
    if 'sentence_transformers' in sys.modules:
        del sys.modules['sentence_transformers']
    
    try:
        with pytest.raises(ImportError, match="sentence-transformers"):
            adapter._load_model()
    finally:
        # Restore modules
        sys.modules.update(original_modules)


def test_cached_embeddings_adapter():
    """Test cached embeddings adapter."""
    base_adapter = StubEmbeddingsAdapter(dimension=32)
    cached_adapter = CachedEmbeddingsAdapter(base_adapter, cache_size=2)
    
    # First encoding should call base adapter
    text1 = "first text"
    embedding1 = cached_adapter.encode(text1)
    
    assert len(embedding1) == 32
    assert len(cached_adapter._cache) == 1
    
    # Second encoding of same text should use cache
    embedding1_cached = cached_adapter.encode(text1)
    assert embedding1 == embedding1_cached
    assert len(cached_adapter._cache) == 1
    
    # Different text should create new entry
    text2 = "second text"
    embedding2 = cached_adapter.encode(text2)
    assert embedding1 != embedding2
    assert len(cached_adapter._cache) == 2
    
    # Third text should evict oldest (FIFO)
    text3 = "third text"
    embedding3 = cached_adapter.encode(text3)
    assert len(cached_adapter._cache) == 2
    
    # Original text1 should no longer be cached
    text1_hash = hashlib.md5(text1.encode('utf-8')).hexdigest()
    assert text1_hash not in cached_adapter._cache


def test_cached_embeddings_adapter_batch():
    """Test cached embeddings adapter batch processing."""
    base_adapter = StubEmbeddingsAdapter(dimension=16)
    cached_adapter = CachedEmbeddingsAdapter(base_adapter, cache_size=10)
    
    # Pre-populate cache with some texts
    cached_adapter.encode("cached text 1")
    cached_adapter.encode("cached text 2")
    
    # Batch with mix of cached and uncached
    texts = ["cached text 1", "new text 1", "cached text 2", "new text 2"]
    embeddings = cached_adapter.encode_batch(texts)
    
    assert len(embeddings) == 4
    assert all(len(emb) == 16 for emb in embeddings)
    
    # Should have cached the new texts
    assert len(cached_adapter._cache) == 4
    
    # Verify cached texts return same embeddings
    assert embeddings[0] == cached_adapter.encode("cached text 1")
    assert embeddings[2] == cached_adapter.encode("cached text 2")


def test_cached_embeddings_dimension():
    """Test cached embeddings adapter dimension property."""
    base_adapter = StubEmbeddingsAdapter(dimension=256)
    cached_adapter = CachedEmbeddingsAdapter(base_adapter)
    
    assert cached_adapter.dimension == 256


def test_text_hash_generation():
    """Test text hash generation for caching."""
    base_adapter = StubEmbeddingsAdapter()
    cached_adapter = CachedEmbeddingsAdapter(base_adapter)
    
    hash1 = cached_adapter._get_text_hash("test text")
    hash2 = cached_adapter._get_text_hash("test text")
    hash3 = cached_adapter._get_text_hash("different text")
    
    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 32  # MD5 hex digest length