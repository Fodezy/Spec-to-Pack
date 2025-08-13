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
@click.argument("spec_path", type=click.Path(path_type=Path))
@click.pass_context
def validate(ctx, spec_path: Path):
    """Validate a source spec against its JSON schema."""
    from uuid import uuid4
    from .audit import AuditLog
    
    # Create run context for audit logging
    run_id = uuid4()
    audit_log = AuditLog(spec_path.parent / "audit.jsonl")
    
    click.echo(f"[VALIDATE] Validating spec: {spec_path}")
    
    # Log validation start
    audit_log.log_event("validation_start", run_id, f"Starting validation of {spec_path}",
                       stage="validation", event="start")
    
    try:
        # Check if file exists
        if not spec_path.exists():
            error_msg = f"File not found: {spec_path}"
            click.echo(f"ERROR: {error_msg}")
            audit_log.log_event("validation_error", run_id, error_msg, 
                               details={"error_type": "file_not_found"},
                               stage="validation", event="error", level="error")
            audit_log.save()
            ctx.exit(2)
        
        # Load spec from file
        try:
            with open(spec_path) as f:
                if spec_path.suffix.lower() in ['.yaml', '.yml']:
                    spec_data = yaml.safe_load(f)
                else:
                    import json
                    spec_data = json.load(f)
        except Exception as e:
            error_msg = f"Failed to parse file: {str(e)}"
            click.echo(f"ERROR: {error_msg}")
            audit_log.log_event("validation_error", run_id, error_msg, 
                               details={"error_type": "parse_error"},
                               stage="validation", event="error", level="error")
            audit_log.save()
            ctx.exit(2)
        
        # Create SourceSpec object
        try:
            spec = SourceSpec(**spec_data)
        except Exception as e:
            error_msg = f"Invalid spec format: {str(e)}"
            click.echo(f"ERROR: {error_msg}")
            audit_log.log_event("validation_error", run_id, error_msg, 
                               details={"error_type": "model_error"}, 
                               stage="validation", event="error", level="error")
            audit_log.save()
            ctx.exit(2)
        
        # Validate using StudioApp
        result = controller.app.validate(spec)
        
        if result.ok:
            click.echo("PASS: Validation passed")
            audit_log.log_event("validation_success", run_id, "Validation completed successfully",
                               stage="validation", event="success")
            audit_log.save()
            # Success - exit code 0 is default
        else:
            click.echo("FAIL: Validation failed:")
            error_details = []
            for error in result.errors:
                error_detail = f"{error.json_pointer}: {error.message}"
                click.echo(f"  {error_detail}")
                error_details.append(error_detail)
            
            error_msg = "Validation failed with schema errors"
            audit_log.log_event("validation_failed", run_id, error_msg, {
                "error_count": len(result.errors),
                "errors": error_details
            })
            audit_log.save()
            ctx.exit(2)
            
    except Exception as e:
        if isinstance(e, SystemExit):
            raise  # Re-raise SystemExit from ctx.exit()
        
        error_msg = f"Unexpected error during validation: {str(e)}"
        click.echo(f"ERROR: {error_msg}")
        audit_log.log_event("validation_error", run_id, error_msg, {"error_type": "unexpected"})
        audit_log.save()
        ctx.exit(2)


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
        
        # Only create CLI dials if no decision files provided
        cli_dials = None
        if not decisions:
            cli_dials = Dials(audience_mode=AudienceMode(audience))
        
        # Generate using StudioApp (will use file-based dials if available)
        artifact_index = controller.app.generate_from_files(
            idea_path=idea,
            decisions_path=decisions,
            pack=pack_type,
            out_dir=out,
            offline=offline,
            dials=cli_dials
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