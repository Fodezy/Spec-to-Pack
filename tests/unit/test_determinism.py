"""Unit tests for determinism utilities."""

import json
import pytest
from pathlib import Path
from studio.determinism import DeterminismUtils


def test_normalize_json():
    """Test JSON normalization with sorted keys."""
    data = {
        "z_key": "last",
        "a_key": "first", 
        "generated_at": "2025-01-01T00:00:00Z",
        "nested": {"b": 2, "a": 1}
    }
    
    result = DeterminismUtils.normalize_json(data)
    
    # Should exclude generated_at by default
    assert "generated_at" not in result
    # Should have sorted keys
    lines = result.split('\n')
    assert '"a_key"' in lines[1]  # First key after opening brace
    assert '"nested"' in lines[2]
    assert '"z_key"' in lines[-2]  # Last key before closing brace


def test_ensure_lf_newlines():
    """Test newline normalization."""
    # Test CRLF to LF
    result = DeterminismUtils.ensure_lf_newlines("line1\r\nline2\r\nline3")
    assert result == "line1\nline2\nline3"
    
    # Test CR to LF
    result = DeterminismUtils.ensure_lf_newlines("line1\rline2\rline3")
    assert result == "line1\nline2\nline3"
    
    # Test mixed
    result = DeterminismUtils.ensure_lf_newlines("line1\r\nline2\rline3\n")
    assert result == "line1\nline2\nline3\n"


def test_utc_timestamp():
    """Test UTC timestamp generation."""
    timestamp = DeterminismUtils.utc_timestamp()
    
    # Should end with Z (UTC indicator)
    assert timestamp.endswith('Z')
    # Should be valid ISO format
    assert 'T' in timestamp
    assert len(timestamp) > 10


def test_normalize_file_for_comparison(tmp_path):
    """Test file normalization for comparison."""
    # Create a test JSON file
    test_data = {
        "name": "test",
        "generated_at": "2025-01-01T00:00:00Z",
        "data": {"b": 2, "a": 1}
    }
    
    test_file = tmp_path / "test.json"
    with open(test_file, 'w') as f:
        json.dump(test_data, f, indent=2)
    
    result = DeterminismUtils.normalize_file_for_comparison(test_file)
    
    # Should exclude generated_at
    assert "generated_at" not in result
    # Should be normalized JSON
    assert '"name": "test"' in result