"""Base agent interface and implementations."""

from abc import ABC, abstractmethod
from typing import Dict, Any

from ..types import SourceSpec, RunContext, Status
from ..artifacts import Blackboard, AgentOutput


class Agent(ABC):
    """Base agent interface."""
    
    def __init__(self, name: str):
        """Initialize agent with name."""
        self.name = name
    
    @abstractmethod
    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Run the agent with given context, spec, and blackboard."""
        pass


class FramerAgent(Agent):
    """Agent that frames and fills missing spec fields."""
    
    def __init__(self):
        super().__init__("FramerAgent")
    
    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Frame the spec by filling missing mandatory fields."""
        filled_fields = []
        overrides = []
        
        # Create a mutable copy of the spec data
        spec_dict = spec.model_dump()
        
        # Check and fill missing meta fields
        if not spec_dict.get("meta", {}).get("description"):
            spec_dict["meta"]["description"] = "Generated description - needs manual review"
            filled_fields.append("meta.description")
        
        # Check and fill missing problem context
        if not spec_dict.get("problem", {}).get("context"):
            spec_dict["problem"]["context"] = "Generated context - needs manual review"
            filled_fields.append("problem.context")
        
        # Check success metrics - ensure it has meaningful content
        success_metrics = spec_dict.get("success_metrics", {})
        if not success_metrics.get("metrics") or success_metrics.get("metrics") == []:
            spec_dict["success_metrics"]["metrics"] = ["User satisfaction > 80%", "Performance meets SLA"]
            filled_fields.append("success_metrics.metrics")
            overrides.append({
                "field": "success_metrics.metrics",
                "reason": "Empty metrics list replaced with default business metrics"
            })
        
        # Create updated spec from modified dict
        try:
            from ..types import SourceSpec
            updated_spec = SourceSpec(**spec_dict)
        except Exception as e:
            # If validation fails, return original spec
            updated_spec = spec
            overrides.append({
                "field": "validation",
                "reason": f"Failed to apply changes: {str(e)}"
            })
        
        notes = {
            "action": "framed_spec",
            "filled_fields": filled_fields,
            "overrides": overrides,
            "total_changes": len(filled_fields)
        }
        
        return AgentOutput(
            notes=notes,
            artifacts=[],
            updated_spec=updated_spec,
            status=Status.OK.value
        )


class LibrarianAgent(Agent):
    """Agent that fetches and indexes research content."""
    
    def __init__(self):
        super().__init__("LibrarianAgent")
    
    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Fetch and index research content."""
        if ctx.offline:
            return AgentOutput(
                notes={"action": "skipped_research", "reason": "offline_mode"},
                artifacts=[],
                status=Status.OK.value
            )
        
        # Stub implementation
        return AgentOutput(
            notes={"action": "research_completed", "sources": []},
            artifacts=[],
            status=Status.OK.value
        )


class SlicerAgent(Agent):
    """Agent that slices and organizes content."""
    
    def __init__(self):
        super().__init__("SlicerAgent")
    
    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Slice and organize content for templates."""
        return AgentOutput(
            notes={"action": "content_sliced"},
            artifacts=[],
            status=Status.OK.value
        )


class PRDWriterAgent(Agent):
    """Agent that writes PRD documents."""
    
    def __init__(self):
        super().__init__("PRDWriterAgent")
    
    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Write PRD and test plan documents."""
        from ..artifacts import DocumentArtifact
        from ..types import PackType
        
        # Create stub PRD artifact
        prd_artifact = DocumentArtifact(
            name="prd.md",
            path=ctx.out_dir / "prd.md",
            pack=PackType.BALANCED,
            purpose="Product Requirements Document"
        )
        
        return AgentOutput(
            notes={"action": "prd_generated", "sections": ["overview", "requirements", "acceptance"]},
            artifacts=[prd_artifact],
            status=Status.OK.value
        )


class DiagrammerAgent(Agent):
    """Agent that generates Mermaid diagrams."""
    
    def __init__(self):
        super().__init__("DiagrammerAgent")
    
    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Generate lifecycle and sequence diagrams."""
        from ..artifacts import DiagramArtifact
        from ..types import PackType
        
        artifacts = []
        if spec.diagram_scope.include_lifecycle:
            lifecycle_artifact = DiagramArtifact(
                name="lifecycle.mmd",
                path=ctx.out_dir / "diagrams" / "lifecycle.mmd",
                pack=PackType.BALANCED,
                purpose="System Lifecycle Diagram"
            )
            artifacts.append(lifecycle_artifact)
        
        if spec.diagram_scope.include_sequence:
            sequence_artifact = DiagramArtifact(
                name="sequence.mmd", 
                path=ctx.out_dir / "diagrams" / "sequence.mmd",
                pack=PackType.BALANCED,
                purpose="Sequence Diagram"
            )
            artifacts.append(sequence_artifact)
        
        return AgentOutput(
            notes={"action": "diagrams_generated", "count": len(artifacts)},
            artifacts=artifacts,
            status=Status.OK.value
        )


class QAArchitectAgent(Agent):
    """Agent that designs test architecture."""
    
    def __init__(self):
        super().__init__("QAArchitectAgent")
    
    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Generate test plan and architecture."""
        from ..artifacts import DocumentArtifact
        from ..types import PackType
        
        test_plan_artifact = DocumentArtifact(
            name="test_plan.md",
            path=ctx.out_dir / "test_plan.md", 
            pack=PackType.BALANCED,
            purpose="Test Plan and Strategy"
        )
        
        return AgentOutput(
            notes={"action": "test_architecture_designed", "strategy": spec.test_strategy.model_dump()},
            artifacts=[test_plan_artifact],
            status=Status.OK.value
        )


class RoadmapperAgent(Agent):
    """Agent that generates project roadmaps."""
    
    def __init__(self):
        super().__init__("RoadmapperAgent")
    
    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Generate project roadmap."""
        from ..artifacts import DocumentArtifact
        from ..types import PackType
        
        roadmap_artifact = DocumentArtifact(
            name="roadmap.md",
            path=ctx.out_dir / "roadmap.md",
            pack=PackType.BALANCED, 
            purpose="Project Roadmap"
        )
        
        return AgentOutput(
            notes={"action": "roadmap_generated", "milestones": []},
            artifacts=[roadmap_artifact],
            status=Status.OK.value
        )


class CriticAgent(Agent):
    """Agent that reviews and critiques outputs."""
    
    def __init__(self):
        super().__init__("CriticAgent")
    
    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Review and critique generated artifacts."""
        return AgentOutput(
            notes={"action": "review_completed", "issues_found": 0},
            artifacts=[],
            status=Status.OK.value
        )


class PackagerAgent(Agent):
    """Agent that packages outputs into bundles."""
    
    def __init__(self):
        super().__init__("PackagerAgent")
    
    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Package artifacts into zip bundles."""
        from ..artifacts import ZipArtifact
        from ..types import PackType
        
        if spec.export.bundle:
            zip_artifact = ZipArtifact(
                name="output_bundle.zip",
                path=ctx.out_dir / "output_bundle.zip",
                pack=PackType.BALANCED,
                purpose="Bundled Output Package"
            )
            
            return AgentOutput(
                notes={"action": "bundle_created", "artifact_count": len(blackboard.artifacts)},
                artifacts=[zip_artifact],
                status=Status.OK.value
            )
        
        return AgentOutput(
            notes={"action": "packaging_skipped", "reason": "bundle_disabled"},
            artifacts=[],
            status=Status.OK.value
        )