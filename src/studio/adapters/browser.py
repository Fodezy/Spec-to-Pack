"""Browser adapter for web content fetching."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


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
    def fetch(self, url: str) -> HtmlContent:
        """Fetch HTML content from URL."""
        pass

    @abstractmethod
    def extract(self, html_content: HtmlContent) -> str:
        """Extract clean text from HTML."""
        pass


class StubBrowserAdapter(BrowserAdapter):
    """Stub implementation for development/testing."""

    def fetch(self, url: str) -> HtmlContent:
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
