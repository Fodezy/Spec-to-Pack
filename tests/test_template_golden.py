"""Golden tests for template consistency."""

import pytest
from pathlib import Path
from jinja2 import Template, StrictUndefined
from studio.types import SourceSpec, Meta, Problem, Dials, RunContext, PackType
from datetime import datetime
from uuid import uuid4
import hashlib
import os


def create_deterministic_spec() -> SourceSpec:
    """Create a deterministic spec for golden tests."""
    return SourceSpec(
        meta=Meta(
            name="Golden Test Spec", 
            version="1.0.0",
            description="Test specification for golden template tests"
        ),
        problem=Problem(
            statement="Create a deterministic template testing system",
            context="This system validates template consistency across versions"
        )
    )


def create_deterministic_template_data() -> dict:
    """Create deterministic template data for golden tests."""
    spec = create_deterministic_spec()
    
    # Use fixed UUID and timestamp for deterministic output
    fixed_uuid = uuid4()  # This will be different each run, we'll override it
    fixed_timestamp = "2024-01-01T12:00:00Z"
    
    ctx = RunContext(
        run_id=fixed_uuid,
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
        "generated_at": fixed_timestamp,
        "run_id": "golden-test-run-001",
        # Optional fields that some templates may expect
        "compliance_context": {},
        "risks_open_questions": {},
        "roadmap_preferences": {}
    }


class TestTemplateGolden:
    """Golden tests for template consistency."""
    
    @pytest.fixture
    def golden_dir(self):
        """Get the golden test directory."""
        return Path(__file__).parent / "golden"
    
    @pytest.fixture
    def expected_dir(self, golden_dir):
        """Get the expected outputs directory."""
        expected = golden_dir / "expected"
        expected.mkdir(parents=True, exist_ok=True)
        return expected
    
    def get_template_content(self, template_name: str) -> str:
        """Get template content by name."""
        templates_dir = Path(__file__).parent.parent / "src" / "studio" / "templates" / "balanced"
        template_path = templates_dir / template_name
        
        if not template_path.exists():
            pytest.skip(f"Template {template_name} not found")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def render_template(self, template_content: str, data: dict) -> str:
        """Render template with data."""
        template = Template(template_content, undefined=StrictUndefined)
        return template.render(data)
    
    def normalize_output(self, content: str) -> str:
        """Normalize output for comparison (remove date variations, etc.)."""
        # Replace any remaining timestamp patterns with fixed values
        import re
        
        # Replace UUID patterns
        content = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 
                        'golden-test-uuid', content, flags=re.IGNORECASE)
        
        # Replace any ISO timestamp patterns that might have slipped through
        content = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?', 
                        '2024-01-01T12:00:00Z', content)
        
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        return content.strip()
    
    def get_content_hash(self, content: str) -> str:
        """Get SHA-256 hash of content for comparison."""
        normalized = self.normalize_output(content)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    @pytest.mark.parametrize("template_name", [
        "brief.md",
        "prd.md.j2", 
        "roadmap.md.j2",
        "test_plan.md.j2"
    ])
    def test_template_golden(self, template_name: str, expected_dir: Path):
        """Test template output against golden files."""
        # Render template
        template_content = self.get_template_content(template_name)
        data = create_deterministic_template_data()
        rendered_content = self.render_template(template_content, data)
        
        # Normalize output
        normalized_content = self.normalize_output(rendered_content)
        
        # Expected file path  
        expected_file = expected_dir / f"{template_name}.expected"
        
        # Check if this is a new golden test or update mode
        update_golden = os.environ.get('UPDATE_GOLDEN', '').lower() in ('true', '1', 'yes')
        
        if not expected_file.exists() or update_golden:
            # Create/update golden file
            with open(expected_file, 'w', encoding='utf-8') as f:
                f.write(normalized_content)
            
            if update_golden:
                print(f"Updated golden file: {expected_file}")
            else:
                print(f"Created golden file: {expected_file}")
            
            # Don't fail the test if we're creating/updating
            return
        
        # Load expected content
        with open(expected_file, 'r', encoding='utf-8') as f:
            expected_content = f.read().strip()
        
        # Compare content
        if normalized_content != expected_content:
            # Calculate hashes for easier debugging
            actual_hash = self.get_content_hash(normalized_content)
            expected_hash = self.get_content_hash(expected_content)
            
            # Write actual output for debugging
            actual_file = expected_dir / f"{template_name}.actual"
            with open(actual_file, 'w', encoding='utf-8') as f:
                f.write(normalized_content)
            
            pytest.fail(
                f"Template {template_name} output differs from golden file.\n"
                f"Expected hash: {expected_hash}\n"
                f"Actual hash:   {actual_hash}\n"
                f"Actual output written to: {actual_file}\n"
                f"Expected file: {expected_file}\n"
                f"To update golden files, run: UPDATE_GOLDEN=true pytest {__file__}::{self.__class__.__name__}::test_template_golden"
            )
    
    def test_template_consistency_across_runs(self):
        """Test that templates produce identical output across multiple runs."""
        template_content = self.get_template_content("brief.md")
        data = create_deterministic_template_data()
        
        # Render template multiple times
        outputs = []
        for _ in range(3):
            rendered = self.render_template(template_content, data)
            normalized = self.normalize_output(rendered)
            outputs.append(normalized)
        
        # All outputs should be identical
        assert len(set(outputs)) == 1, "Template output is not deterministic across runs"
    
    def test_golden_files_exist(self, expected_dir: Path):
        """Test that expected golden files exist for core templates."""
        core_templates = ["brief.md", "prd.md.j2", "roadmap.md.j2", "test_plan.md.j2"]
        
        missing_files = []
        for template_name in core_templates:
            expected_file = expected_dir / f"{template_name}.expected"
            if not expected_file.exists():
                missing_files.append(str(expected_file))
        
        if missing_files:
            pytest.fail(
                f"Missing golden files: {', '.join(missing_files)}\n"
                f"Run: UPDATE_GOLDEN=true pytest {__file__} to create them"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])