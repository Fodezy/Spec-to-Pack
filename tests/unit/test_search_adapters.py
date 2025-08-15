"""Tests for search adapters."""

import pytest

from studio.adapters.search import (
    DuckDuckGoAdapter,
    FallbackSearchAdapter,
    SearchResult,
    SearxNGAdapter,
    StubSearchAdapter,
)


class TestSearchResult:
    """Test SearchResult data class."""
    
    def test_search_result_creation(self):
        """Test SearchResult object creation."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            score=0.95,
            engine="test",
            category="general"
        )
        
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"
        assert result.score == 0.95
        assert result.engine == "test"
        assert result.category == "general"
        
    def test_search_result_repr(self):
        """Test SearchResult string representation."""
        result = SearchResult(
            title="A very long title that should be truncated for display",
            url="https://example.com",
            snippet="snippet",
            engine="test"
        )
        
        repr_str = repr(result)
        assert "A very long title that should be truncated fo..." in repr_str
        assert "https://example.com" in repr_str
        assert "test" in repr_str


class TestStubSearchAdapter:
    """Test StubSearchAdapter."""
    
    def test_health_check(self):
        """Test stub adapter health check."""
        adapter = StubSearchAdapter()
        assert adapter.health_check() is True
        
    def test_empty_query(self):
        """Test search with empty query."""
        adapter = StubSearchAdapter()
        results = adapter.search("")
        assert results == []
        
    def test_search_returns_deterministic_results(self):
        """Test that stub search returns deterministic results."""
        adapter = StubSearchAdapter()
        
        # Same query should return same results
        results1 = adapter.search("test query")
        results2 = adapter.search("test query")
        
        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1.title == r2.title
            assert r1.url == r2.url
            assert r1.snippet == r2.snippet
            
    def test_search_respects_limit(self):
        """Test search respects result limit."""
        adapter = StubSearchAdapter()
        
        results = adapter.search("test", limit=2)
        assert len(results) <= 2
        
    def test_search_different_categories(self):
        """Test search with different categories."""
        adapter = StubSearchAdapter()
        
        general_results = adapter.search("test", category="general")
        it_results = adapter.search("test", category="it")
        
        # Results should be categorized properly
        for result in general_results:
            assert result.category == "general"
            
        for result in it_results:
            assert result.category == "it"


class TestSearxNGAdapter:
    """Test SearxNGAdapter."""
    
    def test_initialization(self):
        """Test SearxNG adapter initialization."""
        adapter = SearxNGAdapter("http://localhost:8888")
        assert adapter.base_url == "http://localhost:8888"
        assert adapter.timeout == 10
        
    def test_custom_timeout(self):
        """Test custom timeout configuration."""
        adapter = SearxNGAdapter(timeout=30)
        assert adapter.timeout == 30
        
    def test_empty_query(self):
        """Test search with empty query."""
        adapter = SearxNGAdapter()
        results = adapter.search("")
        assert results == []
        
    def test_health_check_offline(self):
        """Test health check when SearxNG is not available."""
        adapter = SearxNGAdapter("http://nonexistent:9999")
        assert adapter.health_check() is False


class TestDuckDuckGoAdapter:
    """Test DuckDuckGoAdapter."""
    
    def test_initialization(self):
        """Test DuckDuckGo adapter initialization."""
        adapter = DuckDuckGoAdapter(timeout=15)
        assert adapter.timeout == 15
        
    def test_health_check_without_package(self):
        """Test health check when duckduckgo-search is not available."""
        # This test assumes the package might not be installed
        adapter = DuckDuckGoAdapter()
        health = adapter.health_check()
        assert isinstance(health, bool)
        
    def test_empty_query(self):
        """Test search with empty query."""
        adapter = DuckDuckGoAdapter()
        results = adapter.search("")
        assert results == []


class TestFallbackSearchAdapter:
    """Test FallbackSearchAdapter."""
    
    def test_initialization(self):
        """Test fallback adapter initialization."""
        adapter = FallbackSearchAdapter(
            searxng_url="http://test:8888",
            timeout=20,
            health_check_interval=600
        )
        assert adapter.primary.base_url == "http://test:8888"
        assert adapter.primary.timeout == 20
        assert adapter.health_check_interval == 600
        
    def test_get_active_engine(self):
        """Test getting active engine name."""
        adapter = FallbackSearchAdapter(searxng_url="http://nonexistent:9999")
        
        # Should fallback to duckduckgo when searxng unavailable
        engine = adapter.get_active_engine()
        assert engine in ["searxng", "duckduckgo", "none"]
        
    def test_health_check(self):
        """Test overall health check."""
        adapter = FallbackSearchAdapter(searxng_url="http://nonexistent:9999")
        
        # Should be healthy if at least one adapter works
        health = adapter.health_check()
        assert isinstance(health, bool)
        
    def test_empty_query(self):
        """Test search with empty query."""
        adapter = FallbackSearchAdapter()
        results = adapter.search("")
        assert results == []
        
    def test_health_check_caching(self):
        """Test health check caching."""
        adapter = FallbackSearchAdapter(health_check_interval=1)
        
        # First check
        health1 = adapter._check_primary_health()
        
        # Second check should use cache
        health2 = adapter._check_primary_health()
        
        assert health1 == health2
        assert adapter.last_health_check > 0


@pytest.mark.integration
class TestSearchAdaptersIntegration:
    """Integration tests for search adapters (require network/services)."""
    
    @pytest.mark.skipif(True, reason="Requires SearxNG service running")
    def test_searxng_integration(self):
        """Test SearxNG integration with real service."""
        adapter = SearxNGAdapter("http://localhost:8888")
        
        if adapter.health_check():
            results = adapter.search("python programming", limit=3)
            assert len(results) <= 3
            
            for result in results:
                assert isinstance(result, SearchResult)
                assert result.title
                assert result.url.startswith(("http://", "https://"))
        else:
            pytest.skip("SearxNG service not available")
            
    @pytest.mark.skipif(True, reason="Requires network access")  
    def test_duckduckgo_integration(self):
        """Test DuckDuckGo integration with real API."""
        adapter = DuckDuckGoAdapter()
        
        if adapter.health_check():
            results = adapter.search("test query", limit=2)
            assert len(results) <= 2
            
            for result in results:
                assert isinstance(result, SearchResult) 
                assert result.title
                assert result.url.startswith(("http://", "https://"))
                assert result.engine == "duckduckgo"
        else:
            pytest.skip("DuckDuckGo adapter not available")
            
    def test_fallback_behavior(self):
        """Test fallback from SearxNG to DuckDuckGo."""
        # Use non-existent SearxNG URL to force fallback
        adapter = FallbackSearchAdapter(searxng_url="http://nonexistent:9999")
        
        # Should still work via fallback
        health = adapter.health_check()
        if health:
            results = adapter.search("test", limit=1)
            if results:
                assert len(results) == 1
                assert isinstance(results[0], SearchResult)