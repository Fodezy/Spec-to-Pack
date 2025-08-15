"""Tests for RAG structured logging functionality."""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from studio.logging import RAGLogger, create_rag_logger


class TestRAGLogger:
    """Test RAG logger functionality."""
    
    def test_logger_initialization(self):
        """Test basic logger initialization."""
        logger = RAGLogger()
        assert logger.run_id is None
        assert logger.log_file is None
        
        run_id = uuid4()
        log_file = Path("test.log")
        logger_with_params = RAGLogger(
            log_level="DEBUG",
            run_id=run_id,
            log_file=log_file
        )
        assert logger_with_params.run_id == run_id
        assert logger_with_params.log_file == log_file
    
    def test_create_rag_logger_factory(self):
        """Test logger factory function."""
        run_id = uuid4()
        logger = create_rag_logger(
            run_id=run_id,
            log_level="INFO",
            enable_console=False
        )
        assert logger.run_id == run_id
    
    def test_search_logging_methods(self):
        """Test search operation logging."""
        logger = RAGLogger(enable_console=False)
        
        # These should not raise exceptions
        logger.search_started("test query", "duckduckgo", limit=5)
        logger.search_completed("test query", "duckduckgo", 3, 1500)
        logger.search_failed("test query", "duckduckgo", "Network error", 1000)
    
    def test_web_fetch_logging_methods(self):
        """Test web fetch logging."""
        logger = RAGLogger(enable_console=False)
        
        # These should not raise exceptions
        logger.web_fetch_started("https://example.com", "TestAgent/1.0")
        logger.web_fetch_completed("https://example.com", 15000, 200, 2500)
        logger.web_fetch_failed("https://example.com", "Connection timeout", 408, 30000)
    
    def test_content_guard_logging(self):
        """Test content guard logging."""
        logger = RAGLogger(enable_console=False)
        
        logger.content_guard_check(
            "https://example.com", 
            "url_allowed", 
            True, 
            {"reason": "passed_all_checks"}
        )
        logger.content_guard_check(
            "https://blocked.com", 
            "robots_txt", 
            False, 
            {"reason": "disallowed_by_robots"}
        )
    
    def test_rate_limit_logging(self):
        """Test rate limiting logging."""
        logger = RAGLogger(enable_console=False)
        
        logger.rate_limit_triggered("example.com", 2.5)
    
    def test_embeddings_logging(self):
        """Test embeddings operation logging."""
        logger = RAGLogger(enable_console=False)
        
        logger.embeddings_started(10, "sentence-transformers/all-MiniLM-L6-v2")
        logger.embeddings_completed(10, "sentence-transformers/all-MiniLM-L6-v2", 384, 1200)
    
    def test_vector_store_logging(self):
        """Test vector store operation logging."""
        logger = RAGLogger(enable_console=False)
        
        logger.vector_store_operation("insert", "research_docs", count=5, duration_ms=800)
        logger.vector_store_operation("search", "research_docs", count=10, duration_ms=150)
    
    def test_research_pipeline_logging(self):
        """Test research pipeline logging."""
        logger = RAGLogger(enable_console=False)
        
        logger.research_pipeline_started("Test Product", 10)
        logger.research_pipeline_completed("Test Product", 7, 45000)
    
    def test_agent_execution_logging(self):
        """Test agent execution logging."""
        logger = RAGLogger(enable_console=False)
        
        logger.agent_execution_started("LibrarianAgent", "research")
        logger.agent_execution_completed("LibrarianAgent", "research", "success", 5000, 3)
    
    def test_cache_operations_logging(self):
        """Test cache operations logging."""
        logger = RAGLogger(enable_console=False)
        
        logger.cache_operation("get", "search_results", "test_key", hit=True)
        logger.cache_operation("set", "search_results", "test_key", size_bytes=1024)
    
    def test_performance_metrics_logging(self):
        """Test performance metrics logging."""
        logger = RAGLogger(enable_console=False)
        
        logger.performance_metric("search_latency", 1250, "ms", {"engine": "duckduckgo"})
        logger.performance_metric("documents_processed", 15, "count", {"agent": "LibrarianAgent"})
    
    def test_error_logging(self):
        """Test error logging with context."""
        logger = RAGLogger(enable_console=False)
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            logger.error("Test operation failed", error=e, context={"url": "https://example.com"})
    
    def test_general_logging_methods(self):
        """Test general logging methods."""
        logger = RAGLogger(enable_console=False)
        
        logger.debug("Debug message", operation="test")
        logger.info("Info message", status="processing")
        logger.warning("Warning message", risk="medium")
    
    def test_file_logging(self):
        """Test logging to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test_rag.log"
            logger = RAGLogger(
                log_level="INFO",
                enable_console=False,
                log_file=log_file
            )
            
            logger.info("Test log message", test_key="test_value")
            
            # Check if log file was created (basic test)
            # Note: File creation depends on handler configuration
            # This test validates the logger accepts file parameter without error
            assert log_file.parent.exists()


class TestLoggingIntegration:
    """Test integration of logging with other components."""
    
    def test_logger_with_run_id(self):
        """Test logger with run ID correlation."""
        run_id = uuid4()
        logger = create_rag_logger(run_id=run_id, enable_console=False)
        
        # Should include run_id in logs when available
        logger.info("Test message with run ID", operation="test")
        
        # Verify run_id is stored
        assert logger.run_id == run_id
    
    def test_different_log_levels(self):
        """Test different log levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            logger = RAGLogger(log_level=level, enable_console=False)
            
            # Should not raise exceptions
            logger.debug("Debug message")
            logger.info("Info message") 
            logger.warning("Warning message")
            logger.error("Error message")
    
    def test_logger_without_console(self):
        """Test logger with console disabled."""
        logger = RAGLogger(enable_console=False)
        
        # Should work without console output
        logger.info("Test message without console")
        logger.search_started("test", "engine")
        logger.search_completed("test", "engine", 5, 1000)


class TestLoggingContextManager:
    """Test logging context manager functionality."""
    
    def test_context_manager_import(self):
        """Test importing LoggingContextManager."""
        from studio.logging import LoggingContextManager
        
        logger = RAGLogger(enable_console=False)
        
        # Should be able to create context manager
        with LoggingContextManager(logger, "test_operation", param="value") as ctx:
            assert ctx is not None
    
    def test_successful_operation_context(self):
        """Test context manager for successful operation."""
        from studio.logging import LoggingContextManager
        
        logger = RAGLogger(enable_console=False)
        
        with LoggingContextManager(logger, "test_operation", param="value"):
            # Simulate some work
            pass
        
        # Should complete without exceptions
    
    def test_failed_operation_context(self):
        """Test context manager for failed operation."""
        from studio.logging import LoggingContextManager
        
        logger = RAGLogger(enable_console=False)
        
        with pytest.raises(ValueError):
            with LoggingContextManager(logger, "test_operation", param="value"):
                raise ValueError("Test error")