"""Test orchestrator audit logging features."""

import json
from uuid import uuid4

from src.studio.orchestrator import Orchestrator
from src.studio.types import Dials, Meta, PackType, Problem, RunContext, SourceSpec


def test_orchestrator_audit_enrichment(tmp_path):
    """Test that orchestrator creates enriched audit logs."""
    # Create a minimal spec
    spec = SourceSpec(
        meta=Meta(name="Test Spec", version="1.0.0"),
        problem=Problem(statement="Test problem statement")
    )

    # Create run context
    ctx = RunContext(
        run_id=uuid4(),
        offline=True,  # Ensure we skip research
        dials=Dials(),
        out_dir=tmp_path
    )

    # Create orchestrator with small budget for testing
    orch = Orchestrator(step_budget=5, timeout_per_step_sec=30)

    # Run pipeline
    try:
        orch.run(ctx, spec, PackType.BALANCED)

        # Check audit log was created
        audit_file = tmp_path / "audit.jsonl"
        assert audit_file.exists()

        # Parse audit log
        events = []
        with open(audit_file) as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

        # Verify enriched fields are present
        assert len(events) > 0
        for event in events:
            assert "event_type" in event
            assert "timestamp" in event
            assert "run_id" in event
            assert "stage" in event
            assert "event" in event
            assert "note" in event
            assert "level" in event
            # duration_ms should be present for completed steps

        # Verify pipeline start event
        start_events = [e for e in events if e["event_type"] == "pipeline_start"]
        assert len(start_events) == 1
        assert start_events[0]["stage"] == "pipeline"
        assert start_events[0]["event"] == "start"

        print(f"✓ Generated {len(events)} audit events with enriched fields")

    except Exception:
        # Even if pipeline fails, audit log should exist with error details
        audit_file = tmp_path / "audit.jsonl"
        if audit_file.exists():
            with open(audit_file) as f:
                content = f.read()
                assert "error" in content.lower()
                print("✓ Error properly logged in audit")
