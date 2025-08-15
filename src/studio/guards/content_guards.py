"""Content security guards for RAG system."""

import time
from collections import defaultdict
from typing import Dict, Optional, Set
from urllib.parse import urlparse

import requests

from ..logging import RAGLogger


class ContentGuard:
    """Security guard for content processing with limits and compliance checks."""
    
    def __init__(self, 
                 respect_robots_txt: bool = True,
                 max_doc_tokens: int = 8000,
                 max_docs_per_domain: int = 3,
                 rate_limit_delay: float = 2.0,
                 logger: Optional[RAGLogger] = None):
        """Initialize content guard.
        
        Args:
            respect_robots_txt: Whether to check robots.txt before fetching
            max_doc_tokens: Maximum tokens per document (~6000 words)
            max_docs_per_domain: Maximum documents per domain
            rate_limit_delay: Delay between requests to same domain (seconds)
            logger: Optional RAG logger for structured logging
        """
        self.respect_robots_txt = respect_robots_txt
        self.max_doc_tokens = max_doc_tokens
        self.max_docs_per_domain = max_docs_per_domain
        self.rate_limit_delay = rate_limit_delay
        self.logger = logger
        
        # Track requests per domain
        self.domain_request_count: Dict[str, int] = defaultdict(int)
        self.domain_last_request: Dict[str, float] = {}
        self.robots_cache: Dict[str, bool] = {}
        
    def check_url_allowed(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt and domain limits.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is allowed, False otherwise
            
        Raises:
            ValueError: If URL exceeds domain limits or violates robots.txt
        """
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Check domain request limits
        if self.domain_request_count[domain] >= self.max_docs_per_domain:
            if self.logger:
                self.logger.content_guard_check(
                    url, "domain_limit", False, 
                    {"current_count": self.domain_request_count[domain], 
                     "limit": self.max_docs_per_domain}
                )
            raise ValueError(f"Domain limit exceeded: {domain} (max {self.max_docs_per_domain})")
        
        # Check robots.txt if enabled
        if self.respect_robots_txt:
            if not self._check_robots_txt(domain, url):
                if self.logger:
                    self.logger.content_guard_check(url, "robots_txt", False)
                raise ValueError(f"URL blocked by robots.txt: {url}")
        
        if self.logger:
            self.logger.content_guard_check(url, "url_allowed", True)
                
        return True
        
    def check_rate_limit(self, url: str) -> None:
        """Check and enforce rate limiting for domain.
        
        Args:
            url: URL being requested
        """
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        current_time = time.time()
        
        # Check if we need to wait
        if domain in self.domain_last_request:
            time_since_last = current_time - self.domain_last_request[domain]
            if time_since_last < self.rate_limit_delay:
                wait_time = self.rate_limit_delay - time_since_last
                if self.logger:
                    self.logger.rate_limit_triggered(domain, wait_time)
                time.sleep(wait_time)
        
        # Update last request time
        self.domain_last_request[domain] = time.time()
        
    def record_successful_fetch(self, url: str) -> None:
        """Record successful fetch for domain counting.
        
        Args:
            url: URL that was successfully fetched
        """
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        self.domain_request_count[domain] += 1
        
    def check_content_size(self, content: str, url: str) -> str:
        """Check and truncate content if it exceeds size limits.
        
        Args:
            content: Content to check
            url: Source URL for logging
            
        Returns:
            Potentially truncated content
        """
        # Rough token estimation: 1 token ≈ 4 characters for English
        estimated_tokens = len(content) // 4
        
        if estimated_tokens > self.max_doc_tokens:
            # Truncate to max tokens while preserving structure
            max_chars = self.max_doc_tokens * 4
            truncated = content[:max_chars]
            
            # Try to truncate at sentence boundary
            last_period = truncated.rfind('.')
            if last_period > max_chars * 0.8:  # If sentence boundary is reasonably close
                truncated = truncated[:last_period + 1]
            
            if self.logger:
                self.logger.content_guard_check(
                    url, "content_truncated", True,
                    {"original_tokens": estimated_tokens, 
                     "max_tokens": self.max_doc_tokens,
                     "original_length": len(content),
                     "truncated_length": len(truncated)}
                )
                
            return truncated + f"\n\n[Content truncated at {self.max_doc_tokens} tokens]"
        
        return content
        
    def _check_robots_txt(self, domain: str, url: str) -> bool:
        """Check if URL is allowed by robots.txt.
        
        Args:
            domain: Domain to check
            url: Full URL to check
            
        Returns:
            True if allowed, False if blocked
        """
        # Check cache first
        cache_key = f"{domain}:robots"
        if cache_key in self.robots_cache:
            return self.robots_cache[cache_key]
        
        try:
            robots_url = f"{domain}/robots.txt"
            response = requests.get(robots_url, timeout=5)
            
            if response.status_code == 200:
                robots_content = response.text
                
                # Simple robots.txt parsing for User-agent: *
                lines = robots_content.split('\n')
                current_user_agent = None
                disallowed_paths = []
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('User-agent:'):
                        user_agent = line.split(':', 1)[1].strip()
                        if user_agent == '*':
                            current_user_agent = '*'
                        else:
                            current_user_agent = None
                    elif line.startswith('Disallow:') and current_user_agent == '*':
                        path = line.split(':', 1)[1].strip()
                        if path:
                            disallowed_paths.append(path)
                
                # Check if URL path is disallowed
                parsed = urlparse(url)
                url_path = parsed.path
                
                for disallowed_path in disallowed_paths:
                    if url_path.startswith(disallowed_path):
                        self.robots_cache[cache_key] = False
                        return False
                        
                # Not explicitly disallowed
                self.robots_cache[cache_key] = True
                return True
                
            else:
                # No robots.txt or error accessing it - allow by default
                self.robots_cache[cache_key] = True
                return True
                
        except Exception:
            # Error checking robots.txt - allow by default but be conservative
            self.robots_cache[cache_key] = True
            return True
            
    def get_domain_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics about domain usage.
        
        Returns:
            Dict with domain stats
        """
        stats = {}
        for domain, count in self.domain_request_count.items():
            stats[domain] = {
                'requests': count,
                'remaining': max(0, self.max_docs_per_domain - count),
                'limit': self.max_docs_per_domain
            }
        return stats
        
    def reset_domain_limits(self) -> None:
        """Reset domain request counters."""
        self.domain_request_count.clear()
        self.domain_last_request.clear()