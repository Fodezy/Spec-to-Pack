"""Vector store adapter for semantic search."""

import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class SearchResult:
    """Search result from vector store."""
    id: str
    score: float
    content: str
    metadata: dict[str, Any]


class VectorStoreAdapter(ABC):
    """Abstract vector store adapter interface."""

    @abstractmethod
    def index(self, doc_id: str, embedding: list[float], content: str = "", metadata: dict[str, Any] = None) -> None:
        """Index a document with its embedding."""
        pass

    @abstractmethod
    def search(self, query_embedding: list[float], k: int = 10) -> list[SearchResult]:
        """Search for similar documents."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the vector store connection."""
        pass


class LanceDBVectorStoreAdapter(VectorStoreAdapter):
    """LanceDB-based vector store adapter."""
    
    def __init__(self, db_path: Optional[str] = None, table_name: str = "research_docs"):
        """Initialize LanceDB vector store."""
        self.db_path = db_path or os.path.join(tempfile.gettempdir(), "studio_vector_db")
        self.table_name = table_name
        self._db = None
        self._table = None
        
    def _get_db(self):
        """Lazy load LanceDB connection."""
        if self._db is None:
            try:
                import lancedb
            except ImportError:
                raise ImportError("LanceDBVectorStoreAdapter requires lancedb. Install with: pip install 'studio[rag]'")
            
            # Ensure db directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._db = lancedb.connect(self.db_path)
            
        return self._db
        
    def _get_table(self):
        """Get or create table."""
        if self._table is None:
            db = self._get_db()
            
            # Check if table exists
            try:
                self._table = db.open_table(self.table_name)
            except Exception:
                # Create table if it doesn't exist
                import pyarrow as pa
                
                # Define schema for the table
                schema = pa.schema([
                    pa.field("id", pa.string()),
                    pa.field("vector", pa.list_(pa.float32())),
                    pa.field("content", pa.string()),
                    pa.field("source_url", pa.string()),
                    pa.field("retrieved_at", pa.string()),
                    pa.field("chunk_id", pa.string()),
                    pa.field("content_hash", pa.string()),
                    pa.field("metadata", pa.string())  # JSON string
                ])
                
                # Create empty table
                self._table = db.create_table(self.table_name, schema=schema)
                
        return self._table
        
    def index(self, doc_id: str, embedding: list[float], content: str = "", metadata: dict[str, Any] = None) -> None:
        """Index a document with its embedding."""
        import json
        import pyarrow as pa
        
        table = self._get_table()
        
        # Prepare data
        metadata = metadata or {}
        data = [{
            "id": doc_id,
            "vector": embedding,
            "content": content,
            "source_url": metadata.get("source_url", ""),
            "retrieved_at": metadata.get("retrieved_at", ""),
            "chunk_id": metadata.get("chunk_id", doc_id),
            "content_hash": metadata.get("content_hash", ""),
            "metadata": json.dumps(metadata)
        }]
        
        # Convert to PyArrow table
        pa_table = pa.Table.from_pylist(data)
        
        # Add to LanceDB table
        table.add(pa_table)
        
    def search(self, query_embedding: list[float], k: int = 10) -> list[SearchResult]:
        """Search for similar documents."""
        import json
        
        try:
            table = self._get_table()
            
            # Perform vector search
            results = table.search(query_embedding).limit(k).to_list()
            
            search_results = []
            for result in results:
                try:
                    metadata = json.loads(result.get("metadata", "{}"))
                except json.JSONDecodeError:
                    metadata = {}
                    
                search_results.append(SearchResult(
                    id=result["id"],
                    score=result.get("_distance", 0.0),  # LanceDB uses distance, lower is better
                    content=result.get("content", ""),
                    metadata=metadata
                ))
                
            return search_results
            
        except Exception:
            # Return empty results on error
            return []
            
    def close(self) -> None:
        """Close the vector store connection."""
        self._table = None
        self._db = None


class QdrantVectorStoreAdapter(VectorStoreAdapter):
    """Qdrant-based vector store adapter."""
    
    def __init__(self, host: str = "localhost", port: int = 6333, collection_name: str = "research_docs"):
        """Initialize Qdrant vector store."""
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self._client = None
        
    def _get_client(self):
        """Lazy load Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.models import Distance, VectorParams
            except ImportError:
                raise ImportError("QdrantVectorStoreAdapter requires qdrant-client. Install with: pip install 'studio[rag]'")
            
            self._client = QdrantClient(host=self.host, port=self.port)
            
            # Create collection if it doesn't exist
            try:
                self._client.get_collection(self.collection_name)
            except Exception:
                # Create collection with default settings
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)  # BGE-small default
                )
                
        return self._client
        
    def index(self, doc_id: str, embedding: list[float], content: str = "", metadata: dict[str, Any] = None) -> None:
        """Index a document with its embedding."""
        from qdrant_client.models import PointStruct
        
        client = self._get_client()
        metadata = metadata or {}
        metadata["content"] = content
        
        point = PointStruct(
            id=doc_id,
            vector=embedding,
            payload=metadata
        )
        
        client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
    def search(self, query_embedding: list[float], k: int = 10) -> list[SearchResult]:
        """Search for similar documents."""
        try:
            client = self._get_client()
            
            results = client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=k
            )
            
            search_results = []
            for result in results:
                search_results.append(SearchResult(
                    id=str(result.id),
                    score=result.score,
                    content=result.payload.get("content", ""),
                    metadata=result.payload
                ))
                
            return search_results
            
        except Exception:
            return []
            
    def close(self) -> None:
        """Close the vector store connection."""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None


class StubVectorStoreAdapter(VectorStoreAdapter):
    """Stub implementation for development/testing."""

    def __init__(self):
        self._documents = {}

    def index(self, doc_id: str, embedding: list[float], content: str = "", metadata: dict[str, Any] = None) -> None:
        """Store document in memory (stub)."""
        self._documents[doc_id] = {
            "embedding": embedding,
            "content": content,
            "metadata": metadata or {}
        }

    def search(self, query_embedding: list[float], k: int = 10) -> list[SearchResult]:
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
        
    def close(self) -> None:
        """Close stub vector store (no-op)."""
        pass
