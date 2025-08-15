"""Tests for browser adapters."""

import pytest

from studio.adapters.browser import HtmlContent, PlaywrightBrowserAdapter, StubBrowserAdapter


def test_stub_browser_adapter():
    """Test stub browser adapter."""
    adapter = StubBrowserAdapter()
    
    result = adapter.fetch("https://example.com")
    
    assert isinstance(result, HtmlContent)
    assert result.url == "https://example.com"
    assert result.status_code == 200
    assert "Stub content" in result.html
    
    text = adapter.extract(result)
    assert "Stub content" in text
    assert "<html>" not in text  # Should strip tags


def test_playwright_browser_adapter_offline_mode():
    """Test PlaywrightBrowserAdapter respects offline mode."""
    adapter = PlaywrightBrowserAdapter()
    
    with pytest.raises(RuntimeError, match="Network access blocked in offline mode"):
        adapter.fetch("https://example.com", offline_mode=True)


def test_playwright_browser_adapter_robots_txt_disallowed():
    """Test PlaywrightBrowserAdapter respects robots.txt."""
    adapter = PlaywrightBrowserAdapter()
    
    # Mock a robots.txt check that disallows the URL
    def mock_check_robots_txt(url):
        return False
    
    adapter._check_robots_txt = mock_check_robots_txt
    
    with pytest.raises(ValueError, match="disallowed by robots.txt"):
        adapter.fetch("https://example.com")


def test_playwright_browser_adapter_rate_limiting():
    """Test PlaywrightBrowserAdapter applies rate limiting."""
    import time
    
    adapter = PlaywrightBrowserAdapter(rate_limit_delay=0.1)
    
    # Mock the actual fetch to avoid network calls
    def mock_fetch_without_rate_limit(url, offline_mode=False):
        return HtmlContent(url=url, html="<html><body>Test</body></html>", 
                          status_code=200, headers={})
    
    original_fetch = adapter.fetch
    start_time = time.time()
    
    # Make multiple calls to the same domain
    domain = "https://example.com"
    adapter._last_request_time[domain] = start_time - 0.05  # Recent request
    
    # This should apply rate limiting
    adapter._apply_rate_limit(domain)
    
    elapsed = time.time() - start_time
    assert elapsed >= 0.05  # Should have waited


def test_playwright_browser_adapter_text_extraction():
    """Test PlaywrightBrowserAdapter text extraction."""
    adapter = PlaywrightBrowserAdapter()
    
    html_content = HtmlContent(
        url="https://example.com",
        html="<html><head><script>alert('test');</script></head><body><h1>Title</h1><p>Content</p></body></html>",
        status_code=200,
        headers={}
    )
    
    text = adapter.extract(html_content)
    
    assert "Title" in text
    assert "Content" in text
    assert "script" not in text  # Should remove scripts
    assert "<h1>" not in text    # Should remove HTML tags


def test_browser_adapter_domain_extraction():
    """Test domain extraction helper."""
    adapter = PlaywrightBrowserAdapter()
    
    domain = adapter._get_domain("https://example.com/path/to/page")
    assert domain == "https://example.com"
    
    domain = adapter._get_domain("http://subdomain.example.org:8080/page")
    assert domain == "http://subdomain.example.org:8080"


def test_browser_adapter_empty_html_handling():
    """Test handling of empty HTML content."""
    adapter = PlaywrightBrowserAdapter()
    
    html_content = HtmlContent(
        url="https://example.com",
        html="",
        status_code=500,
        headers={"error": "test error"}
    )
    
    text = adapter.extract(html_content)
    assert text == ""