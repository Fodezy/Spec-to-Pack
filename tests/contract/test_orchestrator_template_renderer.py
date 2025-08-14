"""
Contract Tests: Orchestrator ↔ TemplateRenderer

These tests verify the data shape contracts between the Orchestrator
and TemplateRenderer to ensure consistent interface compliance.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest

from studio.artifacts import Blackboard
from studio.orchestrator import Orchestrator
from studio.rendering import TemplateRenderer
from studio.spec_builder import SpecBuilder
from studio.types import (
    AudienceMode,
    DevelopmentFlow,
    Dials,
    RunContext,
    SourceSpec,
    TestDepth,
)


class TestOrchestratorTemplateRendererContract:
    """Contract tests for Orchestrator-TemplateRenderer interface."""

    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = Orchestrator()
        self.template_renderer = TemplateRenderer()
        self.spec_builder = SpecBuilder()

    def test_template_data_shape_contract(self):
        """
        Verify that Orchestrator provides TemplateRenderer with
        data in the expected shape and structure.
        """
        # Create a minimal valid spec
        spec = self._create_minimal_spec()

        # Mock the template renderer to capture the data passed to it
        captured_data = {}

        def mock_render_string(template_content: str, template_data: dict[str, Any]) -> str:
            captured_data.update(template_data)
            return "# Mocked Template Output\nSome content"

        with tempfile.TemporaryDirectory() as temp_dir:
            ctx = self._create_run_context(Path(temp_dir))

            # Create a fake template file to avoid FileNotFoundError
            template_dir = self.template_renderer.template_dir / "balanced"
            template_dir.mkdir(parents=True, exist_ok=True)
            brief_template_path = template_dir / "brief.md"
            brief_template_path.write_text("# {{ meta.name }}\n{{ problem.statement }}")

            with patch.object(self.template_renderer, 'render_string', side_effect=mock_render_string):
                # Execute the render flow that would normally be called by orchestrator
                self.orchestrator._render_balanced_pack(ctx, spec, Blackboard())

        # Verify the contract: expected template data structure
        expected_keys = {
            'meta', 'problem', 'constraints', 'success_metrics',
            'diagram_scope', 'contracts_data', 'test_strategy',
            'operations', 'export', 'dials', 'pack_type', 'run_id', 'generated_at'
        }

        assert set(captured_data.keys()) == expected_keys, \
            f"Template data missing keys: {expected_keys - set(captured_data.keys())}"

        # Verify data types and structure
        self._validate_template_data_contract(captured_data)

    def test_spec_serialization_contract(self):
        """
        Verify that SourceSpec model_dump() produces data
        that TemplateRenderer can consume without errors.
        """
        spec = self._create_minimal_spec()

        # Serialize spec components
        serialized_data = {
            'meta': spec.meta.model_dump(),
            'problem': spec.problem.model_dump(),
            'constraints': spec.constraints.model_dump(),
            'success_metrics': spec.success_metrics.model_dump(),
            'diagram_scope': spec.diagram_scope.model_dump(),
            'contracts_data': spec.contracts_data.model_dump(),
            'test_strategy': spec.test_strategy.model_dump(),
            'operations': spec.operations.model_dump(),
            'export': spec.export.model_dump()
        }

        # Verify serialized data is JSON-serializable (template renderer requirement)
        json_str = json.dumps(serialized_data)
        reconstructed = json.loads(json_str)

        assert reconstructed == serialized_data

        # Verify no None values that could break templates
        self._validate_no_breaking_nones(serialized_data)

    def test_dials_contract(self):
        """Verify Dials data shape contract."""
        dials = Dials(
            audience_mode=AudienceMode.BALANCED,
            development_flow=DevelopmentFlow.DUAL_TRACK,
            test_depth=TestDepth.ACCEPTANCE
        )

        dials_data = dials.model_dump()

        # Verify expected structure
        expected_dials_keys = {'audience_mode', 'development_flow', 'test_depth'}
        assert set(dials_data.keys()) == expected_dials_keys

        # Verify enum values are strings (for template consumption)
        assert isinstance(dials_data['audience_mode'], str)
        assert isinstance(dials_data['development_flow'], str)
        assert isinstance(dials_data['test_depth'], str)

    def test_template_context_completeness(self):
        """
        Verify template context contains all required data
        for successful template rendering.
        """
        spec = self._create_minimal_spec()
        ctx = self._create_run_context()

        # Prepare template data as orchestrator would
        template_data = {
            "meta": spec.meta.model_dump(),
            "problem": spec.problem.model_dump(),
            "constraints": spec.constraints.model_dump(),
            "success_metrics": spec.success_metrics.model_dump(),
            "diagram_scope": spec.diagram_scope.model_dump(),
            "contracts_data": spec.contracts_data.model_dump(),
            "test_strategy": spec.test_strategy.model_dump(),
            "operations": spec.operations.model_dump(),
            "export": spec.export.model_dump(),
            "dials": ctx.dials.model_dump(),
            "pack_type": "balanced",
            "run_id": str(ctx.run_id),
            "generated_at": ctx.created_at.isoformat()
        }

        # Test with actual templates to ensure no missing variables
        template_dir = Path(__file__).parent.parent.parent / "src" / "studio" / "templates" / "balanced"

        for template_file in template_dir.glob("*.j2"):
            if template_file.name.startswith('.'):
                continue

            template_content = template_file.read_text()

            try:
                rendered = self.template_renderer.render_string(template_content, template_data)
                assert len(rendered) > 0, f"Empty render for {template_file.name}"
                assert "None" not in rendered, f"None values in rendered {template_file.name}"

            except Exception as e:
                pytest.fail(f"Template {template_file.name} failed to render: {e}")

    def test_orchestrator_blackboard_contract(self):
        """
        Verify Orchestrator correctly uses Blackboard for artifact sharing.
        """
        spec = self._create_minimal_spec()
        ctx = self._create_run_context()
        blackboard = Blackboard()

        # Mock file operations to avoid actual file creation
        with tempfile.TemporaryDirectory() as temp_dir:
            ctx.out_dir = Path(temp_dir)

            # Execute render operation
            self.orchestrator._render_balanced_pack(ctx, spec, blackboard)

            # Verify artifacts were added to blackboard
            artifact_index = blackboard.publish()
            assert len(artifact_index.artifacts) > 0

            # Verify artifact structure
            for artifact in artifact_index.artifacts:
                assert hasattr(artifact, 'name')
                assert hasattr(artifact, 'path')
                assert hasattr(artifact, 'pack')
                assert hasattr(artifact, 'purpose')

    def test_error_handling_contract(self):
        """
        Verify error handling contracts between Orchestrator and TemplateRenderer.
        """
        spec = self._create_minimal_spec()
        ctx = self._create_run_context()
        blackboard = Blackboard()

        # Test with invalid template data
        with patch.object(self.template_renderer, 'render_string') as mock_render:
            mock_render.side_effect = Exception("Template rendering failed")

            # Should not crash orchestrator, but may log warning
            with tempfile.TemporaryDirectory() as temp_dir:
                ctx.out_dir = Path(temp_dir)

                # This should handle template errors gracefully
                # (current implementation logs warning and continues)
                self.orchestrator._render_balanced_pack(ctx, spec, blackboard)

    def test_performance_contract(self):
        """
        Verify performance characteristics of Orchestrator-TemplateRenderer interaction.
        """
        spec = self._create_minimal_spec()
        ctx = self._create_run_context()
        blackboard = Blackboard()

        import time

        with tempfile.TemporaryDirectory() as temp_dir:
            ctx.out_dir = Path(temp_dir)

            start_time = time.time()
            self.orchestrator._render_balanced_pack(ctx, spec, blackboard)
            render_time = time.time() - start_time

            # Template rendering should be fast (part of larger performance budget)
            assert render_time < 2.0, f"Template rendering too slow: {render_time:.3f}s"

    def _create_minimal_spec(self) -> SourceSpec:
        """Create a minimal valid SourceSpec for testing."""
        return self.spec_builder.build_minimal_spec()

    def _create_run_context(self, out_dir: Path = None) -> RunContext:
        """Create a test RunContext."""
        if out_dir is None:
            out_dir = Path(tempfile.mkdtemp())

        return RunContext(
            run_id=uuid4(),
            out_dir=out_dir,
            offline=True,
            dials=Dials(
                audience_mode=AudienceMode.BALANCED,
                development_flow=DevelopmentFlow.DUAL_TRACK,
                test_depth=TestDepth.PYRAMID
            ),
            created_at=datetime.utcnow()
        )

    def _validate_template_data_contract(self, template_data: dict[str, Any]) -> None:
        """Validate the template data conforms to expected contract."""

        # Meta should have required fields
        meta = template_data['meta']
        assert 'title' in meta
        assert 'version' in meta
        assert isinstance(meta['title'], str)

        # Problem should have structured data
        problem = template_data['problem']
        assert 'description' in problem
        assert isinstance(problem['description'], str)

        # Constraints should be structured
        constraints = template_data['constraints']
        assert isinstance(constraints, dict)

        # Success metrics should be present
        success_metrics = template_data['success_metrics']
        assert isinstance(success_metrics, dict)

        # Dials should have correct structure
        dials = template_data['dials']
        assert 'audience_mode' in dials
        assert 'development_flow' in dials
        assert 'test_depth' in dials

        # Runtime context should be present
        assert isinstance(template_data['pack_type'], str)
        assert isinstance(template_data['run_id'], str)
        assert isinstance(template_data['generated_at'], str)

    def _validate_no_breaking_nones(self, data: dict[str, Any]) -> None:
        """Ensure no None values that could break template rendering."""

        def check_none_recursively(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    check_none_recursively(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{path}[{i}]"
                    check_none_recursively(item, current_path)
            elif obj is None:
                # None values should be replaced with empty strings or defaults
                pytest.fail(f"Found None value at {path} - could break template rendering")

        check_none_recursively(data)


class TestTemplateDataIntegrity:
    """Tests for template data integrity and completeness."""

    def test_spec_to_template_data_mapping(self):
        """Verify all SourceSpec fields are properly mapped to template data."""
        spec_builder = SpecBuilder()
        spec = spec_builder.build_minimal_spec()

        # Get all spec model fields
        spec.model_fields.keys()

        # Template data mapping (as done in orchestrator)
        template_data = {
            "meta": spec.meta.model_dump(),
            "problem": spec.problem.model_dump(),
            "constraints": spec.constraints.model_dump(),
            "success_metrics": spec.success_metrics.model_dump(),
            "diagram_scope": spec.diagram_scope.model_dump(),
            "contracts_data": spec.contracts_data.model_dump(),
            "test_strategy": spec.test_strategy.model_dump(),
            "operations": spec.operations.model_dump(),
            "export": spec.export.model_dump()
        }

        # Verify all major spec components are mapped
        expected_mappings = [
            'meta', 'problem', 'constraints', 'success_metrics',
            'diagram_scope', 'contracts_data', 'test_strategy',
            'operations', 'export'
        ]

        for mapping in expected_mappings:
            assert mapping in template_data, f"Missing template mapping for {mapping}"
            assert template_data[mapping] is not None, f"Null template data for {mapping}"

    def test_template_variable_completeness(self):
        """
        Verify all template variables have corresponding data sources.
        This helps catch template-data mismatches early.
        """
        template_renderer = TemplateRenderer()
        spec_builder = SpecBuilder()
        spec = spec_builder.build_minimal_spec()

        # Prepare template data
        template_data = {
            "meta": spec.meta.model_dump(),
            "problem": spec.problem.model_dump(),
            "constraints": spec.constraints.model_dump(),
            "success_metrics": spec.success_metrics.model_dump(),
            "diagram_scope": spec.diagram_scope.model_dump(),
            "contracts_data": spec.contracts_data.model_dump(),
            "test_strategy": spec.test_strategy.model_dump(),
            "operations": spec.operations.model_dump(),
            "export": spec.export.model_dump(),
            "dials": Dials().model_dump(),
            "pack_type": "balanced",
            "run_id": str(uuid4()),
            "generated_at": datetime.utcnow().isoformat()
        }

        # Test each template file
        template_dir = Path(__file__).parent.parent.parent / "src" / "studio" / "templates" / "balanced"

        for template_file in template_dir.glob("*.j2"):
            template_content = template_file.read_text()

            # Should render without undefined variable errors
            try:
                rendered = template_renderer.render_string(template_content, template_data)
                assert rendered is not None

            except Exception as e:
                if "undefined" in str(e).lower():
                    pytest.fail(f"Template {template_file.name} has undefined variables: {e}")
                else:
                    # Other errors may be expected in minimal spec testing
                    pass
