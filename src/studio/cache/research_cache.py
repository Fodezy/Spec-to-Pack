"""Multi-level research cache with TTL management."""

import hashlib
import json
import shutil
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from ..types import ResearchDocument


class CacheLevel(Enum):
    """Cache levels with different TTL settings."""
    SEARCH_RESULTS = "search"      # 24 hours
    SCRAPED_CONTENT = "content"    # 7 days  
    EMBEDDINGS = "embeddings"      # 30 days
    RESEARCH_DOCS = "research"     # 14 days


class ResearchCacheManager:
    """Multi-level cache manager for research data."""
    
    def __init__(self, cache_dir: Path = None):
        """Initialize cache manager.
        
        Args:
            cache_dir: Cache directory (default: .cache/research)
        """
        if cache_dir is None:
            cache_dir = Path.cwd() / ".cache" / "research"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache TTL settings
        self.ttl_settings = {
            CacheLevel.SEARCH_RESULTS: timedelta(hours=24),
            CacheLevel.SCRAPED_CONTENT: timedelta(days=7),  
            CacheLevel.EMBEDDINGS: timedelta(days=30),
            CacheLevel.RESEARCH_DOCS: timedelta(days=14),
        }
        
    def _cache_key(self, level: CacheLevel, identifier: str) -> str:
        """Generate cache key from level and identifier.
        
        Args:
            level: Cache level
            identifier: Unique identifier for the cached item
            
        Returns:
            SHA-256 hash as cache key
        """
        key_data = f"{level.value}:{identifier}"
        return hashlib.sha256(key_data.encode()).hexdigest()
        
    def _cache_path(self, cache_key: str) -> Path:
        """Get cache file path with directory structure.
        
        Args:
            cache_key: Cache key hash
            
        Returns:
            Path to cache file with 2-level directory structure
        """
        # Create 2-level directory structure to avoid too many files in one dir
        return self.cache_dir / cache_key[:2] / cache_key[2:4] / f"{cache_key}.json"
        
    def get(self, level: CacheLevel, identifier: str) -> Optional[Dict[str, Any]]:
        """Get cached data if not expired.
        
        Args:
            level: Cache level
            identifier: Unique identifier
            
        Returns:
            Cached data dict or None if not found/expired
        """
        cache_key = self._cache_key(level, identifier)
        cache_path = self._cache_path(cache_key)
        
        if not cache_path.exists():
            return None
            
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # Check expiration
            cached_at = datetime.fromisoformat(cache_data['cached_at'])
            ttl = self.ttl_settings[level]
            
            if datetime.now() - cached_at > ttl:
                self._remove_cache_file(cache_path)
                return None
                
            return cache_data['data']
            
        except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
            # Remove corrupted cache file
            self._remove_cache_file(cache_path)
            return None
            
    def set(self, level: CacheLevel, identifier: str, data: Dict[str, Any]) -> bool:
        """Cache data with timestamp.
        
        Args:
            level: Cache level
            identifier: Unique identifier
            data: Data to cache
            
        Returns:
            True if cached successfully, False otherwise
        """
        cache_key = self._cache_key(level, identifier)
        cache_path = self._cache_path(cache_key)
        
        try:
            # Ensure directory exists
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            cache_entry = {
                'cached_at': datetime.now().isoformat(),
                'cache_level': level.value,
                'identifier': identifier,
                'cache_key': cache_key,
                'data': data
            }
            
            # Write cache file atomically
            temp_path = cache_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_path.replace(cache_path)
            return True
            
        except (OSError, TypeError) as e:
            return False
            
    def _remove_cache_file(self, cache_path: Path) -> None:
        """Safely remove cache file."""
        try:
            if cache_path.exists():
                cache_path.unlink()
                
            # Remove empty parent directories
            try:
                cache_path.parent.rmdir()
                cache_path.parent.parent.rmdir()
            except OSError:
                pass  # Directory not empty, which is fine
        except OSError:
            pass
            
    def clear_level(self, level: CacheLevel) -> int:
        """Clear all caches of specific level.
        
        Args:
            level: Cache level to clear
            
        Returns:
            Number of cache files cleared
        """
        cleared = 0
        
        if not self.cache_dir.exists():
            return 0
            
        for cache_file in self.cache_dir.rglob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                if cache_data.get('cache_level') == level.value:
                    self._remove_cache_file(cache_file)
                    cleared += 1
                    
            except (json.JSONDecodeError, OSError):
                # Remove corrupted files too
                self._remove_cache_file(cache_file)
                cleared += 1
                
        return cleared
        
    def clear_all(self) -> int:
        """Clear entire cache directory.
        
        Returns:
            Number of cache files cleared
        """
        if not self.cache_dir.exists():
            return 0
            
        # Count files before removal
        file_count = sum(1 for _ in self.cache_dir.rglob("*.json"))
        
        try:
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            return file_count
        except OSError:
            return 0
            
    def clear_expired(self) -> int:
        """Clear expired cache files.
        
        Returns:
            Number of expired files cleared
        """
        cleared = 0
        current_time = datetime.now()
        
        if not self.cache_dir.exists():
            return 0
            
        for cache_file in self.cache_dir.rglob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                # Check if expired
                cached_at = datetime.fromisoformat(cache_data['cached_at'])
                cache_level = CacheLevel(cache_data['cache_level'])
                ttl = self.ttl_settings[cache_level]
                
                if current_time - cached_at > ttl:
                    self._remove_cache_file(cache_file)
                    cleared += 1
                    
            except (json.JSONDecodeError, KeyError, ValueError, OSError):
                # Remove corrupted files
                self._remove_cache_file(cache_file)
                cleared += 1
                
        return cleared
        
    def cache_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get cache statistics.
        
        Returns:
            Statistics dict with counts and sizes per cache level
        """
        stats = {}
        total_files = 0
        total_size_mb = 0.0
        
        # Initialize stats for all levels
        for level in CacheLevel:
            stats[level.value] = {
                'count': 0,
                'size_mb': 0.0,
                'expired': 0
            }
        
        if not self.cache_dir.exists():
            stats['total'] = {'count': 0, 'size_mb': 0.0, 'expired': 0}
            return stats
            
        current_time = datetime.now()
        
        for cache_file in self.cache_dir.rglob("*.json"):
            try:
                file_size_mb = cache_file.stat().st_size / 1024 / 1024
                
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                level = cache_data.get('cache_level', 'unknown')
                if level in stats:
                    stats[level]['count'] += 1
                    stats[level]['size_mb'] += file_size_mb
                    
                    # Check if expired
                    try:
                        cached_at = datetime.fromisoformat(cache_data['cached_at'])
                        cache_level = CacheLevel(level)
                        ttl = self.ttl_settings[cache_level]
                        
                        if current_time - cached_at > ttl:
                            stats[level]['expired'] += 1
                    except (KeyError, ValueError):
                        stats[level]['expired'] += 1
                        
                total_files += 1
                total_size_mb += file_size_mb
                
            except (json.JSONDecodeError, OSError):
                total_files += 1
                if 'unknown' not in stats:
                    stats['unknown'] = {'count': 0, 'size_mb': 0.0, 'expired': 0}
                stats['unknown']['count'] += 1
                stats['unknown']['expired'] += 1
                
        # Add total stats
        stats['total'] = {
            'count': total_files,
            'size_mb': total_size_mb,
            'expired': sum(level_stats['expired'] for level_stats in stats.values() if 'expired' in level_stats)
        }
        
        return stats
        
    def cache_research_document(self, doc: ResearchDocument) -> bool:
        """Cache a research document.
        
        Args:
            doc: Research document to cache
            
        Returns:
            True if cached successfully
        """
        if not doc.provenance or not doc.provenance.source_url:
            return False
            
        identifier = doc.provenance.source_url
        data = doc.model_dump()
        
        return self.set(CacheLevel.RESEARCH_DOCS, identifier, data)
        
    def get_research_document(self, source_url: str) -> Optional[ResearchDocument]:
        """Get cached research document by source URL.
        
        Args:
            source_url: Source URL of the document
            
        Returns:
            ResearchDocument if found and not expired, None otherwise
        """
        data = self.get(CacheLevel.RESEARCH_DOCS, source_url)
        if data:
            try:
                return ResearchDocument(**data)
            except (TypeError, ValueError):
                return None
        return None
        
    def cache_search_results(self, query: str, category: str, results: list) -> bool:
        """Cache search results.
        
        Args:
            query: Search query
            category: Search category
            results: List of search results
            
        Returns:
            True if cached successfully
        """
        identifier = f"query:{query}:category:{category}"
        
        # Convert search results to serializable format
        data = {
            'query': query,
            'category': category,
            'results': [
                {
                    'title': result.title,
                    'url': result.url,
                    'snippet': result.snippet,
                    'score': result.score,
                    'engine': result.engine,
                    'category': result.category
                }
                for result in results
            ]
        }
        
        return self.set(CacheLevel.SEARCH_RESULTS, identifier, data)
        
    def get_search_results(self, query: str, category: str):
        """Get cached search results.
        
        Args:
            query: Search query
            category: Search category
            
        Returns:
            List of SearchResult objects if found, None otherwise
        """
        identifier = f"query:{query}:category:{category}"
        data = self.get(CacheLevel.SEARCH_RESULTS, identifier)
        
        if data and 'results' in data:
            # Convert back to SearchResult objects
            from ..adapters.search import SearchResult
            return [
                SearchResult(
                    title=result['title'],
                    url=result['url'],
                    snippet=result['snippet'],
                    score=result['score'],
                    engine=result['engine'],
                    category=result['category']
                )
                for result in data['results']
            ]
        
        return None
        
    def cache_embeddings(self, text: str, embedding: list[float], model_name: str) -> bool:
        """Cache text embeddings.
        
        Args:
            text: Original text
            embedding: Embedding vector
            model_name: Name of the embedding model
            
        Returns:
            True if cached successfully
        """
        identifier = f"model:{model_name}:text_hash:{hashlib.md5(text.encode()).hexdigest()}"
        
        data = {
            'text_hash': hashlib.md5(text.encode()).hexdigest(),
            'model_name': model_name,
            'embedding': embedding,
            'dimension': len(embedding)
        }
        
        return self.set(CacheLevel.EMBEDDINGS, identifier, data)
        
    def get_embeddings(self, text: str, model_name: str) -> Optional[list[float]]:
        """Get cached embeddings.
        
        Args:
            text: Original text
            model_name: Name of the embedding model
            
        Returns:
            Embedding vector if found, None otherwise
        """
        identifier = f"model:{model_name}:text_hash:{hashlib.md5(text.encode()).hexdigest()}"
        data = self.get(CacheLevel.EMBEDDINGS, identifier)
        
        if data and 'embedding' in data:
            return data['embedding']
        
        return None