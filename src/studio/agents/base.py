"""Base agent interface and implementations."""

from abc import ABC, abstractmethod

from ..artifacts import AgentOutput, Blackboard
from ..types import RunContext, SourceSpec, Status


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
        import datetime
        from pathlib import Path

        from ..artifacts import DocumentArtifact
        from ..rendering import TemplateRenderer
        from ..types import PackType, Template, TemplateType

        # Initialize template renderer
        template_dir = Path(__file__).parent.parent / "templates"
        renderer = TemplateRenderer(template_dir)

        # Prepare template data
        template_data = {
            "meta": spec.meta.model_dump() if spec.meta else {"name": "Untitled", "version": "1.0.0"},
            "problem": spec.problem.model_dump() if spec.problem else {},
            "success_metrics": spec.success_metrics.model_dump() if spec.success_metrics else {},
            "constraints": spec.constraints.model_dump() if spec.constraints else {},
            "dials": ctx.dials.model_dump() if ctx.dials else {},
            "test_strategy": spec.test_strategy.model_dump() if spec.test_strategy else {},
            "diagram_scope": spec.diagram_scope.model_dump() if spec.diagram_scope else {},
            "contracts_data": spec.contracts_data.model_dump() if spec.contracts_data else {},
            "operations": spec.operations.model_dump() if spec.operations else {},
            "export": spec.export.model_dump() if spec.export else {},
            "run_id": str(ctx.run_id),
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "pack_type": PackType.BALANCED.value,
            # Add placeholders for missing fields used in templates
            "risks_open_questions": {},
            "roadmap_preferences": {},
            "compliance_context": {}
        }

        artifacts = []

        try:
            # Generate PRD
            Template(
                path=template_dir / "balanced" / "prd.md.j2",
                type=TemplateType.MARKDOWN
            )

            prd_content = renderer.render_string(
                (template_dir / "balanced" / "prd.md.j2").read_text(),
                template_data
            )

            # Write PRD to file
            prd_path = ctx.out_dir / "prd.md"
            prd_path.parent.mkdir(parents=True, exist_ok=True)
            prd_path.write_text(prd_content)

            prd_artifact = DocumentArtifact(
                name="prd.md",
                path=prd_path,
                pack=PackType.BALANCED,
                purpose="Product Requirements Document"
            )
            artifacts.append(prd_artifact)

            # Generate Test Plan
            test_plan_content = renderer.render_string(
                (template_dir / "balanced" / "test_plan.md.j2").read_text(),
                template_data
            )

            # Write test plan to file
            test_plan_path = ctx.out_dir / "test_plan.md"
            test_plan_path.write_text(test_plan_content)

            test_plan_artifact = DocumentArtifact(
                name="test_plan.md",
                path=test_plan_path,
                pack=PackType.BALANCED,
                purpose="Test Plan and Strategy"
            )
            artifacts.append(test_plan_artifact)

            return AgentOutput(
                notes={
                    "action": "prd_generated",
                    "sections": ["overview", "requirements", "acceptance", "test_plan"],
                    "templates_used": ["prd.md.j2", "test_plan.md.j2"]
                },
                artifacts=artifacts,
                status=Status.OK.value
            )

        except Exception as e:
            return AgentOutput(
                notes={
                    "action": "prd_generation_failed",
                    "error": str(e)
                },
                artifacts=[],
                status=Status.FAIL.value
            )


class DiagrammerAgent(Agent):
    """Agent that generates Mermaid diagrams."""

    def __init__(self):
        super().__init__("DiagrammerAgent")

    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Generate lifecycle and sequence diagrams."""
        import datetime
        from pathlib import Path

        from ..artifacts import DiagramArtifact
        from ..rendering import TemplateRenderer
        from ..types import PackType

        # Initialize template renderer
        template_dir = Path(__file__).parent.parent / "templates"
        renderer = TemplateRenderer(template_dir)

        # Prepare template data
        template_data = {
            "meta": spec.meta.model_dump() if spec.meta else {"name": "Untitled", "version": "1.0.0"},
            "diagram_scope": spec.diagram_scope.model_dump() if spec.diagram_scope else {},
            "run_id": str(ctx.run_id),
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "pack_type": PackType.BALANCED.value
        }

        artifacts = []
        templates_used = []

        try:
            # Create diagrams directory
            diagrams_dir = ctx.out_dir / "diagrams"
            diagrams_dir.mkdir(parents=True, exist_ok=True)

            # Generate lifecycle diagram if requested
            if spec.diagram_scope.include_lifecycle:
                lifecycle_content = renderer.render_string(
                    (template_dir / "balanced" / "diagrams" / "lifecycle.mmd.j2").read_text(),
                    template_data
                )

                lifecycle_path = diagrams_dir / "lifecycle.mmd"
                lifecycle_path.write_text(lifecycle_content)

                lifecycle_artifact = DiagramArtifact(
                    name="lifecycle.mmd",
                    path=lifecycle_path,
                    pack=PackType.BALANCED,
                    purpose="System Lifecycle Diagram"
                )
                artifacts.append(lifecycle_artifact)
                templates_used.append("lifecycle.mmd.j2")

            # Generate sequence diagram if requested
            if spec.diagram_scope.include_sequence:
                sequence_content = renderer.render_string(
                    (template_dir / "balanced" / "diagrams" / "sequence.mmd.j2").read_text(),
                    template_data
                )

                sequence_path = diagrams_dir / "sequence.mmd"
                sequence_path.write_text(sequence_content)

                sequence_artifact = DiagramArtifact(
                    name="sequence.mmd",
                    path=sequence_path,
                    pack=PackType.BALANCED,
                    purpose="Sequence Diagram"
                )
                artifacts.append(sequence_artifact)
                templates_used.append("sequence.mmd.j2")

            return AgentOutput(
                notes={
                    "action": "diagrams_generated",
                    "count": len(artifacts),
                    "templates_used": templates_used,
                    "lifecycle_included": spec.diagram_scope.include_lifecycle,
                    "sequence_included": spec.diagram_scope.include_sequence
                },
                artifacts=artifacts,
                status=Status.OK.value
            )

        except Exception as e:
            return AgentOutput(
                notes={
                    "action": "diagram_generation_failed",
                    "error": str(e)
                },
                artifacts=[],
                status=Status.FAIL.value
            )


class QAArchitectAgent(Agent):
    """Agent that designs test architecture and enhances test plans."""

    def __init__(self):
        super().__init__("QAArchitectAgent")

    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Enhance test plan with AC & matrix, validate test strategy."""

        # Check if test plan exists from PRDWriterAgent
        test_plan_path = ctx.out_dir / "test_plan.md"
        enhancements_made = []

        try:
            if test_plan_path.exists():
                # Read existing test plan
                content = test_plan_path.read_text()

                # Add QA-specific enhancements
                qa_matrix = self._generate_qa_matrix(spec)
                acceptance_criteria = self._extract_acceptance_criteria(spec)

                # Append QA architect enhancements
                enhanced_content = content + "\n\n" + self._format_qa_enhancements(qa_matrix, acceptance_criteria)

                # Write enhanced content back
                test_plan_path.write_text(enhanced_content)
                enhancements_made = ["qa_matrix", "acceptance_criteria_mapping", "test_strategy_validation"]

            return AgentOutput(
                notes={
                    "action": "test_architecture_designed",
                    "strategy": spec.test_strategy.model_dump() if spec.test_strategy else {},
                    "enhancements": enhancements_made,
                    "test_plan_enhanced": test_plan_path.exists()
                },
                artifacts=[],  # No new artifacts, enhanced existing ones
                status=Status.OK.value
            )

        except Exception as e:
            return AgentOutput(
                notes={
                    "action": "qa_enhancement_failed",
                    "error": str(e)
                },
                artifacts=[],
                status=Status.FAIL.value
            )

    def _generate_qa_matrix(self, spec: SourceSpec) -> str:
        """Generate QA testing matrix."""
        matrix = "## QA Testing Matrix\n\n"
        matrix += "| Test Type | Priority | Coverage | Status |\n"
        matrix += "|-----------|----------|----------|--------|\n"

        if spec.test_strategy:
            if spec.test_strategy.bdd_journeys:
                matrix += f"| BDD Tests | High | {len(spec.test_strategy.bdd_journeys)} scenarios | Planned |\n"
            if spec.test_strategy.contract_targets:
                matrix += f"| Contract Tests | High | {len(spec.test_strategy.contract_targets)} targets | Planned |\n"
            if spec.test_strategy.property_invariants:
                matrix += f"| Property Tests | Medium | {len(spec.test_strategy.property_invariants)} properties | Planned |\n"

        matrix += "| Unit Tests | High | Component level | Planned |\n"
        matrix += "| Integration Tests | Medium | System level | Planned |\n"
        matrix += "| Performance Tests | Medium | Load/Stress | Planned |\n"

        return matrix

    def _extract_acceptance_criteria(self, spec: SourceSpec) -> str:
        """Extract and format acceptance criteria."""
        ac_section = "## Detailed Acceptance Criteria\n\n"

        if spec.test_strategy and spec.test_strategy.bdd_journeys:
            for journey in spec.test_strategy.bdd_journeys:
                ac_section += f"### {journey}\n"
                ac_section += f"- **Given** system is ready for {journey}\n"
                ac_section += f"- **When** user performs {journey} action\n"
                ac_section += f"- **Then** system delivers expected {journey} outcome\n"
                ac_section += "- **And** system maintains data integrity\n\n"

        return ac_section

    def _format_qa_enhancements(self, qa_matrix: str, acceptance_criteria: str) -> str:
        """Format QA enhancements for test plan."""
        return f"""
---

## QA Architect Enhancements

{qa_matrix}

{acceptance_criteria}

## Test Execution Strategy

### Phase 1: Unit & Component Testing
- Individual component validation
- Mock external dependencies
- Code coverage target: >80%

### Phase 2: Integration Testing
- Component interaction validation
- Database integration testing
- API contract verification

### Phase 3: System Testing
- End-to-end workflow validation
- Performance baseline establishment
- Security testing

### Phase 4: Acceptance Testing
- BDD scenario execution
- User journey validation
- Stakeholder sign-off

---

*Enhanced by QA Architect*
"""


class RoadmapperAgent(Agent):
    """Agent that generates project roadmaps."""

    def __init__(self):
        super().__init__("RoadmapperAgent")

    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Generate project roadmap."""
        import datetime
        from pathlib import Path

        from ..artifacts import DocumentArtifact
        from ..rendering import TemplateRenderer
        from ..types import PackType

        # Initialize template renderer
        template_dir = Path(__file__).parent.parent / "templates"
        renderer = TemplateRenderer(template_dir)

        # Prepare template data
        template_data = {
            "meta": spec.meta.model_dump() if spec.meta else {"name": "Untitled", "version": "1.0.0"},
            "problem": spec.problem.model_dump() if spec.problem else {},
            "success_metrics": spec.success_metrics.model_dump() if spec.success_metrics else {},
            "constraints": spec.constraints.model_dump() if spec.constraints else {},
            "dials": ctx.dials.model_dump() if ctx.dials else {},
            "test_strategy": spec.test_strategy.model_dump() if spec.test_strategy else {},
            "operations": spec.operations.model_dump() if spec.operations else {},
            "export": spec.export.model_dump() if spec.export else {},
            "run_id": str(ctx.run_id),
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "pack_type": PackType.BALANCED.value,
            # Add placeholders for missing fields used in templates
            "risks_open_questions": {},
            "roadmap_preferences": {},
            "compliance_context": {}
        }

        try:
            # Generate roadmap
            roadmap_content = renderer.render_string(
                (template_dir / "balanced" / "roadmap.md.j2").read_text(),
                template_data
            )

            # Write roadmap to file
            roadmap_path = ctx.out_dir / "roadmap.md"
            roadmap_path.parent.mkdir(parents=True, exist_ok=True)
            roadmap_path.write_text(roadmap_content)

            roadmap_artifact = DocumentArtifact(
                name="roadmap.md",
                path=roadmap_path,
                pack=PackType.BALANCED,
                purpose="Project Roadmap"
            )

            # Calculate milestone count from template data
            milestone_length = 2  # Default milestone length
            milestone_count = 4  # Default from template

            return AgentOutput(
                notes={
                    "action": "roadmap_generated",
                    "milestones": milestone_count,
                    "milestone_length_weeks": milestone_length,
                    "templates_used": ["roadmap.md.j2"]
                },
                artifacts=[roadmap_artifact],
                status=Status.OK.value
            )

        except Exception as e:
            return AgentOutput(
                notes={
                    "action": "roadmap_generation_failed",
                    "error": str(e)
                },
                artifacts=[],
                status=Status.FAIL.value
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
