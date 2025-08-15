"""Integration tests for PlaywrightBrowserAdapter."""

import uuid
from pathlib import Path

import pytest

from studio.agents.base import LibrarianAgent
from studio.artifacts import Blackboard
from studio.types import Dials, Meta, Problem, ResearchContext, RunContext, SourceSpec


@pytest.mark.integration
def test_librarian_agent_with_real_browser_adapter():
    """Test LibrarianAgent with real PlaywrightBrowserAdapter fetching content."""
    # Create test context
    run_ctx = RunContext(
        run_id=uuid.uuid4(),
        offline=False,  # Enable real browser fetching
        dials=Dials(),
        out_dir=Path("./test_output")
    )
    
    spec = SourceSpec(
        meta=Meta(name="Test RAG Integration", version="1.0.0"),
        problem=Problem(statement="Test real content fetching with browser adapter"),
        research_context=ResearchContext(
            search_domains=["https://httpbin.org/html"],  # Reliable test URL
            max_documents=1,
            include_embeddings=False  # Skip embeddings for faster test
        )
    )
    
    blackboard = Blackboard()
    agent = LibrarianAgent()
    
    # Run the agent
    result = agent.run(run_ctx, spec, blackboard)
    
    # Verify results
    assert result.status == "ok"
    assert result.notes["action"] == "research_completed"
    assert result.notes["documents_fetched"] > 0
    assert result.notes["errors"] == 0
    
    # Verify real content was fetched
    research_docs = blackboard.notes.get("research_documents", [])
    assert len(research_docs) > 0
    
    first_doc = research_docs[0]
    assert first_doc.content
    assert len(first_doc.content) > 100  # Should have substantial content
    assert "Herman Melville" in first_doc.content  # httpbin.org/html content
    
    # Verify provenance tracking
    assert first_doc.provenance.source_url == "https://httpbin.org/html"
    assert first_doc.provenance.content_hash
    assert first_doc.provenance.chunk_id


@pytest.mark.integration
def test_librarian_agent_browser_adapter_selection():
    """Test that LibrarianAgent correctly selects browser adapter based on context."""
    # Test offline mode uses stub
    offline_ctx = RunContext(
        run_id=uuid.uuid4(),
        offline=True,
        dials=Dials(),
        out_dir=Path("./test_output")
    )
    
    spec = SourceSpec(
        meta=Meta(name="Test", version="1.0.0"),
        problem=Problem(statement="Test problem"),
        research_context=ResearchContext()
    )
    
    blackboard = Blackboard()
    agent = LibrarianAgent()
    
    # Should skip research in offline mode
    result = agent.run(offline_ctx, spec, blackboard)
    assert result.status == "ok"
    assert result.notes["action"] == "skipped_research"
    assert result.notes["reason"] == "offline_mode"
    
    # Test online mode uses PlaywrightBrowserAdapter
    online_ctx = RunContext(
        run_id=uuid.uuid4(),
        offline=False,
        dials=Dials(),
        out_dir=Path("./test_output")
    )
    
    # Add a simple domain for testing
    spec.research_context.search_domains = ["https://httpbin.org/html"]
    spec.research_context.max_documents = 1
    
    agent = LibrarianAgent()
    result = agent.run(online_ctx, spec, blackboard)
    
    assert result.status == "ok"
    assert result.notes["action"] == "research_completed"
    assert agent.browser_adapter.__class__.__name__ == "PlaywrightBrowserAdapter"


@pytest.mark.integration 
def test_playwright_browser_adapter_error_handling():
    """Test PlaywrightBrowserAdapter handles errors gracefully."""
    from studio.adapters.browser import PlaywrightBrowserAdapter
    
    adapter = PlaywrightBrowserAdapter()
    
    # Test invalid URL handling
    result = adapter.fetch("invalid-url", offline_mode=False)
    assert result.status_code == 500
    assert "error" in result.headers
    
    # Test timeout handling with very short timeout
    adapter_short_timeout = PlaywrightBrowserAdapter(timeout_ms=1)
    result = adapter_short_timeout.fetch("https://httpbin.org/delay/5", offline_mode=False)
    assert result.status_code == 500