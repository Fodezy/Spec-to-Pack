"""Structured logging for RAG operations and runtime observability."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog


class RAGLogger:
    """Structured logger for RAG operations with configurable verbosity."""

    def __init__(
        self,
        log_level: str = "INFO",
        enable_console: bool = True,
        log_file: Path | None = None,
        run_id: UUID | None = None,
    ):
        """Initialize RAG logger.

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            enable_console: Whether to log to console
            log_file: Optional file path for log output
            run_id: Optional run ID for correlation
        """
        self.run_id = run_id
        self.log_file = log_file
        self._configure_logging(log_level, enable_console, log_file)
        self.logger = structlog.get_logger("rag")

    def _configure_logging(
        self, log_level: str, enable_console: bool, log_file: Path | None
    ) -> None:
        """Configure structlog with processors and outputs."""

        # Configure stdlib logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout if enable_console else None,
            level=getattr(logging, log_level.upper()),
        )

        # Define processors for structured logging
        processors = [
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Add log level
            structlog.stdlib.add_log_level,
            # Add logger name
            structlog.stdlib.add_logger_name,
            # Add run ID if available
            self._add_run_id,
            # Filter None processor to clean up event dict
            lambda _, __, event_dict: {
                k: v for k, v in event_dict.items() if v is not None
            },
        ]

        # Add caller info in debug mode
        if log_level.upper() == "DEBUG":
            processors.append(
                structlog.processors.CallsiteParameterAdder(
                    parameters=[
                        structlog.processors.CallsiteParameter.FUNC_NAME,
                        structlog.processors.CallsiteParameter.LINENO,
                    ]
                )
            )

        # Add file output if specified
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(str(log_file))
            file_handler.setLevel(getattr(logging, log_level.upper()))
            processors.append(structlog.stdlib.ProcessorFormatter.wrap_for_formatter)

        # Add JSON formatter for structured output
        if enable_console:
            processors.append(structlog.dev.ConsoleRenderer(colors=True))
        else:
            processors.append(structlog.processors.JSONRenderer())

        # Configure structlog
        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def _add_run_id(
        self, logger: Any, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Add run_id to log events if available."""
        if self.run_id:
            event_dict["run_id"] = str(self.run_id)
        return event_dict

    def search_started(self, query: str, engine: str, limit: int = None) -> None:
        """Log search operation start."""
        self.logger.info(
            "Search operation started",
            operation="search",
            query=query,
            engine=engine,
            limit=limit,
            stage="search",
        )

    def search_completed(
        self, query: str, engine: str, results_count: int, duration_ms: int
    ) -> None:
        """Log search operation completion."""
        self.logger.info(
            "Search operation completed",
            operation="search",
            query=query,
            engine=engine,
            results_count=results_count,
            duration_ms=duration_ms,
            stage="search",
            status="success",
        )

    def search_failed(
        self, query: str, engine: str, error: str, duration_ms: int
    ) -> None:
        """Log search operation failure."""
        self.logger.error(
            "Search operation failed",
            operation="search",
            query=query,
            engine=engine,
            error=error,
            duration_ms=duration_ms,
            stage="search",
            status="error",
        )

    def web_fetch_started(self, url: str, user_agent: str = None) -> None:
        """Log web content fetch start."""
        self.logger.info(
            "Web fetch started",
            operation="web_fetch",
            url=url,
            user_agent=user_agent,
            stage="content_retrieval",
        )

    def web_fetch_completed(
        self, url: str, content_length: int, status_code: int, duration_ms: int
    ) -> None:
        """Log web content fetch completion."""
        self.logger.info(
            "Web fetch completed",
            operation="web_fetch",
            url=url,
            content_length=content_length,
            status_code=status_code,
            duration_ms=duration_ms,
            stage="content_retrieval",
            status="success",
        )

    def web_fetch_failed(
        self, url: str, error: str, status_code: int = None, duration_ms: int = None
    ) -> None:
        """Log web content fetch failure."""
        self.logger.error(
            "Web fetch failed",
            operation="web_fetch",
            url=url,
            error=error,
            status_code=status_code,
            duration_ms=duration_ms,
            stage="content_retrieval",
            status="error",
        )

    def content_guard_check(
        self, url: str, action: str, result: bool, details: dict[str, Any] = None
    ) -> None:
        """Log content guard checks."""
        log_func = self.logger.info if result else self.logger.warning
        log_func(
            "Content guard check",
            operation="content_guard",
            url=url,
            action=action,
            result="allowed" if result else "blocked",
            details=details or {},
            stage="content_filtering",
        )

    def rate_limit_triggered(self, domain: str, delay_seconds: float) -> None:
        """Log rate limiting events."""
        self.logger.info(
            "Rate limit triggered",
            operation="rate_limit",
            domain=domain,
            delay_seconds=delay_seconds,
            stage="content_retrieval",
        )

    def embeddings_started(self, text_count: int, model_name: str = None) -> None:
        """Log embeddings generation start."""
        self.logger.info(
            "Embeddings generation started",
            operation="embeddings",
            text_count=text_count,
            model_name=model_name,
            stage="embeddings",
        )

    def embeddings_completed(
        self, text_count: int, model_name: str, dimension: int, duration_ms: int
    ) -> None:
        """Log embeddings generation completion."""
        self.logger.info(
            "Embeddings generation completed",
            operation="embeddings",
            text_count=text_count,
            model_name=model_name,
            dimension=dimension,
            duration_ms=duration_ms,
            stage="embeddings",
            status="success",
        )

    def vector_store_operation(
        self,
        operation: str,
        collection: str,
        count: int = None,
        duration_ms: int = None,
    ) -> None:
        """Log vector store operations."""
        self.logger.info(
            "Vector store operation",
            operation="vector_store",
            action=operation,
            collection=collection,
            count=count,
            duration_ms=duration_ms,
            stage="vector_storage",
        )

    def research_pipeline_started(self, spec_name: str, max_documents: int) -> None:
        """Log research pipeline start."""
        self.logger.info(
            "Research pipeline started",
            operation="research_pipeline",
            spec_name=spec_name,
            max_documents=max_documents,
            stage="research",
        )

    def research_pipeline_completed(
        self, spec_name: str, documents_found: int, total_duration_ms: int
    ) -> None:
        """Log research pipeline completion."""
        self.logger.info(
            "Research pipeline completed",
            operation="research_pipeline",
            spec_name=spec_name,
            documents_found=documents_found,
            total_duration_ms=total_duration_ms,
            stage="research",
            status="success",
        )

    def agent_execution_started(self, agent_name: str, stage: str) -> None:
        """Log agent execution start."""
        self.logger.info(
            "Agent execution started",
            operation="agent_execution",
            agent_name=agent_name,
            stage=stage,
        )

    def agent_execution_completed(
        self,
        agent_name: str,
        stage: str,
        status: str,
        duration_ms: int,
        artifacts_count: int = 0,
    ) -> None:
        """Log agent execution completion."""
        self.logger.info(
            "Agent execution completed",
            operation="agent_execution",
            agent_name=agent_name,
            stage=stage,
            status=status,
            duration_ms=duration_ms,
            artifacts_count=artifacts_count,
        )

    def cache_operation(
        self,
        operation: str,
        cache_type: str,
        key: str,
        hit: bool = None,
        size_bytes: int = None,
    ) -> None:
        """Log cache operations."""
        self.logger.debug(
            "Cache operation",
            operation="cache",
            action=operation,
            cache_type=cache_type,
            key=key,
            hit=hit,
            size_bytes=size_bytes,
            stage="caching",
        )

    def performance_metric(
        self,
        metric_name: str,
        value: int | float,
        unit: str,
        context: dict[str, Any] = None,
    ) -> None:
        """Log performance metrics."""
        self.logger.info(
            "Performance metric",
            operation="performance",
            metric_name=metric_name,
            value=value,
            unit=unit,
            context=context or {},
            stage="monitoring",
        )

    def error(
        self, message: str, error: Exception = None, context: dict[str, Any] = None
    ) -> None:
        """Log errors with context."""
        error_info = {}
        if error:
            error_info = {
                "error_type": type(error).__name__,
                "error_message": str(error),
            }

        self.logger.error(
            message, error_info=error_info, context=context or {}, status="error"
        )

    def debug(self, message: str, **kwargs) -> None:
        """Log debug information."""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info level message."""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, **kwargs)


class LoggingContextManager:
    """Context manager for RAG logging operations."""

    def __init__(self, logger: RAGLogger, operation: str, **kwargs):
        """Initialize context manager.

        Args:
            logger: RAG logger instance
            operation: Operation name for logging
            **kwargs: Additional context for logging
        """
        self.logger = logger
        self.operation = operation
        self.context = kwargs
        self.start_time = None

    def __enter__(self):
        """Enter context and log operation start."""
        self.start_time = datetime.utcnow()
        self.logger.info(f"{self.operation} started", **self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and log operation completion or failure."""
        end_time = datetime.utcnow()
        duration_ms = int((end_time - self.start_time).total_seconds() * 1000)

        if exc_type is None:
            self.logger.info(
                f"{self.operation} completed",
                duration_ms=duration_ms,
                status="success",
                **self.context,
            )
        else:
            context_with_error = {
                **self.context,
                "duration_ms": duration_ms,
                "status": "error",
                "error_type": exc_type.__name__,
                "error_message": str(exc_val),
            }
            self.logger.error(f"{self.operation} failed", context=context_with_error)


def create_rag_logger(
    run_id: UUID = None,
    log_level: str = "INFO",
    enable_console: bool = True,
    log_file: Path | None = None,
) -> RAGLogger:
    """Create and configure a RAG logger instance.

    Args:
        run_id: Run ID for correlation
        log_level: Logging level
        enable_console: Whether to enable console output
        log_file: Optional log file path

    Returns:
        Configured RAG logger instance
    """
    return RAGLogger(
        log_level=log_level,
        enable_console=enable_console,
        log_file=log_file,
        run_id=run_id,
    )
