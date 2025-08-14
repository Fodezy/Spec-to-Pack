"""Unit tests for SpecBuilder."""

import yaml

from studio.spec_builder import SpecBuilder
from studio.types import SourceSpec


def test_spec_builder_init():
    """Test SpecBuilder initialization."""
    builder = SpecBuilder()
    assert builder is not None


def test_merge_idea_decisions_no_files():
    """Test merging with no input files."""
    builder = SpecBuilder()
    spec, dials = builder.merge_idea_decisions()

    assert isinstance(spec, SourceSpec)
    assert spec.meta.name == "Generated Spec"
    assert spec.problem.statement == "Placeholder problem statement"

    # Verify default dials
    from studio.types import Dials
    assert isinstance(dials, Dials)


def test_merge_idea_decisions_with_files(tmp_path):
    """Test merging with idea and decision files."""
    # Create idea file
    idea_data = {
        "name": "Test Feature",
        "description": "A test feature",
        "problem": "Users need to test things"
    }
    idea_file = tmp_path / "idea.yaml"
    with open(idea_file, 'w') as f:
        yaml.dump(idea_data, f)

    # Create decisions file
    decisions_data = {
        "offline": False,
        "budget_tokens": 50000,
        "audience_mode": "deep",
        "development_flow": "kanban",
        "test_depth": "full_matrix"
    }
    decisions_file = tmp_path / "decisions.yaml"
    with open(decisions_file, 'w') as f:
        yaml.dump(decisions_data, f)

    # Merge files
    builder = SpecBuilder()
    spec, dials = builder.merge_idea_decisions(idea_file, decisions_file)

    assert isinstance(spec, SourceSpec)
    assert spec.meta.name == "Test Feature"
    assert spec.meta.description == "A test feature"
    assert spec.problem.statement == "Users need to test things"
    assert not spec.constraints.offline_ok
    assert spec.constraints.budget_tokens == 50000

    # Verify Dials mapping from decisions
    from studio.types import Dials
    assert isinstance(dials, Dials)
    assert dials.audience_mode.value == "deep"
    assert dials.development_flow.value == "kanban"
    assert dials.test_depth.value == "full_matrix"


def test_merge_with_missing_files(tmp_path):
    """Test merging with non-existent files."""
    nonexistent_file = tmp_path / "missing.yaml"

    builder = SpecBuilder()
    spec, dials = builder.merge_idea_decisions(nonexistent_file, nonexistent_file)

    # Should use defaults when files don't exist
    assert isinstance(spec, SourceSpec)
    assert spec.meta.name == "Generated Spec"

    from studio.types import Dials
    assert isinstance(dials, Dials)
