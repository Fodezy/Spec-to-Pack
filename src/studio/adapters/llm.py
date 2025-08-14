"""LLM adapter for model interactions."""

from abc import ABC, abstractmethod
from typing import Any


class LLMAdapter(ABC):
    """Abstract LLM adapter interface."""

    @abstractmethod
    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate JSON output from prompt with schema constraints."""
        pass

    @abstractmethod
    def summarize(self, text: str) -> str:
        """Summarize the given text."""
        pass


class StubLLMAdapter(LLMAdapter):
    """Stub implementation for development/testing."""

    def generate_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate stub JSON response."""
        return {
            "response": "This is a stub response",
            "prompt_received": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "schema_type": schema.get("type", "unknown")
        }

    def summarize(self, text: str) -> str:
        """Generate stub summary."""
        return f"Summary of {len(text)} characters of text: {text[:100]}{'...' if len(text) > 100 else ''}"
