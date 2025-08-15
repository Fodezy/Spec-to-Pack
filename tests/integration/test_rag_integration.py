"""Integration tests for RAG (Research-Augmented Generation) pipeline."""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from studio.adapters.browser import StubBrowserAdapter
from studio.adapters.embeddings import StubEmbeddingsAdapter
from studio.adapters.search import StubSearchAdapter
from studio.adapters.vector_store import StubVectorStoreAdapter
from studio.agents.base import LibrarianAgent, PRDWriterAgent
from studio.artifacts import Blackboard
from studio.cache import ResearchCacheManager
from studio.guards.content_guards import ContentGuard
from studio.guards.network_guards import enforce_offline_mode
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
def temp_cache_dir():
    """Create temporary cache directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_spec():
    """Create sample spec for testing."""
    return SourceSpec(
        meta=Meta(name="Test Product", version="1.0.0"),
        problem=Problem(
            statement="Build an AI-powered task management system",
            context="Users need better task organization and prioritization"
        ),
        research_context=ResearchContext(
            max_documents=5,
            include_embeddings=True,
            search_domains=[]  # Will use generated URLs
        )
    )


@pytest.fixture
def run_context(temp_output_dir):
    """Create run context for testing."""
    return RunContext(
        run_id=uuid4(),
        offline=True,  # Use offline mode for testing
        out_dir=temp_output_dir,
        dials=Dials()
    )


@pytest.fixture
def blackboard():
    """Create blackboard for agent communication."""
    return Blackboard()


class TestLibrarianAgentRAG:
    """Test LibrarianAgent with RAG components."""
    
    def test_librarian_with_stub_adapters(self, sample_spec, run_context, blackboard):
        """Test LibrarianAgent with stub adapters in offline mode."""
        # Initialize with stub adapters
        librarian = LibrarianAgent(
            browser_adapter=StubBrowserAdapter(),
            vector_store_adapter=StubVectorStoreAdapter(),
            embeddings_model=StubEmbeddingsAdapter()
        )
        
        # Should skip research in offline mode
        result = librarian.run(run_context, sample_spec, blackboard)
        
        assert result.status == Status.OK.value
        assert result.notes["action"] == "skipped_research"
        assert result.notes["reason"] == "offline_mode"
        
    def test_librarian_offline_enforcement(self, sample_spec, run_context, blackboard):
        """Test that LibrarianAgent enforces offline mode."""
        librarian = LibrarianAgent()
        
        # Run in offline mode
        result = librarian.run(run_context, sample_spec, blackboard)
        
        # Should enforce offline mode and skip research
        assert result.status == Status.OK.value
        assert "offline" in result.notes.get("reason", "")
        
    def test_librarian_content_guards_integration(self, sample_spec, run_context, blackboard):
        """Test LibrarianAgent integration with content guards."""
        librarian = LibrarianAgent(
            browser_adapter=StubBrowserAdapter(),
            vector_store_adapter=StubVectorStoreAdapter(), 
            embeddings_model=StubEmbeddingsAdapter()
        )
        
        # Enable online mode for this test (but use stub adapters)
        run_context.offline = False
        enforce_offline_mode(False)
        
        try:
            result = librarian.run(run_context, sample_spec, blackboard)
            
            # Should complete successfully with stub adapters
            assert result.status == Status.OK.value
            
            # Should have processed some URLs (from stub generator)
            if "urls_processed" in result.notes:
                assert result.notes["urls_processed"] >= 0
                
        finally:
            # Clean up - re-enable offline mode
            enforce_offline_mode(True)
            run_context.offline = True


class TestPRDWriterAgentRAG:
    """Test PRDWriterAgent with RAG integration."""
    
    def test_prd_writer_without_research(self, sample_spec, run_context, blackboard, temp_output_dir):
        """Test PRDWriterAgent without research data."""
        prd_writer = PRDWriterAgent()
        
        result = prd_writer.run(run_context, sample_spec, blackboard)
        
        assert result.status == Status.OK.value
        assert result.notes["action"] == "prd_generated"
        assert len(result.artifacts) == 2  # PRD + test plan
        
        # Check PRD file was created
        prd_path = temp_output_dir / "prd.md"
        assert prd_path.exists()
        
        # Check content doesn't have research sections
        prd_content = prd_path.read_text()
        assert "Research Summary" not in prd_content
        assert "Evidence & Market Analysis" not in prd_content
        assert "References" not in prd_content
        
    def test_prd_writer_with_mock_research(self, sample_spec, run_context, blackboard, temp_output_dir):
        """Test PRDWriterAgent with mock research data."""
        from studio.types import ContentProvenance, ResearchDocument
        from datetime import datetime
        
        # Create mock research documents
        mock_research_docs = [
            ResearchDocument(
                content="Machine learning systems require careful attention to data quality and model validation. Market research shows increasing demand for AI-powered productivity tools.",
                provenance=ContentProvenance(
                    source_url="https://example.com/ml-best-practices",
                    retrieved_at=datetime.utcnow(),
                    chunk_id="test-chunk-1",
                    content_hash="test-hash-1"
                )
            ),
            ResearchDocument(
                content="Task management applications benefit from intelligent prioritization algorithms. Technical implementation often involves machine learning classification models.",
                provenance=ContentProvenance(
                    source_url="https://example.com/task-management-tech",
                    retrieved_at=datetime.utcnow(),
                    chunk_id="test-chunk-2", 
                    content_hash="test-hash-2"
                )
            )
        ]
        
        # Add research to blackboard
        blackboard.notes["research_documents"] = mock_research_docs
        
        prd_writer = PRDWriterAgent()
        result = prd_writer.run(run_context, sample_spec, blackboard)
        
        assert result.status == Status.OK.value
        assert result.notes["action"] == "prd_generated"
        
        # Check PRD file includes research sections
        prd_path = temp_output_dir / "prd.md"
        assert prd_path.exists()
        
        prd_content = prd_path.read_text()
        assert "Research Summary" in prd_content
        assert "Evidence & Market Analysis" in prd_content
        assert "References" in prd_content
        assert "Research-augmented with 2 sources" in prd_content
        
        # Check evidence categorization
        assert "Market Evidence" in prd_content or "Technical Evidence" in prd_content
        assert "Citation 1" in prd_content
        assert "Citation 2" in prd_content
        assert "example.com" in prd_content
        
    def test_research_evidence_categorization(self, sample_spec, run_context, blackboard):
        """Test research evidence categorization logic."""
        from studio.types import ContentProvenance, ResearchDocument
        from datetime import datetime
        
        # Create documents with different keyword profiles
        research_docs = [
            ResearchDocument(
                content="Market analysis shows strong user demand and revenue potential for productivity software. Customer adoption rates are increasing.",
                provenance=ContentProvenance(
                    source_url="https://example.com/market-research",
                    retrieved_at=datetime.utcnow(),
                    chunk_id="market-doc",
                    content_hash="market-hash"
                )
            ),
            ResearchDocument(
                content="Technical architecture considerations include scalability, performance optimization, and security implementation patterns for web applications.",
                provenance=ContentProvenance(
                    source_url="https://example.com/tech-guide",
                    retrieved_at=datetime.utcnow(),
                    chunk_id="tech-doc",
                    content_hash="tech-hash"
                )
            ),
            ResearchDocument(
                content="Competitor analysis reveals market alternatives and comparison points. Competitor products show various feature sets and market positioning.",
                provenance=ContentProvenance(
                    source_url="https://example.com/competitors",
                    retrieved_at=datetime.utcnow(),
                    chunk_id="comp-doc",
                    content_hash="comp-hash"
                )
            )
        ]
        
        blackboard.notes["research_documents"] = research_docs
        
        prd_writer = PRDWriterAgent()
        
        # Test evidence extraction
        evidence = prd_writer._extract_research_evidence(research_docs, "AI task management")
        
        # Should have categorized evidence
        assert len(evidence["market_evidence"]) > 0
        assert len(evidence["technical_evidence"]) > 0
        assert len(evidence["competitive_evidence"]) > 0
        assert len(evidence["citations"]) == 3
        
        # Check citation structure
        for citation in evidence["citations"]:
            assert "id" in citation
            assert "url" in citation
            assert "title" in citation
            assert "retrieved_at" in citation
            assert "snippet" in citation
            
    def test_research_methodology_disclosure(self, sample_spec, run_context, blackboard):
        """Test research methodology transparency."""
        from studio.types import ContentProvenance, ResearchDocument
        from datetime import datetime
        
        research_docs = [
            ResearchDocument(
                content="Sample research content",
                provenance=ContentProvenance(
                    source_url="https://domain1.com/page",
                    retrieved_at=datetime.utcnow(),
                    chunk_id="doc1",
                    content_hash="hash1"
                )
            ),
            ResearchDocument(
                content="More research content",
                provenance=ContentProvenance(
                    source_url="https://domain2.com/page",
                    retrieved_at=datetime.utcnow(),
                    chunk_id="doc2",
                    content_hash="hash2"
                )
            )
        ]
        
        prd_writer = PRDWriterAgent()
        methodology = prd_writer._get_research_methodology(research_docs)
        
        assert methodology["sources_count"] == 2
        assert methodology["unique_domains"] == 2
        assert "LibrarianAgent" in methodology["data_collection"]
        assert "Keyword-based" in methodology["analysis_method"]
        assert "limitations" in methodology["limitations"].lower()
        
    def test_empty_research_handling(self, sample_spec, run_context, blackboard):
        """Test handling when no research data is available."""
        prd_writer = PRDWriterAgent()
        
        # Test with empty research documents
        evidence = prd_writer._extract_research_evidence([], "test problem")
        
        assert evidence["market_evidence"] == []
        assert evidence["technical_evidence"] == []
        assert evidence["competitive_evidence"] == []
        assert evidence["citations"] == []
        assert "No research data available" in evidence["summary"]
        
        # Test methodology with no research
        methodology = prd_writer._get_research_methodology([])
        
        assert methodology["sources_count"] == 0
        assert "No research conducted" in methodology["data_collection"]


class TestEndToEndRAGPipeline:
    """Test complete end-to-end RAG pipeline."""
    
    def test_librarian_to_prd_pipeline(self, sample_spec, run_context, blackboard, temp_output_dir):
        """Test complete pipeline from LibrarianAgent to PRDWriterAgent."""
        # Set up offline mode with stub adapters
        run_context.offline = False  # Allow LibrarianAgent to run
        enforce_offline_mode(False)
        
        try:
            # Initialize agents with stub adapters
            librarian = LibrarianAgent(
                browser_adapter=StubBrowserAdapter(),
                vector_store_adapter=StubVectorStoreAdapter(),
                embeddings_model=StubEmbeddingsAdapter()
            )
            
            prd_writer = PRDWriterAgent()
            
            # Run LibrarianAgent first
            librarian_result = librarian.run(run_context, sample_spec, blackboard)
            assert librarian_result.status == Status.OK.value
            
            # Research documents should be in blackboard
            research_docs = blackboard.notes.get("research_documents", [])
            
            # Run PRDWriterAgent with research data
            prd_result = prd_writer.run(run_context, sample_spec, blackboard)
            assert prd_result.status == Status.OK.value
            
            # Check PRD includes research if any was generated
            prd_path = temp_output_dir / "prd.md"
            assert prd_path.exists()
            
            prd_content = prd_path.read_text()
            
            if research_docs:
                # Should include research sections
                assert "Research Summary" in prd_content
                assert "Research-augmented" in prd_content
            else:
                # Should work without research
                assert "Research Summary" not in prd_content
                
        finally:
            # Clean up
            enforce_offline_mode(True)
            run_context.offline = True
            
    def test_cache_integration(self, sample_spec, run_context, blackboard, temp_cache_dir):
        """Test RAG pipeline with caching enabled."""
        cache_manager = ResearchCacheManager(cache_dir=temp_cache_dir)
        
        # Test cache operations
        test_data = {"query": "test", "results": ["result1", "result2"]}
        
        # Set and get data
        success = cache_manager.set("SEARCH_RESULTS", "test_key", test_data)
        assert success
        
        retrieved = cache_manager.get("SEARCH_RESULTS", "test_key")
        assert retrieved == test_data
        
        # Check stats
        stats = cache_manager.get_stats()
        assert stats.total_entries >= 1
        
    def test_content_guards_in_pipeline(self, sample_spec, run_context, blackboard):
        """Test content guards integration in pipeline."""
        content_guard = ContentGuard(
            max_doc_tokens=100,
            max_docs_per_domain=2,
            respect_robots_txt=False
        )
        
        # Test URL checking
        test_url = "https://example.com/test"
        content_guard.check_url_allowed(test_url)  # Should not raise
        
        # Test content size limits
        large_content = "Test content " * 100
        processed = content_guard.check_content_size(large_content, test_url)
        
        assert len(processed) < len(large_content)
        assert "[Content truncated" in processed
        
        # Record successful fetch
        content_guard.record_successful_fetch(test_url)
        
        stats = content_guard.get_domain_stats()
        assert "example.com" in stats
        assert stats["example.com"]["documents_fetched"] == 1
        
    def test_search_adapter_integration(self):
        """Test search adapter integration."""
        search_adapter = StubSearchAdapter()
        
        assert search_adapter.health_check()
        
        results = search_adapter.search("AI task management", limit=3)
        assert len(results) <= 3
        
        for result in results:
            assert hasattr(result, 'title')
            assert hasattr(result, 'url')
            assert hasattr(result, 'snippet')
            assert result.engine == "stub"
            
    def test_dual_embeddings_integration(self):
        """Test dual embeddings adapter integration."""
        embeddings_adapter = StubEmbeddingsAdapter(dimension=384)
        
        # Test basic encoding
        query_embedding = embeddings_adapter.encode("test query")
        content_embedding = embeddings_adapter.encode("test content")
        
        assert len(query_embedding) == 384
        assert len(content_embedding) == 384
        
        # Test batch encoding
        batch_results = embeddings_adapter.encode_batch(["text1", "text2", "text3"])
        assert len(batch_results) == 3
        assert all(len(emb) == 384 for emb in batch_results)
        
    @pytest.mark.integration
    def test_error_handling_in_pipeline(self, sample_spec, run_context, blackboard):
        """Test error handling throughout the RAG pipeline."""
        # Test with malformed spec
        broken_spec = SourceSpec(
            meta=Meta(name="Broken", version="1.0.0"),
            problem=Problem(statement="Test problem"),
            research_context=None  # Missing research context
        )
        
        librarian = LibrarianAgent()
        result = librarian.run(run_context, broken_spec, blackboard)
        
        # Should handle missing research context gracefully
        assert result.status == Status.OK.value
        
        # Test PRD writer with broken data
        blackboard.notes["research_documents"] = ["invalid", "data", "structure"]
        
        prd_writer = PRDWriterAgent()
        prd_result = prd_writer.run(run_context, sample_spec, blackboard)
        
        # Should handle invalid research data gracefully
        assert prd_result.status == Status.OK.value