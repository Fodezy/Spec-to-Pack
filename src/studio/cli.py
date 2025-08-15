"""CLI Controller for Spec-to-Pack Studio."""

from pathlib import Path

import click
import yaml

from .app import StudioApp
from .types import AudienceMode, Dials, PackType, SourceSpec


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
    idea: Path | None,
    decisions: Path | None,
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


@main.group()
def cache():
    """Cache management commands for research pipeline."""
    pass


@cache.command()
def stats():
    """Show cache statistics."""
    try:
        from .cache.research_cache import ResearchCacheManager
        
        cache_manager = ResearchCacheManager()
        stats = cache_manager.cache_stats()
        
        click.echo("Cache Statistics:")
        click.echo(f"  Total entries: {stats['total']['count']}")
        click.echo(f"  Total size: {stats['total']['size_mb']:.2f} MB")
        click.echo(f"  Total expired: {stats['total']['expired']}")
        click.echo()
        
        for level, level_stats in stats.items():
            if level != 'total':
                click.echo(f"{level.upper()}:")
                click.echo(f"  Entries: {level_stats['count']}")
                click.echo(f"  Size: {level_stats['size_mb']:.2f} MB")
                click.echo(f"  Expired: {level_stats['expired']}")
                click.echo()
            
    except Exception as e:
        click.echo(f"Error getting cache stats: {e}", err=True)
        return 1


@cache.command()
@click.option("--level", type=click.Choice(["search", "content", "embeddings", "research", "all"]), 
              default="all", help="Cache level to clear")
@click.confirmation_option(prompt="Are you sure you want to clear the cache?")
def clear(level):
    """Clear cache levels."""
    try:
        from .cache.research_cache import ResearchCacheManager, CacheLevel
        
        cache_manager = ResearchCacheManager()
        
        if level == "all":
            cleared = cache_manager.clear_all()
            click.echo(f"Cleared {cleared} cache files from all levels")
        else:
            # Map CLI level names to CacheLevel enum
            level_map = {
                "search": CacheLevel.SEARCH_RESULTS,
                "content": CacheLevel.SCRAPED_CONTENT,
                "embeddings": CacheLevel.EMBEDDINGS,
                "research": CacheLevel.RESEARCH_DOCS
            }
            
            cache_level = level_map[level]
            cleared = cache_manager.clear_level(cache_level)
            click.echo(f"Cleared {cleared} cache files from {level} level")
                
    except Exception as e:
        click.echo(f"Error clearing cache: {e}", err=True)
        return 1


@cache.command()
def cleanup():
    """Clean up expired cache entries."""
    try:
        from .cache.research_cache import ResearchCacheManager
        
        cache_manager = ResearchCacheManager()
        cleaned = cache_manager.clear_expired()
        click.echo(f"Cleaned up {cleaned} expired cache entries")
        
    except Exception as e:
        click.echo(f"Error cleaning up cache: {e}", err=True)
        return 1


@cache.command()
def setup():
    """Setup SearxNG Docker container for research."""
    try:
        import subprocess
        from pathlib import Path
        
        # Check if Docker is available
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            click.echo("Docker is not available. Please install Docker first.", err=True)
            return 1
            
        # Check if docker-compose.searxng.yml exists
        compose_file = Path("docker-compose.searxng.yml")
        if not compose_file.exists():
            click.echo("docker-compose.searxng.yml not found in current directory", err=True)
            click.echo("Please run this command from the Spec-to-Pack project root", err=True)
            return 1
            
        # Start SearxNG container
        click.echo("Starting SearxNG Docker container...")
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.searxng.yml", "up", "-d"],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            click.echo("SearxNG container started successfully")
            click.echo("Service available at: http://localhost:8888")
            click.echo("Wait ~30 seconds for the service to fully initialize")
        else:
            click.echo(f"Failed to start SearxNG container: {result.stderr}", err=True)
            return 1
            
    except Exception as e:
        click.echo(f"Error setting up SearxNG: {e}", err=True)
        return 1


@main.group()
def research():
    """Research pipeline commands."""
    pass


@research.command()
@click.option("--query", default="test query", help="Test search query")
@click.option("--offline", is_flag=True, help="Test in offline mode")
def test(query, offline):
    """Test research pipeline components."""
    try:
        from .adapters.search import FallbackSearchAdapter
        from .adapters.embeddings import DualModelEmbeddingsAdapter
        from .guards.content_guards import ContentGuard
        
        click.echo(f"Testing research pipeline with query: '{query}'")
        
        if offline:
            click.echo("Running in offline mode - using stub adapters")
            from .adapters.search import StubSearchAdapter
            from .adapters.embeddings import StubEmbeddingsAdapter
            
            search_adapter = StubSearchAdapter()
            embeddings_adapter = StubEmbeddingsAdapter()
        else:
            click.echo("Running in online mode")
            search_adapter = FallbackSearchAdapter()
            embeddings_adapter = DualModelEmbeddingsAdapter()
        
        # Test search adapter
        click.echo("\n1. Testing search adapter...")
        if search_adapter.health_check():
            click.echo("[OK] Search adapter health check passed")
            
            results = search_adapter.search(query, limit=3)
            click.echo(f"[OK] Search returned {len(results)} results")
            for i, result in enumerate(results[:2], 1):
                click.echo(f"  {i}. {result.title} ({result.engine})")
        else:
            click.echo("[FAIL] Search adapter health check failed")
            
        # Test embeddings adapter
        click.echo("\n2. Testing embeddings adapter...")
        try:
            if hasattr(embeddings_adapter, 'encode_query'):
                # Dual model adapter
                query_emb = embeddings_adapter.encode_query(query)
                content_emb = embeddings_adapter.encode_content("sample content")
                click.echo(f"[OK] Query embedding: {len(query_emb)}d")
                click.echo(f"[OK] Content embedding: {len(content_emb)}d")
            else:
                # Standard adapter
                embedding = embeddings_adapter.encode(query)
                click.echo(f"[OK] Embedding: {len(embedding)}d")
        except Exception as e:
            click.echo(f"[FAIL] Embeddings test failed: {e}")
            
        # Test content guard
        click.echo("\n3. Testing content guard...")
        content_guard = ContentGuard()
        try:
            # Test with example.com (should be safe)
            test_url = "https://example.com"
            content_guard.check_url_allowed(test_url)
            click.echo(f"[OK] URL allowed: {test_url}")
            
            # Test content size limits
            test_content = "This is test content. " * 100
            processed = content_guard.check_content_size(test_content, test_url)
            click.echo(f"[OK] Content processing: {len(processed)} chars")
        except Exception as e:
            click.echo(f"[FAIL] Content guard test failed: {e}")
            
        click.echo("\n[OK] Research pipeline test completed")
        
    except Exception as e:
        click.echo(f"Research pipeline test failed: {e}", err=True)
        return 1


if __name__ == "__main__":
    main()
