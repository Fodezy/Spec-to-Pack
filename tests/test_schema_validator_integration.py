"""Integration tests for SchemaValidator with fixtures."""

import json
from pathlib import Path
from src.studio.validation import SchemaValidator
from src.studio.types import SourceSpec


def test_schema_validator_with_valid_fixture():
    """Test SchemaValidator with valid fixture."""
    # Load valid fixture as JSON
    fixture_path = Path(__file__).parent / "fixtures" / "valid_spec.json"
    with open(fixture_path) as f:
        spec_data = json.load(f)
    
    # Create SourceSpec from fixture data
    spec = SourceSpec(**spec_data)
    
    # Validate with SchemaValidator
    validator = SchemaValidator()
    result = validator.validate(spec)
    
    assert result.ok
    assert len(result.errors) == 0


def test_schema_validator_with_invalid_fixture():
    """Test SchemaValidator with invalid fixture."""
    # Load invalid fixture as JSON
    fixture_path = Path(__file__).parent / "fixtures" / "invalid_spec.json"
    with open(fixture_path) as f:
        spec_data = json.load(f)
    
    # Add required fields to make it parseable by Pydantic
    spec_data["meta"] = {"name": "Invalid Spec", "version": "1.0.0"}
    spec_data["success_metrics"] = {"metrics": []}
    
    # Create SourceSpec
    spec = SourceSpec(**spec_data)
    
    # Validate with SchemaValidator
    validator = SchemaValidator()
    result = validator.validate(spec)
    
    # Should be valid since we added the missing fields
    assert result.ok