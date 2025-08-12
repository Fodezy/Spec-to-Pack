"""Template rendering components."""

from pathlib import Path
from typing import Dict, Any
import jinja2

from .types import Template, TemplateType
from .artifacts import DocumentArtifact, DiagramArtifact, SchemaArtifact, CIArtifact


class TemplateRenderer:
    """Renders Jinja2 templates with data."""
    
    def __init__(self, template_dir: Path = None):
        """Initialize renderer with template directory."""
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"
        
        self.template_dir = template_dir
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            undefined=jinja2.StrictUndefined,
            autoescape=False
        )
    
    def render(self, template: Template, data: Dict[str, Any]) -> DocumentArtifact:
        """Render a template with given data."""
        try:
            jinja_template = self.env.get_template(str(template.path.relative_to(self.template_dir)))
            content = jinja_template.render(data)
            
            # Create appropriate artifact type based on template type
            if template.type == TemplateType.MARKDOWN:
                return DocumentArtifact(
                    name=template.path.stem,
                    path=template.path,
                    pack=data.get('pack_type', 'balanced'),
                    purpose=f"Rendered {template.type.value} document"
                )
            elif template.type == TemplateType.MERMAID:
                return DiagramArtifact(
                    name=template.path.stem,
                    path=template.path,
                    pack=data.get('pack_type', 'balanced'),
                    purpose=f"Rendered {template.type.value} diagram"
                )
            elif template.type == TemplateType.JSON:
                return SchemaArtifact(
                    name=template.path.stem,
                    path=template.path,
                    pack=data.get('pack_type', 'deep'),
                    purpose=f"Rendered {template.type.value} schema"
                )
            elif template.type == TemplateType.GHA_WORKFLOW:
                return CIArtifact(
                    name=template.path.stem,
                    path=template.path,
                    pack=data.get('pack_type', 'deep'),
                    purpose=f"Rendered {template.type.value} workflow"
                )
            else:
                return DocumentArtifact(
                    name=template.path.stem,
                    path=template.path,
                    pack=data.get('pack_type', 'balanced'),
                    purpose=f"Rendered {template.type.value} document"
                )
        
        except jinja2.TemplateError as e:
            raise RuntimeError(f"Template rendering failed: {e}")
    
    def render_string(self, template_str: str, data: Dict[str, Any]) -> str:
        """Render a template string with data."""
        template = jinja2.Template(template_str, undefined=jinja2.StrictUndefined)
        return template.render(data)