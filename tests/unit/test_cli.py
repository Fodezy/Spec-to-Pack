"""Unit tests for CLI module."""

import yaml
from click.testing import CliRunner

from studio.cli import CLIController, main


def test_cli_controller_init():
    """Test CLI controller initialization."""
    controller = CLIController()
    assert controller.app is not None


def test_cli_help():
    """Test CLI help command."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Spec-to-Pack Studio CLI" in result.output


def test_validate_command_help():
    """Test validate command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--help"])
    assert result.exit_code == 0


def test_generate_command_help():
    """Test generate command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "--help"])
    assert result.exit_code == 0


def test_validate_with_valid_spec(tmp_path):
    """Test validate command with valid spec."""
    # Create a minimal valid spec
    spec_data = {
        "meta": {"name": "Test Spec", "version": "1.0.0"},
        "problem": {"statement": "Test problem"}
    }

    spec_file = tmp_path / "test_spec.yaml"
    with open(spec_file, 'w') as f:
        yaml.dump(spec_data, f)

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(spec_file)])

    # Should validate successfully
    assert "PASS: Validation passed" in result.output


def test_generate_dry_run():
    """Test generate command with dry run."""
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "--dry-run"])

    assert result.exit_code == 0
    assert "[DRY-RUN] Dry run mode" in result.output
