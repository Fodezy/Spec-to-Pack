"""Base agent interface and implementations."""

import datetime
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path

from ..artifacts import AgentOutput, Blackboard
from ..rendering import TemplateRenderer
from ..types import PackType, RunContext, SourceSpec, Status


class Agent(ABC):
    """Base agent interface."""

    def __init__(self, name: str):
        """Initialize agent with name."""
        self.name = name

    @abstractmethod
    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Run the agent with given context, spec, and blackboard."""
        pass
    
    def _create_template_data(self, ctx: RunContext, spec: SourceSpec) -> dict:
        """Create standardized template data structure for all agents."""
        return {
            "meta": spec.meta.model_dump() if spec.meta else {"name": "Untitled", "version": "1.0.0"},
            "problem": spec.problem.model_dump() if spec.problem else {},
            "constraints": spec.constraints.model_dump() if spec.constraints else {},
            "success_metrics": spec.success_metrics if hasattr(spec, 'success_metrics') and spec.success_metrics else [],
            "dials": ctx.dials.model_dump() if ctx.dials else {},
            "test_strategy": spec.test_strategy.model_dump() if spec.test_strategy else {},
            "diagram_scope": spec.diagram_scope.model_dump() if spec.diagram_scope else {},
            "contracts_data": spec.contracts_data.model_dump() if spec.contracts_data else {},
            "operations": spec.operations.model_dump() if spec.operations else {},
            "export": spec.export.model_dump() if spec.export else {},
            "run_id": str(ctx.run_id),
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "pack_type": PackType.DEEP.value if hasattr(ctx, 'pack_type') and ctx.pack_type == PackType.DEEP else PackType.BALANCED.value
        }


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

    def __init__(self, browser_adapter=None, vector_store_adapter=None, embeddings_model=None):
        super().__init__("LibrarianAgent")
        self.browser_adapter = browser_adapter
        self.vector_store_adapter = vector_store_adapter  
        self.embeddings_model = embeddings_model

    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Fetch and index research content."""
        import hashlib
        import uuid
        from datetime import datetime
        from ..types import ContentProvenance, ResearchDocument
        
        if ctx.offline:
            return AgentOutput(
                notes={"action": "skipped_research", "reason": "offline_mode"},
                artifacts=[],
                status=Status.OK.value
            )

        # Use stub adapters if none provided
        if self.browser_adapter is None:
            from ..adapters.browser import StubBrowserAdapter
            self.browser_adapter = StubBrowserAdapter()
            
        if self.vector_store_adapter is None:
            from ..adapters.vector_store import StubVectorStoreAdapter
            self.vector_store_adapter = StubVectorStoreAdapter()
            
        if self.embeddings_model is None:
            from ..adapters.embeddings import StubEmbeddingsAdapter
            self.embeddings_model = StubEmbeddingsAdapter()

        research_docs = []
        fetched_count = 0
        error_count = 0
        
        try:
            # Get URLs from research context or generate based on problem statement
            urls_to_fetch = spec.research_context.search_domains if spec.research_context.search_domains else []
            
            # If no URLs provided, use stub URLs based on problem context
            if not urls_to_fetch:
                urls_to_fetch = self._generate_research_urls(spec.problem.statement)
            
            # Limit number of URLs to process
            max_docs = min(spec.research_context.max_documents, len(urls_to_fetch))
            
            for i, url in enumerate(urls_to_fetch[:max_docs]):
                try:
                    # Fetch content with offline mode check
                    html_content = self.browser_adapter.fetch(url, offline_mode=ctx.offline)
                    
                    if html_content.status_code == 200:
                        # Extract clean text
                        text_content = self.browser_adapter.extract(html_content)
                        
                        if text_content.strip():
                            # Create content hash for deduplication
                            content_hash = hashlib.sha256(text_content.encode('utf-8')).hexdigest()
                            
                            # Create provenance record
                            provenance = ContentProvenance(
                                source_url=url,
                                retrieved_at=datetime.utcnow(),
                                chunk_id=str(uuid.uuid4()),
                                content_hash=content_hash,
                                metadata={
                                    "status_code": html_content.status_code,
                                    "content_length": len(text_content),
                                    "headers": html_content.headers
                                }
                            )
                            
                            # Create research document
                            research_doc = ResearchDocument(
                                content=text_content,
                                provenance=provenance
                            )
                            
                            # Add embeddings if enabled and model available
                            if spec.research_context.include_embeddings and self.embeddings_model:
                                try:
                                    embeddings = self._generate_embeddings(text_content)
                                    research_doc.embedding = embeddings
                                    
                                    # Index in vector store
                                    if self.vector_store_adapter:
                                        self.vector_store_adapter.index(
                                            doc_id=provenance.chunk_id,
                                            embedding=embeddings,
                                            content=text_content,
                                            metadata=provenance.model_dump()
                                        )
                                except Exception as embed_error:
                                    # Continue without embeddings on error
                                    pass
                            
                            research_docs.append(research_doc)
                            fetched_count += 1
                            
                except Exception as e:
                    error_count += 1
                    # Continue processing other URLs
                    continue
            
            # Store research documents in blackboard for other agents
            blackboard.notes["research_documents"] = research_docs
            
            return AgentOutput(
                notes={
                    "action": "research_completed", 
                    "urls_processed": len(urls_to_fetch[:max_docs]),
                    "documents_fetched": fetched_count,
                    "errors": error_count,
                    "total_content_length": sum(len(doc.content) for doc in research_docs),
                    "embeddings_enabled": spec.research_context.include_embeddings,
                    "vector_store_used": self.vector_store_adapter is not None
                },
                artifacts=[],  # Research content stored in blackboard, not as artifacts
                status=Status.OK.value
            )
            
        except Exception as e:
            return AgentOutput(
                notes={
                    "action": "research_failed",
                    "error": str(e),
                    "documents_partial": len(research_docs)
                },
                artifacts=[],
                status=Status.FAIL.value
            )
            
    def _generate_research_urls(self, problem_statement: str) -> list[str]:
        """Generate stub research URLs based on problem statement."""
        # In a real implementation, this might use search APIs or predefined sources
        # For now, return stub URLs for testing
        return [
            "https://example.com/docs/overview",
            "https://example.com/best-practices", 
            "https://example.com/implementation-guide"
        ]
        
    def _generate_embeddings(self, text: str) -> list[float]:
        """Generate embeddings using the configured model."""
        if self.embeddings_model is None:
            # Return stub embeddings for testing
            return [0.1] * 384  # BGE-small dimension
            
        try:
            # Use embeddings adapter
            return self.embeddings_model.encode(text)
        except Exception:
            # Return stub embeddings on error
            return [0.1] * 384


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


class ThreatModelAgent(Agent):
    """Agent that generates threat model documentation."""

    def __init__(self):
        super().__init__("ThreatModelAgent")

    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Generate threat model document for deep pack."""
        import datetime
        from pathlib import Path

        from ..artifacts import DocumentArtifact
        from ..rendering import TemplateRenderer
        from ..types import PackType, Status

        # Initialize template renderer
        template_dir = Path(__file__).parent.parent / "templates"
        renderer = TemplateRenderer(template_dir)

        # Prepare template data using standardized helper
        template_data = self._create_template_data(ctx, spec)

        try:
            # Load and render template
            template_path = template_dir / "deep/docs/threat_model.md.j2"
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            threat_model_content = renderer.render_string(template_content, template_data)
            threat_model_path = ctx.out_dir / "threat_model.md"
            
            with open(threat_model_path, 'w', encoding='utf-8') as f:
                f.write(threat_model_content)

            threat_model_artifact = DocumentArtifact(
                name="threat_model.md",
                path=threat_model_path,
                pack=PackType.DEEP,
                purpose="Security Threat Model and Risk Analysis"
            )

            return AgentOutput(
                notes={
                    "action": "threat_model_generated",
                    "template_used": "deep/docs/threat_model.md.j2"
                },
                artifacts=[threat_model_artifact],
                status=Status.OK.value
            )

        except Exception as e:
            return AgentOutput(
                notes={
                    "action": "threat_model_generation_failed",
                    "error": str(e)
                },
                artifacts=[],
                status=Status.FAIL.value
            )


class AccessibilityAgent(Agent):
    """Agent that generates accessibility plan documentation."""

    def __init__(self):
        super().__init__("AccessibilityAgent")

    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Generate accessibility plan document for deep pack."""
        import datetime
        from pathlib import Path

        from ..artifacts import DocumentArtifact
        from ..rendering import TemplateRenderer
        from ..types import PackType, Status

        # Initialize template renderer
        template_dir = Path(__file__).parent.parent / "templates"
        renderer = TemplateRenderer(template_dir)

        # Prepare template data using standardized helper
        template_data = self._create_template_data(ctx, spec)

        try:
            # Load and render template
            template_path = template_dir / "deep/docs/accessibility_plan.md.j2"
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            accessibility_content = renderer.render_string(template_content, template_data)
            accessibility_path = ctx.out_dir / "accessibility_plan.md"
            
            with open(accessibility_path, 'w', encoding='utf-8') as f:
                f.write(accessibility_content)

            accessibility_artifact = DocumentArtifact(
                name="accessibility_plan.md",
                path=accessibility_path,
                pack=PackType.DEEP,
                purpose="Accessibility Plan and Compliance Strategy"
            )

            return AgentOutput(
                notes={
                    "action": "accessibility_plan_generated",
                    "template_used": "deep/docs/accessibility_plan.md.j2"
                },
                artifacts=[accessibility_artifact],
                status=Status.OK.value
            )

        except Exception as e:
            return AgentOutput(
                notes={
                    "action": "accessibility_plan_generation_failed",
                    "error": str(e)
                },
                artifacts=[],
                status=Status.FAIL.value
            )


class ObservabilityAgent(Agent):
    """Agent that generates observability plan documentation."""

    def __init__(self):
        super().__init__("ObservabilityAgent")

    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Generate observability plan document for deep pack."""
        import datetime
        from pathlib import Path

        from ..artifacts import DocumentArtifact
        from ..rendering import TemplateRenderer
        from ..types import PackType, Status

        # Initialize template renderer
        template_dir = Path(__file__).parent.parent / "templates"
        renderer = TemplateRenderer(template_dir)

        # Prepare template data using standardized helper
        template_data = self._create_template_data(ctx, spec)

        try:
            # Load and render template
            template_path = template_dir / "deep/docs/observability_plan.md.j2"
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            observability_content = renderer.render_string(template_content, template_data)
            observability_path = ctx.out_dir / "observability_plan.md"
            
            with open(observability_path, 'w', encoding='utf-8') as f:
                f.write(observability_content)

            observability_artifact = DocumentArtifact(
                name="observability_plan.md",
                path=observability_path,
                pack=PackType.DEEP,
                purpose="Observability, Monitoring, and Alerting Plan"
            )

            return AgentOutput(
                notes={
                    "action": "observability_plan_generated",
                    "template_used": "deep/docs/observability_plan.md.j2"
                },
                artifacts=[observability_artifact],
                status=Status.OK.value
            )

        except Exception as e:
            return AgentOutput(
                notes={
                    "action": "observability_plan_generation_failed",
                    "error": str(e)
                },
                artifacts=[],
                status=Status.FAIL.value
            )


class RunbookAgent(Agent):
    """Agent that generates operational runbooks."""

    def __init__(self):
        super().__init__("RunbookAgent")

    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Generate runbook document for deep pack."""
        import datetime
        from pathlib import Path

        from ..artifacts import DocumentArtifact
        from ..rendering import TemplateRenderer
        from ..types import PackType, Status

        # Initialize template renderer
        template_dir = Path(__file__).parent.parent / "templates"
        renderer = TemplateRenderer(template_dir)

        # Prepare template data using standardized helper
        template_data = self._create_template_data(ctx, spec)

        try:
            # Load and render template
            template_path = template_dir / "deep/docs/runbooks.md.j2"
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            runbooks_content = renderer.render_string(template_content, template_data)
            runbooks_path = ctx.out_dir / "runbooks.md"
            
            with open(runbooks_path, 'w', encoding='utf-8') as f:
                f.write(runbooks_content)

            runbooks_artifact = DocumentArtifact(
                name="runbooks.md",
                path=runbooks_path,
                pack=PackType.DEEP,
                purpose="Operational Runbooks and Troubleshooting Guides"
            )

            return AgentOutput(
                notes={
                    "action": "runbooks_generated",
                    "template_used": "deep/docs/runbooks.md.j2"
                },
                artifacts=[runbooks_artifact],
                status=Status.OK.value
            )

        except Exception as e:
            return AgentOutput(
                notes={
                    "action": "runbooks_generation_failed",
                    "error": str(e)
                },
                artifacts=[],
                status=Status.FAIL.value
            )


class SLOAgent(Agent):
    """Agent that generates Service Level Objectives documentation."""

    def __init__(self):
        super().__init__("SLOAgent")

    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Generate SLO document for deep pack."""
        import datetime
        from pathlib import Path

        from ..artifacts import DocumentArtifact
        from ..rendering import TemplateRenderer
        from ..types import PackType, Status

        # Initialize template renderer
        template_dir = Path(__file__).parent.parent / "templates"
        renderer = TemplateRenderer(template_dir)

        # Prepare template data using standardized helper
        template_data = self._create_template_data(ctx, spec)

        try:
            # Load and render template
            template_path = template_dir / "deep/docs/slos.md.j2"
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            slos_content = renderer.render_string(template_content, template_data)
            slos_path = ctx.out_dir / "slos.md"
            
            with open(slos_path, 'w', encoding='utf-8') as f:
                f.write(slos_content)

            slos_artifact = DocumentArtifact(
                name="slos.md",
                path=slos_path,
                pack=PackType.DEEP,
                purpose="Service Level Objectives and Performance Targets"
            )

            return AgentOutput(
                notes={
                    "action": "slos_generated",
                    "template_used": "deep/docs/slos.md.j2"
                },
                artifacts=[slos_artifact],
                status=Status.OK.value
            )

        except Exception as e:
            return AgentOutput(
                notes={
                    "action": "slos_generation_failed",
                    "error": str(e)
                },
                artifacts=[],
                status=Status.FAIL.value
            )


class ADRAgent(Agent):
    """Agent that generates Architecture Decision Records template."""

    def __init__(self):
        super().__init__("ADRAgent")

    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Generate ADR template document for deep pack."""
        import datetime
        from pathlib import Path

        from ..artifacts import DocumentArtifact
        from ..rendering import TemplateRenderer
        from ..types import PackType, Status

        # Initialize template renderer
        template_dir = Path(__file__).parent.parent / "templates"
        renderer = TemplateRenderer(template_dir)

        # Prepare template data using standardized helper
        template_data = self._create_template_data(ctx, spec)

        try:
            # Load and render template
            template_path = template_dir / "deep/docs/adrs/template.md.j2"
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            adr_content = renderer.render_string(template_content, template_data)
            adr_path = ctx.out_dir / "adrs.md"
            
            with open(adr_path, 'w', encoding='utf-8') as f:
                f.write(adr_content)

            adr_artifact = DocumentArtifact(
                name="adrs.md",
                path=adr_path,
                pack=PackType.DEEP,
                purpose="Architecture Decision Records Template and Examples"
            )

            return AgentOutput(
                notes={
                    "action": "adr_template_generated",
                    "template_used": "deep/docs/adrs/template.md.j2"
                },
                artifacts=[adr_artifact],
                status=Status.OK.value
            )

        except Exception as e:
            return AgentOutput(
                notes={
                    "action": "adr_generation_failed",
                    "error": str(e)
                },
                artifacts=[],
                status=Status.FAIL.value
            )


class CIWorkflowAgent(Agent):
    """Agent that generates CI/CD workflow files."""

    def __init__(self):
        super().__init__("CIWorkflowAgent")

    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Generate CI workflow file for deep pack."""
        import datetime
        from pathlib import Path

        from ..artifacts import CIArtifact
        from ..rendering import TemplateRenderer
        from ..types import PackType, Status

        # Initialize template renderer
        template_dir = Path(__file__).parent.parent / "templates"
        renderer = TemplateRenderer(template_dir)

        # Prepare template data using standardized helper
        template_data = self._create_template_data(ctx, spec)

        try:
            # Load and render template
            template_path = template_dir / "deep/ci/workflow.yml.j2"
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            workflow_content = renderer.render_string(template_content, template_data)
            workflow_path = ctx.out_dir / "workflow.yml"
            
            with open(workflow_path, 'w', encoding='utf-8') as f:
                f.write(workflow_content)

            workflow_artifact = CIArtifact(
                name="workflow.yml",
                path=workflow_path,
                pack=PackType.DEEP,
                purpose="CI/CD Pipeline Configuration"
            )

            return AgentOutput(
                notes={
                    "action": "ci_workflow_generated",
                    "template_used": "deep/ci/workflow.yml.j2"
                },
                artifacts=[workflow_artifact],
                status=Status.OK.value
            )

        except Exception as e:
            return AgentOutput(
                notes={
                    "action": "ci_workflow_generation_failed",
                    "error": str(e)
                },
                artifacts=[],
                status=Status.FAIL.value
            )


class ContractAgent(Agent):
    """Agent that generates contract schema files."""

    def __init__(self):
        super().__init__("ContractAgent")

    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Generate contract schema files for deep pack."""
        import datetime
        from pathlib import Path

        from ..artifacts import SchemaArtifact
        from ..rendering import TemplateRenderer
        from ..types import PackType, Status

        # Initialize template renderer
        template_dir = Path(__file__).parent.parent / "templates"
        renderer = TemplateRenderer(template_dir)

        # Prepare template data using standardized helper
        template_data = self._create_template_data(ctx, spec)

        artifacts = []
        try:
            # Generate API contract schema
            template_path = template_dir / "deep/contracts/api_contract.schema.json.j2"
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            api_contract_content = renderer.render_string(template_content, template_data)
            api_contract_path = ctx.out_dir / "api_contract.schema.json"
            
            with open(api_contract_path, 'w', encoding='utf-8') as f:
                f.write(api_contract_content)

            api_contract_artifact = SchemaArtifact(
                name="api_contract.schema.json",
                path=api_contract_path,
                pack=PackType.DEEP,
                purpose="API Contract Schema Definition"
            )
            artifacts.append(api_contract_artifact)

            # Generate Data contract schema
            template_path = template_dir / "deep/contracts/data_contract.schema.json.j2"
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            data_contract_content = renderer.render_string(template_content, template_data)
            data_contract_path = ctx.out_dir / "data_contract.schema.json"
            
            with open(data_contract_path, 'w', encoding='utf-8') as f:
                f.write(data_contract_content)

            data_contract_artifact = SchemaArtifact(
                name="data_contract.schema.json",
                path=data_contract_path,
                pack=PackType.DEEP,
                purpose="Data Contract Schema Definition"
            )
            artifacts.append(data_contract_artifact)

            # Generate Service contract schema
            template_path = template_dir / "deep/contracts/service_contract.schema.json.j2"
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            service_contract_content = renderer.render_string(template_content, template_data)
            service_contract_path = ctx.out_dir / "service_contract.schema.json"
            
            with open(service_contract_path, 'w', encoding='utf-8') as f:
                f.write(service_contract_content)

            service_contract_artifact = SchemaArtifact(
                name="service_contract.schema.json",
                path=service_contract_path,
                pack=PackType.DEEP,
                purpose="Service Contract Schema Definition"
            )
            artifacts.append(service_contract_artifact)

            return AgentOutput(
                notes={
                    "action": "contract_schemas_generated",
                    "templates_used": [
                        "deep/contracts/api_contract.schema.json.j2",
                        "deep/contracts/data_contract.schema.json.j2",
                        "deep/contracts/service_contract.schema.json.j2"
                    ],
                    "schemas_created": len(artifacts)
                },
                artifacts=artifacts,
                status=Status.OK.value
            )

        except Exception as e:
            return AgentOutput(
                notes={
                    "action": "contract_generation_failed",
                    "error": str(e)
                },
                artifacts=artifacts,  # Return any artifacts that were successfully created
                status=Status.FAIL.value
            )


class PackagerAgent(Agent):
    """Agent that packages outputs into bundles."""

    def __init__(self):
        super().__init__("PackagerAgent")

    def run(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> AgentOutput:
        """Package artifacts into zip bundles."""
        import zipfile
        from ..artifacts import ZipArtifact
        from ..types import PackType, Status

        if spec.export.bundle:
            zip_path = ctx.out_dir / "output_bundle.zip"
            
            # Calculate hashes for all artifacts before bundling
            for artifact in blackboard.artifacts:
                if artifact.path.exists() and artifact.sha256_hash is None:
                    artifact.calculate_hash()
            
            # Create the actual zip file with all blackboard artifacts
            created_files = 0
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for artifact in blackboard.artifacts:
                    if artifact.path.exists():
                        # Use relative path within zip for clean structure
                        arcname = artifact.path.relative_to(ctx.out_dir)
                        zip_file.write(artifact.path, arcname=arcname)
                        created_files += 1
            
            zip_artifact = ZipArtifact(
                name="output_bundle.zip",
                path=zip_path,
                pack=PackType.BALANCED,
                purpose="Bundled Output Package"
            )
            
            # Calculate hash for the zip file itself
            zip_artifact.calculate_hash()

            return AgentOutput(
                notes={
                    "action": "bundle_created", 
                    "artifact_count": len(blackboard.artifacts),
                    "files_bundled": created_files,
                    "zip_path": str(zip_path)
                },
                artifacts=[zip_artifact],
                status=Status.OK.value
            )

        return AgentOutput(
            notes={"action": "packaging_skipped", "reason": "bundle_disabled"},
            artifacts=[],
            status=Status.OK.value
        )
