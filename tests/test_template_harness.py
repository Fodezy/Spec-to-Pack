"""Template harness test that validates all templates render with minimal spec."""

import pytest
from pathlib import Path
from jinja2 import Template, StrictUndefined, TemplateError
from studio.types import SourceSpec, Meta, Problem, Dials, RunContext, PackType
from studio.rendering import TemplateRenderer
from uuid import uuid4


def create_minimal_spec() -> SourceSpec:
    """Create the smallest valid SourceSpec for template testing."""
    return SourceSpec(
        meta=Meta(name="Test Spec", version="1.0.0"),
        problem=Problem(statement="Test problem statement")
    )


def create_template_data() -> dict:
    """Create minimal template data context."""
    from datetime import datetime
    
    spec = create_minimal_spec()
    ctx = RunContext(
        run_id=uuid4(),
        offline=True,
        dials=Dials(),
        out_dir=Path("/tmp/test")
    )
    
    return {
        "spec": spec,
        "ctx": ctx,
        "pack_type": PackType.BALANCED,
        "meta": spec.meta.model_dump(),
        "problem": spec.problem.model_dump(),
        "constraints": spec.constraints.model_dump(),
        "success_metrics": spec.success_metrics.model_dump(),
        "diagram_scope": spec.diagram_scope.model_dump(),
        "contracts_data": spec.contracts_data.model_dump(),
        "test_strategy": spec.test_strategy.model_dump(),
        "operations": spec.operations.model_dump(),
        "export": spec.export.model_dump(),
        "dials": ctx.dials,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "run_id": str(ctx.run_id),
        # Optional fields that some templates may expect
        "compliance_context": {},
        "risks_open_questions": {},
        "roadmap_preferences": {}
    }


class TestTemplateHarness:
    """Template harness tests."""
    
    def get_template_files(self) -> list[Path]:
        """Get all template files to test."""
        templates_dir = Path(__file__).parent.parent / "src" / "studio" / "templates"
        template_files = []
        
        # Get all .j2 and .md template files
        for pattern in ["**/*.j2", "**/*.md"]:
            template_files.extend(templates_dir.glob(pattern))
        
        return template_files
    
    def test_all_templates_render_with_minimal_spec(self):
        """Test that all templates can render with minimal spec data."""
        template_files = self.get_template_files()
        assert len(template_files) > 0, "No template files found"
        
        data = create_template_data()
        
        failed_templates = []
        
        for template_file in template_files:
            try:
                # Read template content
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                # Create Jinja2 template with StrictUndefined
                template = Template(
                    template_content, 
                    undefined=StrictUndefined
                )
                
                # Attempt to render
                rendered = template.render(data)
                
                # Basic validation: should not be empty and should be string
                assert isinstance(rendered, str), f"Template {template_file} did not render to string"
                assert len(rendered.strip()) > 0, f"Template {template_file} rendered to empty content"
                
            except TemplateError as e:
                failed_templates.append({
                    "file": template_file,
                    "error": str(e),
                    "type": "TemplateError"
                })
            except Exception as e:
                failed_templates.append({
                    "file": template_file,
                    "error": str(e),
                    "type": type(e).__name__
                })
        
        # Report all failures
        if failed_templates:
            error_details = "\n".join([
                f"  - {fail['file']}: {fail['type']} - {fail['error']}"
                for fail in failed_templates
            ])
            pytest.fail(f"Template rendering failed for {len(failed_templates)} templates:\n{error_details}")
    
    def test_balanced_pack_templates(self):
        """Test balanced pack templates specifically."""
        balanced_dir = Path(__file__).parent.parent / "src" / "studio" / "templates" / "balanced"
        
        expected_templates = [
            "brief.md",
            "prd.md.j2", 
            "roadmap.md.j2",
            "test_plan.md.j2",
            "diagrams/lifecycle.mmd.j2",
            "diagrams/sequence.mmd.j2"
        ]
        
        data = create_template_data()
        
        for template_name in expected_templates:
            template_path = balanced_dir / template_name
            assert template_path.exists(), f"Expected balanced template {template_name} not found"
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            template = Template(template_content, undefined=StrictUndefined)
            
            try:
                rendered = template.render(data)
                assert isinstance(rendered, str)
                assert len(rendered.strip()) > 0
            except TemplateError as e:
                pytest.fail(f"Balanced template {template_name} failed to render: {e}")
    
    def test_template_strict_undefined_enforcement(self):
        """Test that templates fail fast on missing variables."""
        # Create template with undefined variable
        test_template = Template(
            "Hello {{ undefined_variable }}!",
            undefined=StrictUndefined
        )
        
        data = create_template_data()
        
        with pytest.raises(TemplateError):
            test_template.render(data)
    
    def test_template_renderer_with_minimal_spec(self):
        """Test TemplateRenderer class with minimal spec."""
        renderer = TemplateRenderer()
        data = create_template_data()
        
        # Test that renderer can be instantiated and has proper configuration
        assert renderer.env.undefined == StrictUndefined
        assert not renderer.env.autoescape
        
        # Test render_string method
        result = renderer.render_string("Hello {{ meta.name }}!", data)
        assert result == "Hello Test Spec!"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])