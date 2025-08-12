"""Unit tests for agents."""

import pytest
from uuid import uuid4
from pathlib import Path
from studio.agents.base import (
    Agent, FramerAgent, PRDWriterAgent, DiagrammerAgent, QAArchitectAgent
)
from studio.types import SourceSpec, Meta, Problem, RunContext, Dials, Status, PackType
from studio.artifacts import Blackboard


@pytest.fixture
def run_context(tmp_path):
    """Create a test run context."""
    return RunContext(
        run_id=uuid4(),
        offline=True,
        dials=Dials(),
        out_dir=tmp_path
    )


@pytest.fixture
def source_spec():
    """Create a test source spec."""
    return SourceSpec(
        meta=Meta(name="Test Spec", version="1.0.0"),
        problem=Problem(statement="Test problem statement")
    )


@pytest.fixture
def blackboard():
    """Create a test blackboard."""
    return Blackboard()


def test_framer_agent(run_context, source_spec, blackboard):
    """Test FramerAgent execution."""
    agent = FramerAgent()
    
    assert agent.name == "FramerAgent"
    
    result = agent.run(run_context, source_spec, blackboard)
    
    assert result.status == Status.OK
    assert "framed_spec" in result.notes["action"]
    assert result.updated_spec == source_spec  # Should return the same spec in stub


def test_prd_writer_agent(run_context, source_spec, blackboard):
    """Test PRDWriterAgent execution."""
    agent = PRDWriterAgent()
    
    result = agent.run(run_context, source_spec, blackboard)
    
    assert result.status == Status.OK
    assert len(result.artifacts) == 1
    assert result.artifacts[0].name == "prd.md"
    assert result.artifacts[0].pack == PackType.BALANCED


def test_diagrammer_agent(run_context, source_spec, blackboard):
    """Test DiagrammerAgent execution."""
    agent = DiagrammerAgent()
    
    result = agent.run(run_context, source_spec, blackboard)
    
    assert result.status == Status.OK
    assert len(result.artifacts) >= 1  # Should create lifecycle and/or sequence diagrams
    
    # Check that at least one diagram was created
    diagram_names = [a.name for a in result.artifacts]
    assert any("lifecycle" in name or "sequence" in name for name in diagram_names)


def test_qa_architect_agent(run_context, source_spec, blackboard):
    """Test QAArchitectAgent execution."""
    agent = QAArchitectAgent()
    
    result = agent.run(run_context, source_spec, blackboard)
    
    assert result.status == Status.OK
    assert len(result.artifacts) == 1
    assert result.artifacts[0].name == "test_plan.md"
    assert "test_architecture_designed" in result.notes["action"]


def test_agent_interface():
    """Test that agents follow the interface correctly."""
    agents = [FramerAgent(), PRDWriterAgent(), DiagrammerAgent(), QAArchitectAgent()]
    
    for agent in agents:
        assert hasattr(agent, 'name')
        assert hasattr(agent, 'run')
        assert isinstance(agent.name, str)
        assert agent.name.endswith('Agent')