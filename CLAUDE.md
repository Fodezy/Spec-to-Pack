# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Installation
```bash
# Install in development mode with dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Alternative: Use Makefile
make install
```

### Testing and Linting
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_cli.py -v

# Run tests with coverage
pytest tests/ --cov=src

# Lint code
ruff check src tests
black --check src tests
isort --check-only src tests

# Alternative: Use Makefile
make test
make lint
make format
```

### CLI Usage
```bash
# CLI is accessible via module or installed command
python -m studio.cli --help

# Generate with minimal spec (uses defaults)
python -m studio.cli generate --offline --out test_output

# Validate a spec file
python -m studio.cli validate path/to/spec.yaml

# Generate with idea and decision files
python -m studio.cli generate \
  --idea path/to/idea.yaml \
  --decisions path/to/decisions.yaml \
  --pack balanced \
  --out ./output
```

## Architecture Overview

This codebase follows a strict **Controller → App → Orchestrator → Agents** architecture as defined in `Diagrams/Class.mmd`. Every architectural change must be validated against this diagram.

### Core Flow
1. **Controllers** (`CLIController`, `ApiController`) receive user requests
2. **StudioApp** serves as the central facade, handling validation and coordination
3. **Orchestrator** manages the pipeline execution with step budgets, timeouts, and audit logging
4. **Agents** execute specific tasks (FramerAgent, PRDWriterAgent, DiagrammerAgent, etc.)
5. **Blackboard** enables agent communication and artifact sharing
6. **ArtifactIndex** tracks all generated outputs with manifest integrity

### Key Components

**Data Models** (`src/studio/types.py`):
- `SourceSpec`: Central spec with meta, problem, constraints, success_metrics, etc.
- `RunContext`: Runtime context with run_id, offline mode, dials, output directory
- `Dials`: Configuration for audience_mode, development_flow, test_depth
- All enums: `PackType`, `AudienceMode`, `DevelopmentFlow`, `TestDepth`, `Status`

**Orchestration** (`src/studio/orchestrator.py`):
- Pipeline execution with step budgets (default: 50) and timeouts (default: 5min per step)
- Raises `BudgetExceededException` or `StepTimeoutException` when limits exceeded
- Complete audit trail in JSONL format with durations and details

**Agents** (`src/studio/agents/base.py`):
- All inherit from `Agent` interface with `run(ctx, spec, blackboard)` method
- Return `AgentOutput` with notes, artifacts, updated_spec, and status
- Pipeline order: Framer → Librarian → PRDWriter → Diagrammer → QAArchitect → Roadmapper → Packager

**Artifacts** (`src/studio/artifacts.py`):
- Hierarchy: `DocumentArtifact`, `DiagramArtifact`, `SchemaArtifact`, `CIArtifact`, `ZipArtifact`
- Tracked in `ArtifactIndex` with run_id, template metadata, and SHA-256 hashes
- Blackboard enables artifact sharing between agents

**Validation** (`src/studio/validation.py`):
- `SchemaValidator` validates against JSON Schema 2020-12
- Returns `ValidationResult` with JSON pointer error locations
- Combines Pydantic model validation with JSONSchema validation

### Pack Types
- **Balanced Pack**: PRD, Test Plan, diagrams, roadmap (standard business docs)
- **Deep Pack**: Engineering contracts, CI workflows, packaged zips with integrity
- **Both**: Generates all artifacts from both pack types

### Determinism Requirements
- All outputs must be byte-identical across runs (except timestamps)
- `DeterminismUtils` normalizes JSON keys, ensures LF newlines, UTC timestamps
- CI includes `rerun-diff` job that compares two successive generations
- Golden tests validate template consistency

### Template System
- Templates use Jinja2 with `StrictUndefined` (fails fast on missing variables)
- Template sets have semantic versioning (e.g., "balanced-1.0.0")
- Each run embeds `template_set` and `template_commit` in manifest
- Template harness validates all templates against minimal valid spec

### Repository Automation
```bash
# Bootstrap GitHub issues/milestones (requires gh CLI)
./bootstrap_issues.sh Fodezy/Spec-to-Pack --dry-run
./bootstrap_issues.sh Fodezy/Spec-to-Pack  # actual run
```

### Offline Mode and Security
- `--offline` flag enforces network isolation for tests and runs
- Guards block socket access when offline mode enabled
- RAG/research features respect robots.txt and implement rate limiting
- No secrets or API keys committed to repository

### Important Architectural Constraints
- Controllers MUST use StudioApp, never directly access Orchestrator
- All agents MUST follow the Agent interface and return AgentOutput
- Artifacts MUST be tracked through Blackboard and published to ArtifactIndex  
- Schema changes MUST validate against JSON Schema 2020-12 meta-schema
- Template changes MUST pass the template harness test
- Pipeline modifications MUST respect step budgets and timeout enforcement

When making changes, always verify compliance with `Diagrams/Class.mmd` and update the diagram if architectural changes are necessary.