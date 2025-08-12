"""Main Studio application class."""

from pathlib import Path
from typing import Optional
from uuid import uuid4
from datetime import datetime

from .types import SourceSpec, PackType, RunContext, Dials
from .artifacts import ArtifactIndex, ZipArtifact
from .validation import SchemaValidator, ValidationResult
from .orchestrator import Orchestrator
from .spec_builder import SpecBuilder


class StudioApp:
    """Main Studio application for generating document packs."""
    
    def __init__(self):
        """Initialize the Studio application."""
        self.schema_validator = SchemaValidator()
        self.orchestrator = Orchestrator()
        self.spec_builder = SpecBuilder()
    
    def validate(self, spec: SourceSpec) -> ValidationResult:
        """Validate a source spec."""
        return self.schema_validator.validate(spec)
    
    def generate(
        self, 
        spec: SourceSpec, 
        pack: PackType,
        out_dir: Path = None,
        offline: bool = False,
        dials: Optional[Dials] = None
    ) -> ArtifactIndex:
        """Generate a document pack from a source spec."""
        # Set up run context
        if out_dir is None:
            out_dir = Path("./out")
        
        out_dir.mkdir(parents=True, exist_ok=True)
        
        ctx = RunContext(
            run_id=uuid4(),
            offline=offline,
            dials=dials or Dials(),
            out_dir=out_dir
        )
        
        # Validate spec before processing
        validation_result = self.validate(spec)
        if not validation_result.ok:
            error_messages = [f"{err.json_pointer}: {err.message}" for err in validation_result.errors]
            raise ValueError(f"Spec validation failed: {'; '.join(error_messages)}")
        
        # Run orchestrator
        return self.orchestrator.run(ctx, spec, pack)
    
    def generate_from_files(
        self,
        idea_path: Optional[Path] = None,
        decisions_path: Optional[Path] = None,
        pack: PackType = PackType.BALANCED,
        out_dir: Path = None,
        offline: bool = False,
        dials: Optional[Dials] = None
    ) -> ArtifactIndex:
        """Generate a document pack from idea and decision files."""
        # Build spec from files
        spec = self.spec_builder.merge_idea_decisions(idea_path, decisions_path)
        
        # Generate pack
        return self.generate(spec, pack, out_dir, offline, dials)
    
    def package(self, index: ArtifactIndex) -> ZipArtifact:
        """Package artifacts into a zip bundle."""
        import zipfile
        from uuid import uuid4
        
        zip_path = Path(f"output_bundle_{index.run_id}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add manifest
            manifest_path = f"artifact_index.json"
            zipf.writestr(manifest_path, index.to_json())
            
            # Add all artifacts
            for artifact in index.artifacts:
                if artifact.path.exists():
                    zipf.write(artifact.path, artifact.name)
        
        return ZipArtifact(
            name=zip_path.name,
            path=zip_path,
            pack=PackType.BOTH,  # Contains artifacts from all packs
            purpose="Complete artifact bundle"
        )