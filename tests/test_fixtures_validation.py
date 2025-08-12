"""Test that validates fixtures against schemas."""

import json
import pytest
from pathlib import Path
import jsonschema

def test_valid_spec_fixture():
    """Test that valid_spec.json validates against source_spec.schema.json."""
    # Load schema
    schema_path = Path(__file__).parent.parent / "schemas" / "source_spec.schema.json"
    with open(schema_path) as f:
        schema = json.load(f)
    
    # Load valid fixture
    fixture_path = Path(__file__).parent / "fixtures" / "valid_spec.json"
    with open(fixture_path) as f:
        spec = json.load(f)
    
    # Should validate without errors
    jsonschema.validate(spec, schema)


def test_invalid_spec_fixture():
    """Test that invalid_spec.json fails validation with expected errors."""
    # Load schema
    schema_path = Path(__file__).parent.parent / "schemas" / "source_spec.schema.json"
    with open(schema_path) as f:
        schema = json.load(f)
    
    # Load invalid fixture
    fixture_path = Path(__file__).parent / "fixtures" / "invalid_spec.json"
    with open(fixture_path) as f:
        spec = json.load(f)
    
    # Should fail validation
    with pytest.raises(jsonschema.ValidationError) as exc_info:
        jsonschema.validate(spec, schema)
    
    # Check that it fails on missing 'meta' field
    error = exc_info.value
    assert "'meta' is a required property" in str(error.message)


def test_schema_self_validation():
    """Test that schemas validate against JSON Schema Draft 2020-12 meta-schema."""
    from jsonschema.validators import Draft202012Validator
    
    schema_dir = Path(__file__).parent.parent / "schemas"
    for schema_file in schema_dir.glob("*.schema.json"):
        with open(schema_file) as f:
            schema = json.load(f)
        
        # Should validate against meta-schema
        Draft202012Validator.check_schema(schema)