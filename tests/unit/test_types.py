"""Unit tests for core types."""

import pytest
from studio.types import (
    SourceSpec, Meta, Problem, Constraints, Dials,
    AudienceMode, PackType, Status, ValidationResult, ValidationError
)


def test_source_spec_creation():
    """Test SourceSpec creation with required fields."""
    meta = Meta(name="Test Spec", version="1.0.0")
    problem = Problem(statement="Test problem statement")
    
    spec = SourceSpec(meta=meta, problem=problem)
    
    assert spec.meta.name == "Test Spec"
    assert spec.problem.statement == "Test problem statement"
    assert spec.is_valid()


def test_source_spec_with_all_fields():
    """Test SourceSpec with all optional fields."""
    spec_data = {
        "meta": {"name": "Full Spec", "version": "2.0.0", "description": "A complete spec"},
        "problem": {"statement": "Complex problem", "context": "Business context"},
        "constraints": {"offline_ok": False, "budget_tokens": 100000},
        "success_metrics": {"metrics": ["p95 < 2s", "accuracy > 95%"]},
        "diagram_scope": {"include_sequence": True, "include_lifecycle": False},
        "contracts_data": {"generate_schemas": True, "api_specs": ["users", "orders"]},
        "test_strategy": {"unit_tests": True, "e2e_tests": True},
        "operations": {"ci_cd": True, "monitoring": True},
        "export": {"formats": ["markdown", "pdf"], "bundle": True}
    }
    
    spec = SourceSpec(**spec_data)
    
    assert spec.meta.description == "A complete spec"
    assert spec.problem.context == "Business context"
    assert spec.constraints.budget_tokens == 100000
    assert len(spec.success_metrics.metrics) == 2
    assert spec.export.bundle == True


def test_dials_creation():
    """Test Dials creation with enums."""
    dials = Dials(
        audience_mode=AudienceMode.DEEP,
        development_flow="agile", 
        test_depth="full_matrix"
    )
    
    assert dials.audience_mode == AudienceMode.DEEP
    assert dials.development_flow.value == "agile"
    assert dials.test_depth.value == "full_matrix"


def test_validation_result():
    """Test ValidationResult with errors."""
    errors = [
        ValidationError(json_pointer="/meta/name", message="Name is required"),
        ValidationError(json_pointer="/problem/statement", message="Statement too short")
    ]
    
    result = ValidationResult(ok=False, errors=errors)
    
    assert not result.ok
    assert len(result.errors) == 2
    assert result.errors[0].json_pointer == "/meta/name"


def test_enum_values():
    """Test enum value conversion."""
    assert PackType.BALANCED.value == "balanced"
    assert Status.OK.value == "ok"
    assert AudienceMode.BRIEF.value == "brief"


def test_spec_model_validation():
    """Test Pydantic validation on SourceSpec."""
    # This should raise ValidationError due to missing required fields
    with pytest.raises(Exception):
        SourceSpec()
    
    # This should work with minimal required fields
    spec = SourceSpec(
        meta=Meta(name="Test", version="1.0.0"),
        problem=Problem(statement="Test problem")
    )
    assert spec.is_valid()