"""Artifact classes for generated outputs."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from .types import PackType
from .templates.template_version import get_template_set_version, get_template_commit


class Artifact(BaseModel, ABC):
    """Abstract base artifact."""
    name: str
    path: Path
    pack: PackType
    purpose: str
    
    class Config:
        arbitrary_types_allowed = True


class DocumentArtifact(Artifact):
    """Markdown document artifact."""
    format: str = "md"


class DiagramArtifact(Artifact):
    """Mermaid diagram artifact."""
    format: str = "mmd"


class SchemaArtifact(Artifact):
    """JSON schema artifact."""
    format: str = "json"


class CIArtifact(Artifact):
    """CI workflow artifact."""
    format: str = "yml"


class ZipArtifact(Artifact):
    """Zip bundle artifact."""
    format: str = "zip"


class ArtifactIndex(BaseModel):
    """Index of all generated artifacts."""
    run_id: UUID
    generated_at: str
    template_set: str = Field(default_factory=lambda: get_template_set_version())
    template_commit: str = Field(default_factory=get_template_commit)
    artifacts: List[Artifact] = Field(default_factory=list)
    
    def add(self, artifact: Artifact) -> None:
        """Add an artifact to the index."""
        self.artifacts.append(artifact)
    
    def get_by_pack(self, pack: PackType) -> List[Artifact]:
        """Get artifacts by pack type."""
        return [a for a in self.artifacts if a.pack == pack]
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return self.model_dump_json(indent=2)


class Blackboard(BaseModel):
    """Shared blackboard for agent communication."""
    artifacts: List[Artifact] = Field(default_factory=list)
    notes: Dict[str, Any] = Field(default_factory=dict)
    
    def add_artifact(self, artifact: Artifact) -> None:
        """Add an artifact to the blackboard."""
        self.artifacts.append(artifact)
    
    def get_by_pack(self, pack: PackType) -> List[Artifact]:
        """Get artifacts by pack type."""
        return [a for a in self.artifacts if a.pack == pack]
    
    def publish(self, pack_type: str = "balanced") -> ArtifactIndex:
        """Publish artifacts to an index."""
        from uuid import uuid4
        from datetime import datetime
        
        index = ArtifactIndex(
            run_id=uuid4(),
            generated_at=datetime.utcnow().isoformat() + "Z",
            template_set=get_template_set_version(pack_type),
            template_commit=get_template_commit()
        )
        
        for artifact in self.artifacts:
            index.add(artifact)
        
        return index


class AgentOutput(BaseModel):
    """Output from an agent execution."""
    notes: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[Artifact] = Field(default_factory=list) 
    updated_spec: Optional[Any] = None  # Will be SourceSpec, but avoiding circular import
    status: str  # Status enum value as string
    
    class Config:
        arbitrary_types_allowed = True