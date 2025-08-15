"""Search adapters for retrieving web content and research data."""

import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests


class SearchResult:
    """Represents a single search result."""
    
    def __init__(self, title: str, url: str, snippet: str, score: float = 0.0, 
                 engine: str = "unknown", category: str = "general"):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.score = score
        self.engine = engine
        self.category = category
        
    def __repr__(self) -> str:
        return f"SearchResult(title='{self.title[:50]}...', url='{self.url}', engine='{self.engine}')"


class SearchAdapter(ABC):
    """Abstract search adapter interface."""
    
    @abstractmethod
    def search(self, query: str, category: str = "general", limit: int = 10) -> List[SearchResult]:
        """Perform search and return results."""
        pass
        
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the search service is available."""
        pass


class SearxNGAdapter(SearchAdapter):
    """SearxNG search adapter with configurable endpoint."""
    
    def __init__(self, base_url: str = "http://localhost:8888", timeout: int = 10):
        """Initialize SearxNG adapter.
        
        Args:
            base_url: SearxNG instance URL (default: http://localhost:8888)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Spec-to-Pack Research Bot 1.0 (Educational/Research Use)'
        })
        
    def health_check(self) -> bool:
        """Check if SearxNG instance is available."""
        try:
            response = self.session.get(
                f"{self.base_url}/healthz", 
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception:
            return False
            
    def search(self, query: str, category: str = "general", limit: int = 10) -> List[SearchResult]:
        """Search using SearxNG JSON API.
        
        Args:
            query: Search query string
            category: Search category (general, it, science)
            limit: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        if not query.strip():
            return []
            
        try:
            # SearxNG JSON API endpoint
            search_url = f"{self.base_url}/search"
            
            # Map our categories to SearxNG categories
            category_map = {
                "general": "general",
                "it": "it", 
                "science": "science"
            }
            searxng_category = category_map.get(category, "general")
            
            params = {
                "q": query,
                "format": "json",
                "categories": searxng_category,
                "language": "en",
                "time_range": "",  # No time restriction
                "safesearch": "0"  # No safe search for technical content
            }
            
            response = self.session.get(
                search_url, 
                params=params, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Parse results from SearxNG response
            for item in data.get("results", [])[:limit]:
                try:
                    result = SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        score=float(item.get("score", 0.0)),
                        engine=item.get("engine", "searxng"),
                        category=category
                    )
                    
                    # Only include results with valid URLs
                    if result.url and urlparse(result.url).scheme in ['http', 'https']:
                        results.append(result)
                        
                except (KeyError, ValueError) as e:
                    # Skip malformed results
                    continue
                    
            return results
            
        except Exception as e:
            # Return empty list on error (fallback will handle)
            return []


class DuckDuckGoAdapter(SearchAdapter):
    """DuckDuckGo search adapter as fallback."""
    
    def __init__(self, timeout: int = 10):
        """Initialize DuckDuckGo adapter.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        
    def health_check(self) -> bool:
        """DuckDuckGo is generally available."""
        try:
            # Try to import the required package
            import duckduckgo_search
            return True
        except ImportError:
            return False
            
    def search(self, query: str, category: str = "general", limit: int = 10) -> List[SearchResult]:
        """Search using duckduckgo-search library.
        
        Args:
            query: Search query string
            category: Search category (ignored for DDG)
            limit: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        if not query.strip():
            return []
            
        try:
            from duckduckgo_search import DDGS
            
            results = []
            with DDGS() as ddgs:
                # Use text search with regional preference for English
                search_results = ddgs.text(
                    keywords=query,
                    region="us-en",
                    max_results=min(limit, 20)  # DDG has limits
                )
                
                for i, item in enumerate(search_results):
                    try:
                        result = SearchResult(
                            title=item.get("title", ""),
                            url=item.get("href", ""),
                            snippet=item.get("body", ""),
                            score=float(limit - i),  # Simple relevance scoring
                            engine="duckduckgo",
                            category=category
                        )
                        
                        # Only include results with valid URLs
                        if result.url and urlparse(result.url).scheme in ['http', 'https']:
                            results.append(result)
                            
                    except (KeyError, ValueError):
                        # Skip malformed results
                        continue
                        
            return results[:limit]
            
        except Exception as e:
            # Return empty list on error
            return []


class FallbackSearchAdapter(SearchAdapter):
    """Search adapter with automatic fallback from SearxNG to DuckDuckGo."""
    
    def __init__(self, 
                 searxng_url: str = "http://localhost:8888",
                 timeout: int = 10,
                 health_check_interval: int = 300):
        """Initialize fallback search adapter.
        
        Args:
            searxng_url: SearxNG instance URL
            timeout: Request timeout in seconds  
            health_check_interval: Seconds between health checks
        """
        self.primary = SearxNGAdapter(base_url=searxng_url, timeout=timeout)
        self.fallback = DuckDuckGoAdapter(timeout=timeout)
        self.health_check_interval = health_check_interval
        self.last_health_check = 0
        self.primary_available = None
        
    def _check_primary_health(self) -> bool:
        """Check primary adapter health with caching."""
        current_time = time.time()
        
        # Use cached result if recent
        if (self.primary_available is not None and 
            current_time - self.last_health_check < self.health_check_interval):
            return self.primary_available
            
        # Perform fresh health check
        self.primary_available = self.primary.health_check()
        self.last_health_check = current_time
        
        return self.primary_available
        
    def health_check(self) -> bool:
        """Check if any search adapter is available."""
        return self._check_primary_health() or self.fallback.health_check()
        
    def search(self, query: str, category: str = "general", limit: int = 10) -> List[SearchResult]:
        """Search with automatic fallback.
        
        Args:
            query: Search query string
            category: Search category (general, it, science)
            limit: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        if not query.strip():
            return []
            
        # Try primary (SearxNG) first if healthy
        if self._check_primary_health():
            results = self.primary.search(query, category, limit)
            if results:  # Got results from primary
                return results
                
        # Fall back to DuckDuckGo
        if self.fallback.health_check():
            return self.fallback.search(query, category, limit)
            
        # Both adapters failed
        return []
        
    def get_active_engine(self) -> str:
        """Get name of currently active search engine."""
        if self._check_primary_health():
            return "searxng"
        elif self.fallback.health_check():
            return "duckduckgo"
        else:
            return "none"


class StubSearchAdapter(SearchAdapter):
    """Stub search adapter for testing and offline mode."""
    
    def __init__(self):
        """Initialize stub adapter."""
        pass
        
    def health_check(self) -> bool:
        """Always available in offline mode."""
        return True
        
    def search(self, query: str, category: str = "general", limit: int = 10) -> List[SearchResult]:
        """Return deterministic stub results based on query."""
        if not query.strip():
            return []
            
        # Generate deterministic results based on query hash
        import hashlib
        query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
        
        results = []
        for i in range(min(limit, 3)):  # Return up to 3 stub results
            title_suffix = query_hash[i*2:i*2+2]
            results.append(SearchResult(
                title=f"{query} - Resource {i+1} ({title_suffix})",
                url=f"https://example.com/stub/{category}/{title_suffix}",
                snippet=f"This is a stub search result for '{query}' in category '{category}'. " +
                        f"Result {i+1} would contain relevant information about the query topic.",
                score=float(limit - i),
                engine="stub",
                category=category
            ))
            
        return results