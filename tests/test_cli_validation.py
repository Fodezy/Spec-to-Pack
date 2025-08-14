"""Test CLI validation command with audit logging."""

import json

from click.testing import CliRunner
from src.studio.cli import main


def test_validate_valid_spec(tmp_path):
    """Test validate command with valid spec."""
    # Create a valid spec file
    spec_data = {
        "meta": {"name": "Test Spec", "version": "1.0.0"},
        "problem": {"statement": "Test problem statement"},
        "success_metrics": {"metrics": ["metric1"]}
    }

    spec_file = tmp_path / "valid_spec.json"
    with open(spec_file, 'w') as f:
        json.dump(spec_data, f)

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(spec_file)])

    assert result.exit_code == 0
    assert "PASS: Validation passed" in result.output

    # Check audit log was created
    audit_file = tmp_path / "audit.jsonl"
    assert audit_file.exists()

    # Verify audit log content
    with open(audit_file) as f:
        lines = f.readlines()

    assert len(lines) >= 2  # at least start and success events
    start_event = json.loads(lines[0])
    success_event = json.loads(lines[1])

    assert start_event["event_type"] == "validation_start"
    assert success_event["event_type"] == "validation_success"
    assert start_event["run_id"] == success_event["run_id"]  # Same run


def test_validate_invalid_spec(tmp_path):
    """Test validate command with invalid spec."""
    # Create an invalid spec file (missing required meta field)
    spec_data = {
        "problem": {"statement": "Test problem statement"},
        "success_metrics": {"metrics": []}
    }

    spec_file = tmp_path / "invalid_spec.json"
    with open(spec_file, 'w') as f:
        json.dump(spec_data, f)

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(spec_file)])

    assert result.exit_code == 2
    assert "ERROR: Invalid spec format" in result.output

    # Check audit log was created
    audit_file = tmp_path / "audit.jsonl"
    assert audit_file.exists()

    # Verify audit log content
    with open(audit_file) as f:
        lines = f.readlines()

    assert len(lines) >= 2  # at least start and error events
    start_event = json.loads(lines[0])
    error_event = json.loads(lines[1])

    assert start_event["event_type"] == "validation_start"
    assert error_event["event_type"] == "validation_error"
    assert error_event["details"]["error_type"] == "model_error"


def test_validate_file_not_found(tmp_path):
    """Test validate command with non-existent file."""
    nonexistent_file = tmp_path / "nonexistent.json"

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(nonexistent_file)])

    assert result.exit_code == 2
    assert "ERROR: File not found" in result.output

    # Check audit log was created
    audit_file = tmp_path / "audit.jsonl"
    assert audit_file.exists()

    # Verify audit log content
    with open(audit_file) as f:
        lines = f.readlines()

    assert len(lines) >= 2  # at least start and error events
    error_event = json.loads(lines[1])
    assert error_event["event_type"] == "validation_error"
    assert error_event["details"]["error_type"] == "file_not_found"


def test_validate_malformed_json(tmp_path):
    """Test validate command with malformed JSON."""
    spec_file = tmp_path / "malformed.json"
    with open(spec_file, 'w') as f:
        f.write("{ invalid json")

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(spec_file)])

    assert result.exit_code == 2
    assert "ERROR: Failed to parse file" in result.output

    # Check audit log
    audit_file = tmp_path / "audit.jsonl"
    assert audit_file.exists()

    with open(audit_file) as f:
        lines = f.readlines()

    error_event = json.loads(lines[1])
    assert error_event["details"]["error_type"] == "parse_error"
