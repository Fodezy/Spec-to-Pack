"""Browser adapter for web content fetching."""

import asyncio
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser


@dataclass
class HtmlContent:
    """HTML content wrapper."""
    url: str
    html: str
    status_code: int
    headers: dict


class BrowserAdapter(ABC):
    """Abstract browser adapter interface."""

    @abstractmethod
    def fetch(self, url: str, offline_mode: bool = False) -> HtmlContent:
        """Fetch HTML content from URL."""
        pass

    @abstractmethod
    def extract(self, html_content: HtmlContent) -> str:
        """Extract clean text from HTML."""
        pass


class PlaywrightBrowserAdapter(BrowserAdapter):
    """Playwright-based browser adapter with robots.txt and rate limiting."""
    
    def __init__(self, 
                 user_agent: str = "Spec-to-Pack Studio Research Bot 1.0",
                 rate_limit_delay: float = 1.0,
                 timeout_ms: int = 30000):
        """Initialize with rate limiting and user agent."""
        self.user_agent = user_agent
        self.rate_limit_delay = rate_limit_delay
        self.timeout_ms = timeout_ms
        self._last_request_time: dict[str, float] = {}
        self._robots_cache: dict[str, Optional[RobotFileParser]] = {}
        
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
        
    def _check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        domain = self._get_domain(url)
        
        # Check cache first
        if domain in self._robots_cache:
            robots = self._robots_cache[domain]
            if robots is None:
                return True  # No robots.txt found, assume allowed
            return robots.can_fetch(self.user_agent, url)
            
        # Fetch robots.txt
        try:
            robots_url = urljoin(domain, "/robots.txt")
            robots = RobotFileParser()
            robots.set_url(robots_url)
            robots.read()
            self._robots_cache[domain] = robots
            return robots.can_fetch(self.user_agent, url)
        except Exception:
            # If robots.txt can't be fetched, assume allowed but cache None
            self._robots_cache[domain] = None
            return True
            
    def _apply_rate_limit(self, domain: str) -> None:
        """Apply rate limiting per domain."""
        now = time.time()
        last_time = self._last_request_time.get(domain, 0)
        
        time_since_last = now - last_time
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
            
        self._last_request_time[domain] = time.time()

    def fetch(self, url: str, offline_mode: bool = False) -> HtmlContent:
        """Fetch HTML content from URL using Playwright."""
        # Offline mode guard
        if offline_mode:
            raise RuntimeError("Network access blocked in offline mode")
            
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError("PlaywrightBrowserAdapter requires playwright. Install with: pip install 'studio[rag]'")
            
        # Check robots.txt
        if not self._check_robots_txt(url):
            raise ValueError(f"URL {url} disallowed by robots.txt")
            
        # Apply rate limiting
        domain = self._get_domain(url)
        self._apply_rate_limit(domain)
        
        # Fetch content with Playwright
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    page = browser.new_page(user_agent=self.user_agent)
                    response = page.goto(url, timeout=self.timeout_ms)
                    
                    if response is None:
                        raise ValueError(f"Failed to navigate to {url}")
                        
                    # Wait for page to load
                    page.wait_for_load_state("networkidle")
                    
                    html = page.content()
                    status_code = response.status
                    headers = dict(response.headers)
                    
                    return HtmlContent(
                        url=url,
                        html=html,
                        status_code=status_code,
                        headers=headers
                    )
                    
                finally:
                    browser.close()
                    
        except Exception as e:
            # Return empty content on error
            return HtmlContent(
                url=url,
                html="",
                status_code=500,
                headers={"error": str(e)}
            )
            
    def extract(self, html_content: HtmlContent) -> str:
        """Extract clean text from HTML using basic cleanup."""
        if not html_content.html:
            return ""
            
        # Remove script and style elements
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content.html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text


class StubBrowserAdapter(BrowserAdapter):
    """Stub implementation for development/testing."""

    def fetch(self, url: str, offline_mode: bool = False) -> HtmlContent:
        """Return stub HTML content."""
        return HtmlContent(
            url=url,
            html=f"<html><body><h1>Stub content for {url}</h1><p>This is placeholder content.</p></body></html>",
            status_code=200,
            headers={"content-type": "text/html"}
        )

    def extract(self, html_content: HtmlContent) -> str:
        """Extract stub text content."""
        # Simple HTML tag removal for stub
        import re
        text = re.sub(r'<[^>]+>', '', html_content.html)
        return text.strip()
