"""Embeddings adapters for semantic text processing."""

import hashlib
from abc import ABC, abstractmethod
from typing import Optional


class EmbeddingsAdapter(ABC):
    """Abstract embeddings adapter interface."""

    @abstractmethod
    def encode(self, text: str) -> list[float]:
        """Encode text into embedding vector."""
        pass

    @abstractmethod
    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple texts into embedding vectors."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get embedding dimension."""
        pass


class BGEEmbeddingsAdapter(EmbeddingsAdapter):
    """BGE (BAAI General Embedding) adapter using sentence-transformers."""
    
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", cache_dir: Optional[str] = None):
        """Initialize BGE embeddings model."""
        self.model_name = model_name
        self.cache_dir = cache_dir
        self._model = None
        self._dimension = None
        
    def _load_model(self):
        """Lazy load the embeddings model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError("BGEEmbeddingsAdapter requires sentence-transformers. Install with: pip install 'studio[rag]'")
            
            self._model = SentenceTransformer(
                self.model_name,
                cache_folder=self.cache_dir
            )
            
            # Determine dimension by encoding a test string
            test_embedding = self._model.encode("test")
            self._dimension = len(test_embedding)
        
        return self._model
        
    def encode(self, text: str) -> list[float]:
        """Encode single text into embedding vector."""
        model = self._load_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
        
    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple texts into embedding vectors."""
        model = self._load_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return [emb.tolist() for emb in embeddings]
        
    @property 
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is None:
            self._load_model()  # This will set _dimension
        return self._dimension


class CachedEmbeddingsAdapter(EmbeddingsAdapter):
    """Embeddings adapter with hash-based caching."""
    
    def __init__(self, base_adapter: EmbeddingsAdapter, cache_size: int = 1000):
        """Initialize with base adapter and cache settings."""
        self.base_adapter = base_adapter
        self.cache_size = cache_size
        self._cache = {}
        
    def _get_text_hash(self, text: str) -> str:
        """Get hash key for text."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
        
    def encode(self, text: str) -> list[float]:
        """Encode with caching."""
        text_hash = self._get_text_hash(text)
        
        if text_hash in self._cache:
            return self._cache[text_hash]
            
        # Generate embedding using base adapter
        embedding = self.base_adapter.encode(text)
        
        # Store in cache with LRU eviction
        if len(self._cache) >= self.cache_size:
            # Remove oldest entry (simple FIFO for now)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            
        self._cache[text_hash] = embedding
        return embedding
        
    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode batch with caching."""
        results = []
        uncached_texts = []
        uncached_indices = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            text_hash = self._get_text_hash(text)
            if text_hash in self._cache:
                results.append(self._cache[text_hash])
            else:
                results.append(None)  # Placeholder
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Encode uncached texts in batch
        if uncached_texts:
            uncached_embeddings = self.base_adapter.encode_batch(uncached_texts)
            
            # Fill in results and cache
            for idx, embedding in zip(uncached_indices, uncached_embeddings):
                results[idx] = embedding
                text_hash = self._get_text_hash(texts[idx])
                
                # Store in cache with eviction
                if len(self._cache) >= self.cache_size:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                    
                self._cache[text_hash] = embedding
        
        return results
        
    @property
    def dimension(self) -> int:
        """Get embedding dimension from base adapter."""
        return self.base_adapter.dimension


class DualModelEmbeddingsAdapter(EmbeddingsAdapter):
    """Dual model embeddings adapter with query and content models."""
    
    def __init__(self, 
                 query_model: str = "BAAI/bge-small-en-v1.5",
                 content_model: str = "BAAI/bge-base-en-v1.5", 
                 cache_dir: Optional[str] = None):
        """Initialize dual model embeddings adapter.
        
        Args:
            query_model: Model for queries and tool calls (384d)
            content_model: Model for documents and content (768d)
            cache_dir: Cache directory for models
        """
        self.query_model_name = query_model
        self.content_model_name = content_model
        self.cache_dir = cache_dir
        self._query_model = None
        self._content_model = None
        self._query_dimension = None
        self._content_dimension = None
        
    def _load_query_model(self):
        """Lazy load the query embeddings model."""
        if self._query_model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError("DualModelEmbeddingsAdapter requires sentence-transformers. Install with: pip install 'studio[rag]'")
            
            self._query_model = SentenceTransformer(
                self.query_model_name,
                cache_folder=self.cache_dir
            )
            
            # Determine dimension
            test_embedding = self._query_model.encode("test")
            self._query_dimension = len(test_embedding)
        
        return self._query_model
        
    def _load_content_model(self):
        """Lazy load the content embeddings model."""
        if self._content_model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError("DualModelEmbeddingsAdapter requires sentence-transformers. Install with: pip install 'studio[rag]'")
            
            self._content_model = SentenceTransformer(
                self.content_model_name,
                cache_folder=self.cache_dir
            )
            
            # Determine dimension
            test_embedding = self._content_model.encode("test")
            self._content_dimension = len(test_embedding)
        
        return self._content_model
    
    def encode_query(self, text: str) -> list[float]:
        """Encode query text using query model (384d)."""
        model = self._load_query_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
        
    def encode_content(self, text: str) -> list[float]:
        """Encode content text using content model (768d)."""
        model = self._load_content_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
        
    def encode_batch_queries(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple queries using query model."""
        model = self._load_query_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return [emb.tolist() for emb in embeddings]
        
    def encode_batch_content(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple content texts using content model."""
        model = self._load_content_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return [emb.tolist() for emb in embeddings]
    
    def encode(self, text: str) -> list[float]:
        """Default encode using content model for backward compatibility."""
        return self.encode_content(text)
        
    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Default batch encode using content model for backward compatibility."""
        return self.encode_batch_content(texts)
        
    @property
    def dimension(self) -> int:
        """Get content model dimension (default for compatibility)."""
        if self._content_dimension is None:
            self._load_content_model()  # This will set _content_dimension
        return self._content_dimension
        
    @property
    def query_dimension(self) -> int:
        """Get query model dimension."""
        if self._query_dimension is None:
            self._load_query_model()  # This will set _query_dimension
        return self._query_dimension
        
    @property
    def content_dimension(self) -> int:
        """Get content model dimension."""
        if self._content_dimension is None:
            self._load_content_model()  # This will set _content_dimension
        return self._content_dimension
        
    def cross_similarity(self, query: str, content: str) -> float:
        """Calculate cross-model similarity between query and content.
        
        Args:
            query: Query text (encoded with query model)
            content: Content text (encoded with content model)
            
        Returns:
            Cosine similarity score between query and content embeddings
        """
        import numpy as np
        
        query_emb = np.array(self.encode_query(query))
        content_emb = np.array(self.encode_content(content))
        
        # For cross-model similarity, we need to handle different dimensions
        # Use a simple approach: pad or truncate to match dimensions
        if len(query_emb) < len(content_emb):
            # Pad query embedding to match content
            padded_query = np.pad(query_emb, (0, len(content_emb) - len(query_emb)), 'constant')
            similarity = np.dot(padded_query, content_emb) / (np.linalg.norm(padded_query) * np.linalg.norm(content_emb))
        elif len(query_emb) > len(content_emb):
            # Pad content embedding to match query
            padded_content = np.pad(content_emb, (0, len(query_emb) - len(content_emb)), 'constant')
            similarity = np.dot(query_emb, padded_content) / (np.linalg.norm(query_emb) * np.linalg.norm(padded_content))
        else:
            # Same dimensions
            similarity = np.dot(query_emb, content_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(content_emb))
            
        return float(similarity)


class StubEmbeddingsAdapter(EmbeddingsAdapter):
    """Stub embeddings adapter for testing."""
    
    def __init__(self, dimension: int = 384):
        self._dimension = dimension
        
    def encode(self, text: str) -> list[float]:
        """Return stub embedding based on text hash."""
        # Create deterministic embedding from text hash
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        # Use hash to create pseudo-random but deterministic values
        values = []
        for i in range(self._dimension):
            # Use modulo to cycle through the hash characters
            hash_idx = (i * 2) % len(text_hash)
            hex_chars = text_hash[hash_idx:hash_idx + 2]
            if len(hex_chars) < 2:
                hex_chars = text_hash[hash_idx] + text_hash[0]  # Wrap around if needed
            byte_val = int(hex_chars, 16)
            values.append((byte_val - 128) / 128.0)  # Normalize to [-1, 1]
        return values
        
    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Return stub embeddings for batch."""
        return [self.encode(text) for text in texts]
        
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension