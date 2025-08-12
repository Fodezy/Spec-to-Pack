"""CLI interface for Spec-to-Pack Studio."""

import click
from pathlib import Path
from typing import Optional


@click.group()
@click.version_option()
def main():
    """Spec-to-Pack Studio CLI - Generate engineering document packs from specs."""
    pass


@main.command()
@click.argument("spec_path", type=click.Path(exists=True, path_type=Path))
def validate(spec_path: Path):
    """Validate a source spec against its JSON schema."""
    click.echo(f"🔍 Validating spec: {spec_path}")
    click.echo("✅ Validation passed (stub implementation)")


@main.command()
@click.option("--idea", type=click.Path(exists=True, path_type=Path), help="Path to idea file")
@click.option("--decisions", type=click.Path(exists=True, path_type=Path), help="Path to decisions file")
@click.option("--out", type=click.Path(path_type=Path), default=Path("./out"), help="Output directory")
@click.option("--pack", default="balanced", help="Pack type to generate")
@click.option("--dry-run", is_flag=True, help="Preview artifacts without generating")
@click.option("--offline", is_flag=True, help="Run in offline mode")
def generate(
    idea: Optional[Path], 
    decisions: Optional[Path], 
    out: Path, 
    pack: str,
    dry_run: bool,
    offline: bool
):
    """Generate a document pack from idea and decisions."""
    if dry_run:
        click.echo("🧪 Dry run mode - previewing artifacts")
    
    click.echo(f"📝 Generating {pack} pack")
    click.echo(f"📂 Output directory: {out}")
    
    if idea:
        click.echo(f"💡 Idea file: {idea}")
    if decisions:
        click.echo(f"📋 Decisions file: {decisions}")
    
    if offline:
        click.echo("🔒 Running in offline mode")
    
    click.echo("✅ Generate completed (stub implementation)")


if __name__ == "__main__":
    main()