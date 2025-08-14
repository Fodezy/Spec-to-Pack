"""Artifact classes for generated outputs."""

import hashlib
from abc import ABC
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .templates.template_version import get_template_commit, get_template_set_version
from .types import PackType


class Artifact(BaseModel, ABC):
    """Abstract base artifact."""
    name: str
    path: Path
    pack: PackType
    purpose: str
    sha256_hash: str | None = None

    class Config:
        arbitrary_types_allowed = True

    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of the file content."""
        if not self.path.exists():
            raise FileNotFoundError(f"Cannot hash non-existent file: {self.path}")
        
        sha256_hash = hashlib.sha256()
        with open(self.path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        self.sha256_hash = sha256_hash.hexdigest()
        return self.sha256_hash

    def verify_integrity(self) -> bool:
        """Verify file integrity against stored hash."""
        if self.sha256_hash is None:
            return False
        
        try:
            current_hash = hashlib.sha256()
            with open(self.path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    current_hash.update(chunk)
            return current_hash.hexdigest() == self.sha256_hash
        except FileNotFoundError:
            return False


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
    artifacts: list[Artifact] = Field(default_factory=list)

    def add(self, artifact: Artifact) -> None:
        """Add an artifact to the index."""
        self.artifacts.append(artifact)

    def get_by_pack(self, pack: PackType) -> list[Artifact]:
        """Get artifacts by pack type."""
        return [a for a in self.artifacts if a.pack == pack]

    def calculate_all_hashes(self) -> None:
        """Calculate SHA-256 hashes for all artifacts."""
        for artifact in self.artifacts:
            if artifact.path.exists():
                artifact.calculate_hash()

    def verify_manifest_integrity(self) -> dict[str, Any]:
        """Verify integrity of all artifacts in the manifest."""
        results = {
            "total_artifacts": len(self.artifacts),
            "verified": 0,
            "failed": 0,
            "missing": 0,
            "details": []
        }

        for artifact in self.artifacts:
            if not artifact.path.exists():
                results["missing"] += 1
                results["details"].append({
                    "name": artifact.name,
                    "status": "missing",
                    "path": str(artifact.path)
                })
            elif artifact.verify_integrity():
                results["verified"] += 1
                results["details"].append({
                    "name": artifact.name,
                    "status": "verified",
                    "hash": artifact.sha256_hash
                })
            else:
                results["failed"] += 1
                results["details"].append({
                    "name": artifact.name,
                    "status": "hash_mismatch",
                    "path": str(artifact.path),
                    "expected_hash": artifact.sha256_hash
                })

        results["integrity_ok"] = results["failed"] == 0 and results["missing"] == 0
        return results

    def to_json(self) -> str:
        """Convert to JSON string."""
        return self.model_dump_json(indent=2)


class Blackboard(BaseModel):
    """Shared blackboard for agent communication."""
    artifacts: list[Artifact] = Field(default_factory=list)
    notes: dict[str, Any] = Field(default_factory=dict)

    def add_artifact(self, artifact: Artifact) -> None:
        """Add an artifact to the blackboard."""
        self.artifacts.append(artifact)

    def get_by_pack(self, pack: PackType) -> list[Artifact]:
        """Get artifacts by pack type."""
        return [a for a in self.artifacts if a.pack == pack]

    def publish(self, pack_type: str = "balanced") -> ArtifactIndex:
        """Publish artifacts to an index."""
        from datetime import datetime
        from uuid import uuid4

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
    notes: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[Artifact] = Field(default_factory=list)
    updated_spec: Any | None = None  # Will be SourceSpec, but avoiding circular import
    status: str  # Status enum value as string

    class Config:
        arbitrary_types_allowed = True
