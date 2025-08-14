"""Unit tests for StudioApp."""

from studio.app import StudioApp
from studio.artifacts import ArtifactIndex
from studio.types import Meta, PackType, Problem, SourceSpec


def test_studio_app_init():
    """Test StudioApp initialization."""
    app = StudioApp()
    assert app.schema_validator is not None
    assert app.orchestrator is not None
    assert app.spec_builder is not None


def test_validate_valid_spec():
    """Test validating a valid spec."""
    app = StudioApp()
    spec = SourceSpec(
        meta=Meta(name="Test Spec", version="1.0.0"),
        problem=Problem(statement="Test problem")
    )

    result = app.validate(spec)
    assert result.ok
    assert len(result.errors) == 0


def test_generate_from_spec(tmp_path):
    """Test generating from a SourceSpec."""
    app = StudioApp()
    spec = SourceSpec(
        meta=Meta(name="Test Spec", version="1.0.0"),
        problem=Problem(statement="Test problem")
    )

    result = app.generate(
        spec=spec,
        pack=PackType.BALANCED,
        out_dir=tmp_path,
        offline=True
    )

    assert isinstance(result, ArtifactIndex)
    assert result.run_id is not None
    assert len(result.artifacts) > 0  # Should have some artifacts from stub agents


def test_generate_from_files_missing_files(tmp_path):
    """Test generating from missing files uses defaults."""
    app = StudioApp()

    result = app.generate_from_files(
        idea_path=None,
        decisions_path=None,
        pack=PackType.BALANCED,
        out_dir=tmp_path,
        offline=True
    )

    assert isinstance(result, ArtifactIndex)
    assert result.run_id is not None


def test_package_artifacts():
    """Test packaging artifacts into zip."""
    app = StudioApp()

    # Create a simple artifact index
    index = ArtifactIndex(
        run_id="12345678-1234-1234-1234-123456789012",
        generated_at="2025-01-01T00:00:00Z"
    )

    # Package would create zip (stub implementation)
    zip_artifact = app.package(index)

    assert zip_artifact.format == "zip"
    assert "bundle" in zip_artifact.name
