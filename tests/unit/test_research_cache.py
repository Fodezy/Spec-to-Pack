"""Tests for research cache manager."""

import json
import tempfile
import time
from pathlib import Path

import pytest

from studio.cache.research_cache import CacheEntry, CacheStats, ResearchCacheManager


class TestCacheEntry:
    """Test CacheEntry data class."""
    
    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        current_time = time.time()
        entry = CacheEntry(
            key="test_key",
            data={"test": "data"},
            created_at=current_time,
            expires_at=current_time + 3600,
            metadata={"source": "test"}
        )
        
        assert entry.key == "test_key"
        assert entry.data == {"test": "data"}
        assert entry.created_at == current_time
        assert entry.expires_at == current_time + 3600
        assert entry.metadata == {"source": "test"}
        
    def test_is_expired(self):
        """Test expiration checking."""
        current_time = time.time()
        
        # Not expired entry
        fresh_entry = CacheEntry(
            key="fresh",
            data="data",
            created_at=current_time,
            expires_at=current_time + 3600,
            metadata={}
        )
        assert not fresh_entry.is_expired()
        
        # Expired entry
        expired_entry = CacheEntry(
            key="expired",
            data="data",
            created_at=current_time - 7200,
            expires_at=current_time - 3600,
            metadata={}
        )
        assert expired_entry.is_expired()
        
    def test_age_calculation(self):
        """Test age calculation."""
        created_time = time.time() - 1800  # 30 minutes ago
        entry = CacheEntry(
            key="test",
            data="data",
            created_at=created_time,
            expires_at=created_time + 3600,
            metadata={}
        )
        
        age = entry.age_seconds()
        assert 1700 <= age <= 1900  # Approximately 30 minutes


class TestResearchCacheManager:
    """Test ResearchCacheManager."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
            
    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """Create cache manager with temporary directory."""
        return ResearchCacheManager(cache_dir=temp_cache_dir, max_size_mb=1)
        
    def test_initialization(self, temp_cache_dir):
        """Test cache manager initialization."""
        manager = ResearchCacheManager(cache_dir=temp_cache_dir)
        
        assert manager.cache_dir == Path(temp_cache_dir)
        assert manager.max_size_bytes == 100 * 1024 * 1024  # 100MB default
        
        # Cache level directories should be created
        for level in manager.TTL_CONFIG.keys():
            level_dir = manager.cache_dir / level.lower()
            assert level_dir.exists()
            
    def test_get_cache_key(self, cache_manager):
        """Test cache key generation."""
        # String input
        key1 = cache_manager._get_cache_key("test string")
        key2 = cache_manager._get_cache_key("test string")
        key3 = cache_manager._get_cache_key("different string")
        
        assert key1 == key2  # Same input = same key
        assert key1 != key3  # Different input = different key
        assert len(key1) == 16  # Hash is truncated to 16 chars
        
        # Dict input
        dict_key = cache_manager._get_cache_key({"key": "value", "order": "matters"})
        same_dict_key = cache_manager._get_cache_key({"order": "matters", "key": "value"})
        assert dict_key == same_dict_key  # Order shouldn't matter (sorted)
        
    def test_set_and_get(self, cache_manager):
        """Test basic set and get operations."""
        level = "SEARCH_RESULTS"
        key = "test_key"
        data = {"query": "test", "results": ["result1", "result2"]}
        
        # Set data
        success = cache_manager.set(level, key, data)
        assert success
        
        # Get data
        retrieved = cache_manager.get(level, key)
        assert retrieved == data
        
        # Non-existent key
        missing = cache_manager.get(level, "nonexistent")
        assert missing is None
        
    def test_hash_based_operations(self, cache_manager):
        """Test hash-based set and get operations."""
        level = "EMBEDDINGS"
        key_data = "input text for embedding"
        value_data = [0.1, 0.2, 0.3, 0.4]
        
        # Set by hash
        success = cache_manager.set_by_hash(level, key_data, value_data)
        assert success
        
        # Get by hash
        retrieved = cache_manager.get_by_hash(level, key_data)
        assert retrieved == value_data
        
        # Different input should not match
        different = cache_manager.get_by_hash(level, "different input")
        assert different is None
        
    def test_ttl_expiration(self, cache_manager):
        """Test TTL-based expiration."""
        level = "SEARCH_RESULTS"
        key = "expiring_key"
        data = "test data"
        
        # Manually create an expired entry
        current_time = time.time()
        expired_entry = CacheEntry(
            key=key,
            data=data,
            created_at=current_time - 7200,  # 2 hours ago
            expires_at=current_time - 3600,  # Expired 1 hour ago
            metadata={}
        )
        
        # Load existing entries and add expired one
        entries = cache_manager._load_cache_level(level)
        entries[key] = expired_entry
        cache_manager._save_cache_level(level, entries)
        
        # Should return None for expired entry
        retrieved = cache_manager.get(level, key)
        assert retrieved is None
        
    def test_cleanup_expired(self, cache_manager):
        """Test cleanup of expired entries."""
        level = "SCRAPED_CONTENT"
        current_time = time.time()
        
        # Add mix of fresh and expired entries
        fresh_data = cache_manager.set(level, "fresh", "fresh_data")
        assert fresh_data
        
        # Manually add expired entry
        entries = cache_manager._load_cache_level(level)
        entries["expired"] = CacheEntry(
            key="expired",
            data="expired_data",
            created_at=current_time - 7200,
            expires_at=current_time - 3600,
            metadata={}
        )
        cache_manager._save_cache_level(level, entries)
        
        # Cleanup should remove expired entries
        cleaned_count = cache_manager.cleanup_expired()
        assert cleaned_count >= 1
        
        # Fresh data should still be there
        fresh_retrieved = cache_manager.get(level, "fresh")
        assert fresh_retrieved == "fresh_data"
        
        # Expired data should be gone
        expired_retrieved = cache_manager.get(level, "expired")
        assert expired_retrieved is None
        
    def test_clear_operations(self, cache_manager):
        """Test cache clearing operations."""
        # Add data to multiple levels
        cache_manager.set("SEARCH_RESULTS", "key1", "data1")
        cache_manager.set("EMBEDDINGS", "key2", "data2")
        
        # Clear single level
        success = cache_manager.clear_level("SEARCH_RESULTS")
        assert success
        
        # Data should be gone from cleared level
        assert cache_manager.get("SEARCH_RESULTS", "key1") is None
        
        # Data should remain in other level
        assert cache_manager.get("EMBEDDINGS", "key2") == "data2"
        
        # Clear all levels
        success = cache_manager.clear_all()
        assert success
        
        # All data should be gone
        assert cache_manager.get("EMBEDDINGS", "key2") is None
        
    def test_cache_stats(self, cache_manager):
        """Test cache statistics generation."""
        # Add some test data
        cache_manager.set("SEARCH_RESULTS", "key1", "data1")
        cache_manager.set("EMBEDDINGS", "key2", {"embedding": [1, 2, 3]})
        
        # Get stats
        stats = cache_manager.get_stats()
        
        assert isinstance(stats, CacheStats)
        assert stats.total_entries >= 2
        assert stats.cache_size_bytes > 0
        assert isinstance(stats.level_stats, dict)
        
        # Check level-specific stats
        for level in cache_manager.TTL_CONFIG.keys():
            if level in stats.level_stats:
                level_stat = stats.level_stats[level]
                assert "entries" in level_stat
                assert "expired" in level_stat
                assert "size_bytes" in level_stat
                
    def test_size_limit_enforcement(self, temp_cache_dir):
        """Test size limit enforcement."""
        # Create manager with very small limit
        small_cache = ResearchCacheManager(cache_dir=temp_cache_dir, max_size_mb=0.001)  # ~1KB
        
        level = "RESEARCH_DOCS"
        
        # Add large data that exceeds limit
        large_data = "x" * 2000  # 2KB string
        
        # Add multiple entries
        for i in range(5):
            small_cache.set(level, f"key{i}", large_data)
            
        # Check that not all entries remain (LRU eviction)
        remaining_entries = 0
        for i in range(5):
            if small_cache.get(level, f"key{i}") is not None:
                remaining_entries += 1
                
        # Should have fewer entries due to size limits
        assert remaining_entries < 5
        
    def test_invalid_cache_level(self, cache_manager):
        """Test handling of invalid cache levels."""
        with pytest.raises(ValueError, match="Invalid cache level"):
            cache_manager.get("INVALID_LEVEL", "key")
            
        with pytest.raises(ValueError, match="Invalid cache level"):
            cache_manager.set("INVALID_LEVEL", "key", "data")
            
        with pytest.raises(ValueError, match="Invalid cache level"):
            cache_manager.clear_level("INVALID_LEVEL")
            
    def test_persistence(self, cache_manager):
        """Test cache persistence across manager instances."""
        level = "SEARCH_RESULTS"
        key = "persistent_key"
        data = {"persistent": "data"}
        
        # Set data with first manager
        cache_manager.set(level, key, data)
        
        # Create new manager with same directory
        new_manager = ResearchCacheManager(cache_dir=str(cache_manager.cache_dir))
        
        # Data should still be there
        retrieved = new_manager.get(level, key)
        assert retrieved == data
        
    def test_corrupted_cache_handling(self, cache_manager, temp_cache_dir):
        """Test handling of corrupted cache files."""
        level = "EMBEDDINGS"
        cache_file = cache_manager._cache_files[level]
        
        # Create corrupted cache file
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w') as f:
            f.write("invalid json content")
            
        # Should handle corruption gracefully
        entries = cache_manager._load_cache_level(level)
        assert entries == {}  # Should return empty dict
        
        # Should be able to set new data after corruption
        success = cache_manager.set(level, "new_key", "new_data")
        assert success
        
        retrieved = cache_manager.get(level, "new_key")
        assert retrieved == "new_data"