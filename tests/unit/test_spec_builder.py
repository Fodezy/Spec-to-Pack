"""Unit tests for SpecBuilder."""

import pytest
from studio.spec_builder import SpecBuilder


def test_spec_builder_init():
    """Test SpecBuilder initialization."""
    builder = SpecBuilder()
    assert builder is not None


def test_merge_idea_decisions():
    """Test merging idea and decisions."""
    builder = SpecBuilder()
    spec = builder.merge_idea_decisions()
    
    assert spec is not None
    assert "meta" in spec
    assert "problem" in spec
    assert spec["meta"]["name"] == "Sample Spec"