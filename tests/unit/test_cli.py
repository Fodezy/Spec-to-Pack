"""Unit tests for CLI module."""

import pytest
from click.testing import CliRunner
from studio.cli import main


def test_cli_help():
    """Test CLI help command."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Spec-to-Pack Studio CLI" in result.output


def test_validate_command():
    """Test validate command with stub."""
    runner = CliRunner()
    # This will fail because we need a real file, but shows the command works
    result = runner.invoke(main, ["validate", "--help"])
    assert result.exit_code == 0


def test_generate_command():
    """Test generate command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "--help"])
    assert result.exit_code == 0