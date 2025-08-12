"""CLI Controller for Spec-to-Pack Studio."""

import click
import yaml
from pathlib import Path
from typing import Optional

from .app import StudioApp
from .types import SourceSpec, PackType, Dials, AudienceMode


class CLIController:
    """CLI Controller following the class diagram pattern."""
    
    def __init__(self):
        """Initialize CLI controller with StudioApp."""
        self.app = StudioApp()
    
    def main(self, args) -> int:
        """Main CLI entry point."""
        return 0


# Global controller instance
controller = CLIController()


@click.group()
@click.version_option()
def main():
    """Spec-to-Pack Studio CLI - Generate engineering document packs from specs."""
    pass


@main.command()
@click.argument("spec_path", type=click.Path(exists=True, path_type=Path))
def validate(spec_path: Path):
    """Validate a source spec against its JSON schema."""
    click.echo(f"[VALIDATE] Validating spec: {spec_path}")
    
    try:
        # Load spec from file
        with open(spec_path) as f:
            if spec_path.suffix.lower() in ['.yaml', '.yml']:
                spec_data = yaml.safe_load(f)
            else:
                import json
                spec_data = json.load(f)
        
        # Create SourceSpec object
        spec = SourceSpec(**spec_data)
        
        # Validate using StudioApp
        result = controller.app.validate(spec)
        
        if result.ok:
            click.echo("PASS: Validation passed")
        else:
            click.echo("FAIL: Validation failed:")
            for error in result.errors:
                click.echo(f"  {error.json_pointer}: {error.message}")
            return 1
            
    except Exception as e:
        click.echo(f"ERROR: Error validating spec: {str(e)}")
        return 1


@main.command()
@click.option("--idea", type=click.Path(exists=True, path_type=Path), help="Path to idea file")
@click.option("--decisions", type=click.Path(exists=True, path_type=Path), help="Path to decisions file")
@click.option("--out", type=click.Path(path_type=Path), default=Path("./out"), help="Output directory")
@click.option("--pack", type=click.Choice(["balanced", "deep", "both"]), default="balanced", help="Pack type to generate")
@click.option("--dry-run", is_flag=True, help="Preview artifacts without generating")
@click.option("--offline", is_flag=True, help="Run in offline mode")
@click.option("--audience", type=click.Choice(["brief", "balanced", "deep"]), default="balanced", help="Audience complexity level")
def generate(
    idea: Optional[Path], 
    decisions: Optional[Path], 
    out: Path, 
    pack: str,
    dry_run: bool,
    offline: bool,
    audience: str
):
    """Generate a document pack from idea and decisions."""
    try:
        if dry_run:
            click.echo("[DRY-RUN] Dry run mode - previewing artifacts")
            # TODO: Implement dry run preview
            return
        
        click.echo(f"[GENERATE] Generating {pack} pack")
        click.echo(f"[OUTPUT] Output directory: {out}")
        
        if idea:
            click.echo(f"[IDEA] Idea file: {idea}")
        if decisions:
            click.echo(f"[DECISIONS] Decisions file: {decisions}")
        
        if offline:
            click.echo("[OFFLINE] Running in offline mode")
        
        # Convert string arguments to enums
        pack_type = PackType(pack)
        dials = Dials(audience_mode=AudienceMode(audience))
        
        # Generate using StudioApp
        artifact_index = controller.app.generate_from_files(
            idea_path=idea,
            decisions_path=decisions,
            pack=pack_type,
            out_dir=out,
            offline=offline,
            dials=dials
        )
        
        click.echo("[SUCCESS] Generation completed")
        click.echo(f"[ARTIFACTS] Generated {len(artifact_index.artifacts)} artifacts")
        click.echo(f"[RUN-ID] Run ID: {artifact_index.run_id}")
        
        # Save manifest
        manifest_path = out / "artifact_index.json"
        with open(manifest_path, 'w') as f:
            f.write(artifact_index.to_json())
        click.echo(f"[MANIFEST] Manifest saved: {manifest_path}")
        
    except Exception as e:
        click.echo(f"[ERROR] Error generating pack: {str(e)}")
        import traceback
        if click.get_current_context().obj and click.get_current_context().obj.get('debug'):
            click.echo(traceback.format_exc())
        return 1


if __name__ == "__main__":
    main()