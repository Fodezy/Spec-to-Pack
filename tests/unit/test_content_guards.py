"""Tests for content guards and security features."""

import time
from unittest.mock import Mock, patch

import pytest

from studio.guards.content_guards import ContentGuard, ContentGuardException, RobotsTxtChecker


class TestRobotsTxtChecker:
    """Test RobotsTxtChecker."""
    
    def test_initialization(self):
        """Test robots.txt checker initialization."""
        checker = RobotsTxtChecker(
            user_agent="Test Bot",
            cache_ttl=1800
        )
        
        assert checker.user_agent == "Test Bot"
        assert checker.cache_ttl == 1800
        assert checker._cache == {}
        
    def test_get_robots_txt_url(self):
        """Test robots.txt URL generation."""
        checker = RobotsTxtChecker()
        
        url = "https://example.com/some/path"
        robots_url = checker._get_robots_txt_url(url)
        
        assert robots_url == "https://example.com/robots.txt"
        
    def test_can_fetch_no_robots_txt(self):
        """Test behavior when robots.txt is not available."""
        checker = RobotsTxtChecker()
        
        # Mock failed robots.txt fetch
        with patch.object(checker, '_fetch_robots_txt', return_value=None):
            # Should allow fetching when no robots.txt found
            result = checker.can_fetch("https://example.com/page")
            assert result is True
            
    def test_can_fetch_with_cache(self):
        """Test caching behavior."""
        checker = RobotsTxtChecker(cache_ttl=3600)
        
        # Mock robots parser
        mock_parser = Mock()
        mock_parser.can_fetch.return_value = True
        
        # Add to cache
        domain = "example.com"
        checker._cache[domain] = (mock_parser, time.time())
        
        # Should use cached parser
        result = checker.can_fetch("https://example.com/test")
        assert result is True
        mock_parser.can_fetch.assert_called_once()
        
    def test_cache_expiration(self):
        """Test cache expiration handling."""
        checker = RobotsTxtChecker(cache_ttl=10)
        
        domain = "example.com"
        mock_parser = Mock()
        
        # Add expired entry to cache
        checker._cache[domain] = (mock_parser, time.time() - 20)
        
        # Should not use expired cache
        cached_parser = checker._get_cached_robots_parser(domain)
        assert cached_parser is None
        
    def test_error_handling(self):
        """Test error handling in robots.txt checking."""
        checker = RobotsTxtChecker()
        
        # Invalid URL should not crash
        result = checker.can_fetch("not-a-url")
        assert result is True  # Conservative default
        
        # Should handle network errors gracefully
        with patch('requests.get', side_effect=Exception("Network error")):
            result = checker.can_fetch("https://example.com/test")
            assert result is True


class TestContentGuard:
    """Test ContentGuard."""
    
    def test_initialization_defaults(self):
        """Test content guard initialization with defaults."""
        guard = ContentGuard()
        
        assert guard.max_doc_tokens == 8000
        assert guard.max_docs_per_domain == 3
        assert guard.rate_limit_delay == 2.0
        assert guard.respect_robots_txt is True
        assert guard._domain_counts == {}
        assert guard._last_request_time == {}
        
    def test_initialization_custom(self):
        """Test content guard initialization with custom values."""
        guard = ContentGuard(
            max_doc_tokens=5000,
            max_docs_per_domain=5,
            rate_limit_delay=1.5,
            respect_robots_txt=False
        )
        
        assert guard.max_doc_tokens == 5000
        assert guard.max_docs_per_domain == 5
        assert guard.rate_limit_delay == 1.5
        assert guard.respect_robots_txt is False
        assert guard._robots_checker is None
        
    def test_domain_extraction(self):
        """Test domain extraction from URLs."""
        guard = ContentGuard()
        
        assert guard._get_domain("https://example.com/path") == "example.com"
        assert guard._get_domain("http://test.example.com:8080/") == "test.example.com:8080"
        assert guard._get_domain("invalid-url") == "unknown"
        
    def test_token_estimation(self):
        """Test token count estimation."""
        guard = ContentGuard()
        
        # Simple text
        short_text = "Hello world"
        tokens = guard._estimate_tokens(short_text)
        assert tokens == max(1, len(short_text) // 4)
        
        # Empty text
        empty_tokens = guard._estimate_tokens("")
        assert empty_tokens == 1  # Minimum 1 token
        
    def test_url_allowed_checking(self):
        """Test URL allowance checking."""
        guard = ContentGuard(max_docs_per_domain=2)
        
        url1 = "https://example.com/page1"
        url2 = "https://example.com/page2" 
        url3 = "https://example.com/page3"
        
        # First URL should be allowed
        guard.check_url_allowed(url1)  # Should not raise
        
        # Second URL should be allowed
        guard.check_url_allowed(url2)  # Should not raise
        
        # Simulate successful fetches
        guard.record_successful_fetch(url1)
        guard.record_successful_fetch(url2)
        
        # Third URL should be blocked (exceeds domain limit)
        with pytest.raises(ContentGuardException, match="Domain limit exceeded"):
            guard.check_url_allowed(url3)
            
    def test_robots_txt_checking(self):
        """Test robots.txt compliance checking."""
        guard = ContentGuard(respect_robots_txt=True)
        
        # Mock robots checker
        mock_robots_checker = Mock()
        mock_robots_checker.can_fetch.return_value = False
        guard._robots_checker = mock_robots_checker
        
        # Should raise exception when robots.txt disallows
        with pytest.raises(ContentGuardException, match="Robots.txt disallows"):
            guard.check_url_allowed("https://example.com/blocked")
            
        # Should work when robots.txt allows
        mock_robots_checker.can_fetch.return_value = True
        guard.check_url_allowed("https://example.com/allowed")  # Should not raise
        
    def test_rate_limiting(self):
        """Test rate limiting enforcement."""
        guard = ContentGuard(rate_limit_delay=0.1)  # Short delay for testing
        
        url = "https://example.com/test"
        
        # First request should be immediate
        start_time = time.time()
        guard.check_rate_limit(url)
        first_duration = time.time() - start_time
        
        assert first_duration < 0.05  # Should be very quick
        
        # Second request should be delayed
        start_time = time.time()
        guard.check_rate_limit(url)
        second_duration = time.time() - start_time
        
        assert second_duration >= 0.08  # Should include rate limit delay
        
    def test_content_size_checking(self):
        """Test content size limits and truncation."""
        guard = ContentGuard(max_doc_tokens=10)  # Very small for testing
        
        url = "https://example.com/test"
        
        # Small content should pass through unchanged
        small_content = "Short text"
        result = guard.check_content_size(small_content, url)
        assert result == small_content
        
        # Large content should be truncated
        large_content = "This is a very long piece of content " * 100
        result = guard.check_content_size(large_content, url)
        
        assert len(result) < len(large_content)
        assert "[Content truncated at" in result
        
        # Empty content should raise exception
        with pytest.raises(ContentGuardException, match="Empty or invalid content"):
            guard.check_content_size("", url)
            
        with pytest.raises(ContentGuardException, match="Empty or invalid content"):
            guard.check_content_size("   ", url)  # Only whitespace
            
    def test_content_truncation_boundaries(self):
        """Test content truncation at sentence/line boundaries."""
        guard = ContentGuard(max_doc_tokens=20)  # Small limit
        
        url = "https://example.com/test"
        
        # Content with sentence boundary
        content_with_period = "First sentence is here. Second sentence continues. Third sentence ends."
        result = guard.check_content_size(content_with_period, url)
        
        # Should try to truncate at sentence boundary if reasonable
        if "." in result and not result.endswith("[Content truncated at 20 tokens limit]"):
            # If truncated at period, should end with period + truncation notice
            assert result.count(".") >= 1
            
        # Content with line breaks
        content_with_lines = "Line one\nLine two\nLine three\nLine four\nLine five"
        result = guard.check_content_size(content_with_lines, url)
        assert "[Content truncated at" in result
        
    def test_successful_fetch_recording(self):
        """Test recording successful fetches."""
        guard = ContentGuard()
        
        url1 = "https://example.com/page1"
        url2 = "https://different.com/page1"
        url3 = "https://example.com/page2"
        
        # Record fetches
        guard.record_successful_fetch(url1)
        guard.record_successful_fetch(url2)
        guard.record_successful_fetch(url3)
        
        # Check domain counts
        stats = guard.get_domain_stats()
        
        assert stats["example.com"]["documents_fetched"] == 2
        assert stats["different.com"]["documents_fetched"] == 1
        
    def test_domain_statistics(self):
        """Test domain usage statistics."""
        guard = ContentGuard(max_docs_per_domain=3)
        
        # Record some fetches
        guard.record_successful_fetch("https://example.com/1")
        guard.record_successful_fetch("https://example.com/2")
        guard.record_successful_fetch("https://test.com/1")
        
        stats = guard.get_domain_stats()
        
        assert "example.com" in stats
        assert "test.com" in stats
        
        example_stats = stats["example.com"]
        assert example_stats["documents_fetched"] == 2
        assert example_stats["remaining_quota"] == 1
        
        test_stats = stats["test.com"]
        assert test_stats["documents_fetched"] == 1
        assert test_stats["remaining_quota"] == 2
        
    def test_reset_statistics(self):
        """Test resetting usage statistics."""
        guard = ContentGuard()
        
        # Add some data
        guard.record_successful_fetch("https://example.com/test")
        guard._last_request_time["example.com"] = time.time()
        
        # Verify data exists
        assert len(guard._domain_counts) > 0
        assert len(guard._last_request_time) > 0
        
        # Reset
        guard.reset_stats()
        
        # Verify data is cleared
        assert len(guard._domain_counts) == 0
        assert len(guard._last_request_time) == 0
        
    def test_robots_txt_disabled(self):
        """Test behavior when robots.txt checking is disabled."""
        guard = ContentGuard(respect_robots_txt=False)
        
        # Should not check robots.txt
        assert guard._robots_checker is None
        
        # Should allow any URL
        guard.check_url_allowed("https://example.com/any-path")  # Should not raise


class TestContentGuardsIntegration:
    """Integration tests for content guards."""
    
    @pytest.mark.integration
    def test_end_to_end_content_processing(self):
        """Test end-to-end content processing workflow."""
        guard = ContentGuard(
            max_doc_tokens=100,
            max_docs_per_domain=2,
            rate_limit_delay=0.01,  # Fast for testing
            respect_robots_txt=False  # Skip for testing
        )
        
        urls = [
            "https://example.com/page1",
            "https://example.com/page2", 
            "https://test.com/page1"
        ]
        
        contents = [
            "Short content for page 1",
            "Longer content for page 2 " * 50,  # Will be truncated
            "Content for different domain"
        ]
        
        processed_contents = []
        
        for url, content in zip(urls, contents):
            # Check URL is allowed
            guard.check_url_allowed(url)
            
            # Apply rate limiting
            guard.check_rate_limit(url)
            
            # Process content
            processed = guard.check_content_size(content, url)
            processed_contents.append(processed)
            
            # Record successful fetch
            guard.record_successful_fetch(url)
            
        # Verify results
        assert len(processed_contents) == 3
        assert processed_contents[0] == contents[0]  # Short content unchanged
        assert len(processed_contents[1]) < len(contents[1])  # Long content truncated
        assert "[Content truncated" in processed_contents[1]
        
        # Check domain limits would block additional requests
        with pytest.raises(ContentGuardException):
            guard.check_url_allowed("https://example.com/page3")  # Would exceed limit
            
        # Different domain should still work
        guard.check_url_allowed("https://test.com/page2")  # Should not raise
        
    def test_multiple_guards_independence(self):
        """Test that multiple guard instances are independent."""
        guard1 = ContentGuard(max_docs_per_domain=1)
        guard2 = ContentGuard(max_docs_per_domain=2)
        
        url = "https://example.com/test"
        
        # First guard allows one fetch
        guard1.check_url_allowed(url)
        guard1.record_successful_fetch(url)
        
        # Second guard should still allow the same domain
        guard2.check_url_allowed(url)  # Should not raise
        guard2.record_successful_fetch(url)
        
        # First guard should now block additional requests
        with pytest.raises(ContentGuardException):
            guard1.check_url_allowed(url)
            
        # Second guard should still allow one more
        guard2.check_url_allowed(url)  # Should not raise