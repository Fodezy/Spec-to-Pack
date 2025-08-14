"""Tests for LibrarianAgent."""

import uuid
from pathlib import Path

import pytest

from studio.adapters.browser import StubBrowserAdapter
from studio.adapters.embeddings import StubEmbeddingsAdapter
from studio.adapters.vector_store import StubVectorStoreAdapter
from studio.agents.base import LibrarianAgent
from studio.artifacts import Blackboard
from studio.types import (
    Dials,
    Meta,
    Problem,
    ResearchContext,
    RunContext,
    SourceSpec,
    Status,
)


@pytest.fixture
def sample_spec():
    """Create a sample spec for testing."""
    return SourceSpec(
        meta=Meta(name="Test Project", version="1.0.0"),
        problem=Problem(statement="Test problem statement"),
        research_context=ResearchContext(
            search_domains=["https://example.com/docs"],
            max_documents=2,
            include_embeddings=True
        )
    )


@pytest.fixture
def run_context():
    """Create a run context for testing."""
    return RunContext(
        run_id=uuid.uuid4(),
        offline=False,
        dials=Dials(),
        out_dir=Path("/tmp/test_out")
    )


@pytest.fixture
def offline_run_context():
    """Create an offline run context for testing."""
    return RunContext(
        run_id=uuid.uuid4(),
        offline=True,
        dials=Dials(),
        out_dir=Path("/tmp/test_out")
    )


def test_librarian_agent_offline_mode(sample_spec, offline_run_context):
    """Test LibrarianAgent respects offline mode."""
    agent = LibrarianAgent()
    blackboard = Blackboard()
    
    result = agent.run(offline_run_context, sample_spec, blackboard)
    
    assert result.status == Status.OK.value
    assert result.notes["action"] == "skipped_research"
    assert result.notes["reason"] == "offline_mode"
    assert len(result.artifacts) == 0


def test_librarian_agent_with_stub_adapters(sample_spec, run_context):
    """Test LibrarianAgent with stub adapters."""
    browser_adapter = StubBrowserAdapter()
    vector_store_adapter = StubVectorStoreAdapter()
    embeddings_adapter = StubEmbeddingsAdapter()
    
    agent = LibrarianAgent(
        browser_adapter=browser_adapter,
        vector_store_adapter=vector_store_adapter,
        embeddings_model=embeddings_adapter
    )
    
    blackboard = Blackboard()
    result = agent.run(run_context, sample_spec, blackboard)
    
    assert result.status == Status.OK.value
    assert result.notes["action"] == "research_completed"
    assert result.notes["documents_fetched"] >= 0
    assert "research_documents" in blackboard.notes


def test_librarian_agent_research_context_empty_domains(sample_spec, run_context):
    """Test LibrarianAgent when no search domains are provided."""
    # Modify spec to have empty search domains
    sample_spec.research_context.search_domains = []
    
    agent = LibrarianAgent()
    blackboard = Blackboard()
    
    result = agent.run(run_context, sample_spec, blackboard)
    
    assert result.status == Status.OK.value
    assert result.notes["action"] == "research_completed"
    # Should fall back to generated URLs


def test_librarian_agent_provenance_tracking(sample_spec, run_context):
    """Test that LibrarianAgent creates proper provenance records."""
    agent = LibrarianAgent()
    blackboard = Blackboard()
    
    result = agent.run(run_context, sample_spec, blackboard)
    
    research_docs = blackboard.notes.get("research_documents", [])
    
    for doc in research_docs:
        assert hasattr(doc, 'provenance')
        assert hasattr(doc.provenance, 'source_url')
        assert hasattr(doc.provenance, 'retrieved_at')
        assert hasattr(doc.provenance, 'chunk_id')
        assert hasattr(doc.provenance, 'content_hash')


def test_librarian_agent_embeddings_integration(sample_spec, run_context):
    """Test LibrarianAgent integrates embeddings correctly."""
    embeddings_adapter = StubEmbeddingsAdapter(dimension=128)
    
    agent = LibrarianAgent(embeddings_model=embeddings_adapter)
    blackboard = Blackboard()
    
    result = agent.run(run_context, sample_spec, blackboard)
    
    assert result.status == Status.OK.value
    assert result.notes["embeddings_enabled"] == True
    
    research_docs = blackboard.notes.get("research_documents", [])
    
    # Check that embeddings are included for docs
    for doc in research_docs:
        if doc.embedding is not None:
            assert len(doc.embedding) == 128  # Stub dimension


def test_librarian_agent_vector_store_indexing(sample_spec, run_context):
    """Test LibrarianAgent indexes documents in vector store."""
    vector_store = StubVectorStoreAdapter()
    embeddings_adapter = StubEmbeddingsAdapter()
    
    agent = LibrarianAgent(
        vector_store_adapter=vector_store,
        embeddings_model=embeddings_adapter
    )
    blackboard = Blackboard()
    
    result = agent.run(run_context, sample_spec, blackboard)
    
    assert result.status == Status.OK.value
    assert result.notes["vector_store_used"] == True
    
    # Verify documents were indexed in vector store
    assert len(vector_store._documents) > 0


def test_librarian_agent_error_handling(sample_spec, run_context):
    """Test LibrarianAgent error handling."""
    class FailingBrowserAdapter(StubBrowserAdapter):
        def fetch(self, url: str, offline_mode: bool = False):
            raise Exception("Network error")
    
    agent = LibrarianAgent(browser_adapter=FailingBrowserAdapter())
    blackboard = Blackboard()
    
    result = agent.run(run_context, sample_spec, blackboard)
    
    # Should handle errors gracefully and continue
    assert result.status == Status.OK.value
    assert result.notes["action"] == "research_completed"
    assert result.notes["errors"] > 0


def test_librarian_agent_max_documents_limit(sample_spec, run_context):
    """Test LibrarianAgent respects max_documents limit."""
    sample_spec.research_context.max_documents = 1
    sample_spec.research_context.search_domains = [
        "https://example.com/doc1",
        "https://example.com/doc2", 
        "https://example.com/doc3"
    ]
    
    agent = LibrarianAgent()
    blackboard = Blackboard()
    
    result = agent.run(run_context, sample_spec, blackboard)
    
    assert result.notes["urls_processed"] <= 1


def test_generate_research_urls():
    """Test URL generation from problem statement."""
    agent = LibrarianAgent()
    
    urls = agent._generate_research_urls("web application development")
    
    assert len(urls) > 0
    assert all(url.startswith("http") for url in urls)


def test_generate_embeddings_stub():
    """Test stub embeddings generation."""
    agent = LibrarianAgent()
    
    embeddings = agent._generate_embeddings("test text")
    
    assert len(embeddings) == 384  # BGE-small dimension
    assert all(isinstance(val, float) for val in embeddings)