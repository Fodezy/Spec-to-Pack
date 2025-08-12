"""Vector store adapter for semantic search."""

from typing import List, Any, Dict
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Search result from vector store."""
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]


class VectorStoreAdapter(ABC):
    """Abstract vector store adapter interface."""
    
    @abstractmethod
    def index(self, doc_id: str, embedding: List[float], content: str = "", metadata: Dict[str, Any] = None) -> None:
        """Index a document with its embedding."""
        pass
    
    @abstractmethod
    def search(self, query_embedding: List[float], k: int = 10) -> List[SearchResult]:
        """Search for similar documents."""
        pass


class StubVectorStoreAdapter(VectorStoreAdapter):
    """Stub implementation for development/testing."""
    
    def __init__(self):
        self._documents = {}
    
    def index(self, doc_id: str, embedding: List[float], content: str = "", metadata: Dict[str, Any] = None) -> None:
        """Store document in memory (stub)."""
        self._documents[doc_id] = {
            "embedding": embedding,
            "content": content,
            "metadata": metadata or {}
        }
    
    def search(self, query_embedding: List[float], k: int = 10) -> List[SearchResult]:
        """Return stub search results."""
        results = []
        for doc_id, doc in list(self._documents.items())[:k]:
            results.append(SearchResult(
                id=doc_id,
                score=0.85,  # Stub score
                content=doc["content"],
                metadata=doc["metadata"]
            ))
        return results