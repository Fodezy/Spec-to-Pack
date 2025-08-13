"""Core types and enums for Spec-to-Pack Studio."""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path
from uuid import UUID
from pydantic import BaseModel, Field


# Enums from the class diagram
class Status(Enum):
    """Agent execution status."""
    OK = "ok"
    RETRY = "retry"
    FAIL = "fail"


class AudienceMode(Enum):
    """Target audience complexity level."""
    BRIEF = "brief"
    BALANCED = "balanced" 
    DEEP = "deep"


class DevelopmentFlow(Enum):
    """Development methodology."""
    AGILE = "agile"
    KANBAN = "kanban"
    DUAL_TRACK = "dual_track"
    WATERFALL = "waterfall"


class TestDepth(Enum):
    """Testing strategy depth."""
    LIGHT = "light"
    PYRAMID = "pyramid"
    FULL_MATRIX = "full_matrix"


class PackType(Enum):
    """Pack type to generate."""
    BALANCED = "balanced"
    DEEP = "deep"
    BOTH = "both"


class TemplateType(Enum):
    """Template format types."""
    MARKDOWN = "markdown"
    JSON = "json"
    YAML = "yaml"
    MERMAID = "mermaid"
    YAML_SCHEMA = "yaml_schema"
    GHA_WORKFLOW = "gha_workflow"


# Core data classes
class Dials(BaseModel):
    """Configuration dials for generation behavior."""
    audience_mode: AudienceMode = AudienceMode.BALANCED
    development_flow: DevelopmentFlow = DevelopmentFlow.AGILE
    test_depth: TestDepth = TestDepth.PYRAMID


class Meta(BaseModel):
    """Spec metadata."""
    name: str
    version: str = "0.1.0"
    description: Optional[str] = None


class Problem(BaseModel):
    """Problem statement."""
    statement: str
    context: Optional[str] = None


class Constraints(BaseModel):
    """System constraints."""
    offline_ok: bool = True
    budget_tokens: int = 80000
    max_duration_minutes: int = 30


class SuccessMetrics(BaseModel):
    """Success metrics and acceptance criteria."""
    metrics: List[str] = Field(default_factory=list)


class DiagramScope(BaseModel):
    """Diagram generation scope."""
    include_sequence: bool = True
    include_lifecycle: bool = True
    include_architecture: bool = False


class ContractsData(BaseModel):
    """Contract and schema data."""
    generate_schemas: bool = False
    api_specs: List[str] = Field(default_factory=list)


class TestStrategy(BaseModel):
    """Testing strategy configuration."""
    unit_tests: bool = True
    integration_tests: bool = True
    e2e_tests: bool = False


class Operations(BaseModel):
    """Operations and deployment configuration."""
    ci_cd: bool = False
    monitoring: bool = False
    logging: bool = True


class Export(BaseModel):
    """Export configuration."""
    formats: List[str] = Field(default_factory=lambda: ["markdown"])
    bundle: bool = False


class SourceSpec(BaseModel):
    """Main source specification."""
    meta: Meta
    problem: Problem
    constraints: Constraints = Field(default_factory=Constraints)
    success_metrics: SuccessMetrics = Field(default_factory=SuccessMetrics)
    diagram_scope: DiagramScope = Field(default_factory=DiagramScope)
    contracts_data: ContractsData = Field(default_factory=ContractsData)
    test_strategy: TestStrategy = Field(default_factory=TestStrategy)
    operations: Operations = Field(default_factory=Operations)
    export: Export = Field(default_factory=Export)
    
    def is_valid(self) -> bool:
        """Check if the spec is valid."""
        try:
            self.model_validate(self.model_dump())
            return True
        except Exception:
            return False


class ValidationError(BaseModel):
    """Validation error with JSON pointer."""
    json_pointer: str
    message: str


class ValidationResult(BaseModel):
    """Result of spec validation."""
    ok: bool
    errors: List[ValidationError] = Field(default_factory=list)


class RunContext(BaseModel):
    """Runtime context for a generation run."""
    run_id: UUID
    offline: bool = False
    dials: Dials = Field(default_factory=Dials)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    out_dir: Path
    
    class Config:
        arbitrary_types_allowed = True


class PipelineEvent(BaseModel):
    """Audit log event."""
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    run_id: UUID
    stage: str = "unknown"
    event: str = ""
    note: str
    duration_ms: Optional[int] = None
    level: str = "info"
    details: Dict[str, Any] = Field(default_factory=dict)


class Template(BaseModel):
    """Template definition."""
    path: Path
    type: TemplateType
    version: str = "1.0.0"
    
    class Config:
        arbitrary_types_allowed = True