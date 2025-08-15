"""Orchestrator for managing the generation pipeline."""

import time
from typing import Any

from .adapters.browser import BrowserAdapter, StubBrowserAdapter
from .adapters.embeddings import DualModelEmbeddingsAdapter, EmbeddingsAdapter, StubEmbeddingsAdapter
from .adapters.llm import LLMAdapter, StubLLMAdapter
from .adapters.search import FallbackSearchAdapter, SearchAdapter, StubSearchAdapter
from .adapters.vector_store import StubVectorStoreAdapter, VectorStoreAdapter
from .agents.base import (
    AccessibilityAgent,
    ADRAgent,
    Agent,
    CIWorkflowAgent,
    ContractAgent,
    DiagrammerAgent,
    FramerAgent,
    LibrarianAgent,
    ObservabilityAgent,
    PackagerAgent,
    PRDWriterAgent,
    QAArchitectAgent,
    RoadmapperAgent,
    RunbookAgent,
    SLOAgent,
    ThreatModelAgent,
)
from .artifacts import ArtifactIndex, Blackboard
from .audit import AuditLog
from .rendering import TemplateRenderer
from .types import PackType, RunContext, SourceSpec, Status
from .validation import SchemaValidator


class BudgetExceededException(Exception):
    """Raised when step budget is exceeded."""
    pass


class StepTimeoutException(Exception):
    """Raised when step timeout is exceeded."""
    pass


class Orchestrator:
    """Orchestrates the document generation pipeline."""

    def __init__(
        self,
        step_budget: int = 12,  # Per R1 specification
        timeout_per_step_sec: int = 60,  # Increased for browser content fetching
        llm_adapter: LLMAdapter | None = None,
        vector_store_adapter: VectorStoreAdapter | None = None,
        browser_adapter: BrowserAdapter | None = None,
        embeddings_adapter: EmbeddingsAdapter | None = None,
        search_adapter: SearchAdapter | None = None
    ):
        """Initialize orchestrator with budgets and adapters."""
        self.step_budget = step_budget
        self.timeout_per_step_sec = timeout_per_step_sec

        # Adapters (use stubs if not provided)
        self.llm_adapter = llm_adapter or StubLLMAdapter()
        self.vector_store_adapter = vector_store_adapter or StubVectorStoreAdapter()
        # Use smart browser adapter selection
        if browser_adapter is None:
            # Let LibrarianAgent handle smart adapter selection based on context
            self.browser_adapter = None
        else:
            self.browser_adapter = browser_adapter
        # Use real search adapter by default, only stub if explicitly passed
        if search_adapter is None:
            try:
                self.search_adapter = FallbackSearchAdapter()
            except ImportError:
                self.search_adapter = StubSearchAdapter()
        else:
            self.search_adapter = search_adapter
        
        # Use dual model embeddings by default, fallback to stub
        if embeddings_adapter is None:
            try:
                self.embeddings_adapter = DualModelEmbeddingsAdapter()
            except ImportError:
                self.embeddings_adapter = StubEmbeddingsAdapter()
        else:
            self.embeddings_adapter = embeddings_adapter

        # Core components
        self.schema_validator = SchemaValidator()
        self.template_renderer = TemplateRenderer()

        # Initialize cache manager
        from .cache import ResearchCacheManager
        self.cache_manager = ResearchCacheManager()

        # Agent registry
        self.agents: dict[str, Agent] = {
            "framer": FramerAgent(),
            "librarian": LibrarianAgent(
                search_adapter=self.search_adapter,
                browser_adapter=self.browser_adapter,
                vector_store_adapter=self.vector_store_adapter,
                embeddings_model=self.embeddings_adapter,
                cache_manager=self.cache_manager
            ),
            "prd_writer": PRDWriterAgent(),
            "diagrammer": DiagrammerAgent(),
            "qa_architect": QAArchitectAgent(),
            "roadmapper": RoadmapperAgent(),
            "packager": PackagerAgent(),
            # Deep pack agents
            "threat_model": ThreatModelAgent(),
            "accessibility": AccessibilityAgent(),
            "observability": ObservabilityAgent(),
            "runbook": RunbookAgent(),
            "slo": SLOAgent(),
            "adr": ADRAgent(),
            "ci_workflow": CIWorkflowAgent(),
            "contract": ContractAgent()
        }

        self.step_count = 0

        # Retry configuration per R1
        self.max_retries = 3
        self.base_backoff_sec = 2

    def run(self, ctx: RunContext, spec: SourceSpec, pack: PackType) -> ArtifactIndex:
        """Run the generation pipeline."""
        audit_log = AuditLog(ctx.out_dir / "audit.jsonl")
        blackboard = Blackboard()

        audit_log.log_event("pipeline_start", ctx.run_id, f"Starting {pack.value} pack generation",
                           stage="pipeline", event="start")

        try:
            # Validate spec
            self._execute_step("validate_spec", ctx, audit_log, lambda: self._validate_spec(spec))

            # Frame spec (fill missing fields)
            spec = self._execute_step("frame_spec", ctx, audit_log,
                                    lambda: self._run_agent("framer", ctx, spec, blackboard))

            # Determine agent pipeline based on pack type
            if pack in [PackType.BALANCED, PackType.BOTH]:
                self._run_balanced_pipeline(ctx, spec, blackboard, audit_log)

            if pack in [PackType.DEEP, PackType.BOTH]:
                self._run_deep_pipeline(ctx, spec, blackboard, audit_log)

            # Package outputs
            self._execute_step("package_outputs", ctx, audit_log,
                             lambda: self._run_agent("packager", ctx, spec, blackboard))

            # Create final artifact index
            artifact_index = blackboard.publish()
            artifact_index.run_id = ctx.run_id

            audit_log.log_event("pipeline_complete", ctx.run_id,
                              f"Generated {len(artifact_index.artifacts)} artifacts")

            return artifact_index

        except Exception as e:
            audit_log.log_event("pipeline_error", ctx.run_id, f"Pipeline failed: {str(e)}")
            raise
        finally:
            audit_log.save()

    def _execute_step_with_retry(self, step_name: str, ctx: RunContext, audit_log: AuditLog, step_func, retryable: bool = False) -> Any:
        """Execute a pipeline step with optional retry logic for Research and RenderPacks."""
        if not retryable:
            return self._execute_step(step_name, ctx, audit_log, step_func)

        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    # Exponential backoff
                    backoff_time = self.base_backoff_sec * (2 ** (attempt - 1))
                    audit_log.log_event("step_retry", ctx.run_id,
                                      f"Retrying step {step_name} (attempt {attempt + 1}/{self.max_retries + 1})")
                    time.sleep(backoff_time)

                return self._execute_step(f"{step_name}_attempt_{attempt + 1}", ctx, audit_log, step_func)

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    audit_log.log_event("step_retry_failed", ctx.run_id,
                                      f"Step {step_name} attempt {attempt + 1} failed: {str(e)}")
                    continue
                else:
                    # Final attempt failed
                    audit_log.log_event("step_max_retries_exceeded", ctx.run_id,
                                      f"Step {step_name} failed after {self.max_retries + 1} attempts")
                    raise last_exception

    def _execute_step(self, step_name: str, ctx: RunContext, audit_log: AuditLog, step_func) -> Any:
        """Execute a pipeline step with budget and timeout enforcement."""
        if self.step_count >= self.step_budget:
            raise BudgetExceededException(f"Step budget of {self.step_budget} exceeded")

        start_time = time.time()
        audit_log.log_event("step_start", ctx.run_id, f"Starting step: {step_name}")

        try:
            # Execute with timeout
            result = step_func()

            duration = time.time() - start_time
            duration_ms = int(duration * 1000)

            if duration > self.timeout_per_step_sec:
                raise StepTimeoutException(f"Step {step_name} exceeded timeout of {self.timeout_per_step_sec}s")

            self.step_count += 1
            audit_log.log_event("step_complete", ctx.run_id,
                              f"Completed step: {step_name}",
                              details={"duration_sec": duration},
                              stage=step_name, event="complete", duration_ms=duration_ms)

            return result

        except Exception as e:
            duration = time.time() - start_time
            duration_ms = int(duration * 1000)
            audit_log.log_event("step_error", ctx.run_id,
                              f"Step {step_name} failed: {str(e)}",
                              details={"duration_sec": duration, "error": str(e)},
                              stage=step_name, event="error", duration_ms=duration_ms, level="error")
            raise

    def _validate_spec(self, spec: SourceSpec) -> None:
        """Validate the source spec."""
        result = self.schema_validator.validate(spec)
        if not result.ok:
            error_messages = [f"{err.json_pointer}: {err.message}" for err in result.errors]
            raise ValueError(f"Spec validation failed: {'; '.join(error_messages)}")

    def _run_agent(self, agent_name: str, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> SourceSpec:
        """Run a specific agent."""
        agent = self.agents[agent_name]
        output = agent.run(ctx, spec, blackboard)

        # Add artifacts to blackboard
        for artifact in output.artifacts:
            blackboard.add_artifact(artifact)

        # Update spec if agent returned changes
        if output.updated_spec:
            spec = output.updated_spec

        # Handle agent status
        if output.status == Status.FAIL:
            raise RuntimeError(f"Agent {agent_name} failed")
        elif output.status == Status.RETRY:
            # For now, just log retry - could implement retry logic
            pass

        return spec

    def _run_balanced_pipeline(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard, audit_log: AuditLog) -> None:
        """Run the balanced pack pipeline following R1 state machine."""

        # R1 State: Research (with guard for offline mode)
        if not ctx.offline and ctx.dials.audience_mode.value in ["balanced", "deep"]:
            audit_log.log_event("state_enter", ctx.run_id, "Entering Research state")
            self._execute_step_with_retry("research_content", ctx, audit_log,
                             lambda: self._run_agent("librarian", ctx, spec, blackboard), retryable=True)
        else:
            audit_log.log_event("state_skip", ctx.run_id, "Skipping Research state (offline guard)")

        # R1 State: SliceMVP (stub for now)
        audit_log.log_event("state_enter", ctx.run_id, "Entering SliceMVP state")
        # TODO: Implement SlicerAgent

        # R1 State: WritePRD
        audit_log.log_event("state_enter", ctx.run_id, "Entering WritePRD state")
        self._execute_step("write_prd", ctx, audit_log,
                          lambda: self._run_agent("prd_writer", ctx, spec, blackboard))

        # R1 State: GenDiagrams
        audit_log.log_event("state_enter", ctx.run_id, "Entering GenDiagrams state")
        self._execute_step("generate_diagrams", ctx, audit_log,
                          lambda: self._run_agent("diagrammer", ctx, spec, blackboard))

        # R1 State: TestPlan
        audit_log.log_event("state_enter", ctx.run_id, "Entering TestPlan state")
        self._execute_step("design_tests", ctx, audit_log,
                          lambda: self._run_agent("qa_architect", ctx, spec, blackboard))

        # R1 State: Roadmap
        audit_log.log_event("state_enter", ctx.run_id, "Entering Roadmap state")
        self._execute_step("create_roadmap", ctx, audit_log,
                          lambda: self._run_agent("roadmapper", ctx, spec, blackboard))

        # R1 State: RedTeam (stub for now)
        audit_log.log_event("state_enter", ctx.run_id, "Entering RedTeam state")
        # TODO: Implement CriticAgent

        # R1 State: RenderPacks (with retries)
        audit_log.log_event("state_enter", ctx.run_id, "Entering RenderPacks state")
        self._execute_step_with_retry("render_packs", ctx, audit_log,
                      lambda: self._render_balanced_pack(ctx, spec, blackboard), retryable=True)

    def _run_deep_pipeline(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard, audit_log: AuditLog) -> None:
        """Run the deep pack pipeline."""
        audit_log.log_event("state_enter", ctx.run_id, "Entering Deep pack pipeline")
        
        # Generate threat model documentation
        audit_log.log_event("state_enter", ctx.run_id, "Generating threat model")
        self._execute_step("generate_threat_model", ctx, audit_log,
                          lambda: self._run_agent("threat_model", ctx, spec, blackboard))
        
        # Generate accessibility plan
        audit_log.log_event("state_enter", ctx.run_id, "Generating accessibility plan")
        self._execute_step("generate_accessibility_plan", ctx, audit_log,
                          lambda: self._run_agent("accessibility", ctx, spec, blackboard))
        
        # Generate observability plan
        audit_log.log_event("state_enter", ctx.run_id, "Generating observability plan")
        self._execute_step("generate_observability_plan", ctx, audit_log,
                          lambda: self._run_agent("observability", ctx, spec, blackboard))
        
        # Generate operational runbooks
        audit_log.log_event("state_enter", ctx.run_id, "Generating operational runbooks")
        self._execute_step("generate_runbooks", ctx, audit_log,
                          lambda: self._run_agent("runbook", ctx, spec, blackboard))
        
        # Generate SLO documentation
        audit_log.log_event("state_enter", ctx.run_id, "Generating SLO documentation")
        self._execute_step("generate_slos", ctx, audit_log,
                          lambda: self._run_agent("slo", ctx, spec, blackboard))
        
        # Generate ADR templates
        audit_log.log_event("state_enter", ctx.run_id, "Generating ADR templates")
        self._execute_step("generate_adrs", ctx, audit_log,
                          lambda: self._run_agent("adr", ctx, spec, blackboard))
        
        # Generate CI workflow
        audit_log.log_event("state_enter", ctx.run_id, "Generating CI workflows")
        self._execute_step("generate_ci_workflow", ctx, audit_log,
                          lambda: self._run_agent("ci_workflow", ctx, spec, blackboard))
        
        # Generate contract schemas
        audit_log.log_event("state_enter", ctx.run_id, "Generating contract schemas")
        self._execute_step("generate_contracts", ctx, audit_log,
                          lambda: self._run_agent("contract", ctx, spec, blackboard))

    def _render_balanced_pack(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard) -> None:
        """Render balanced pack templates."""
        # Prepare template data
        template_data = {
            "meta": spec.meta.model_dump(),
            "problem": spec.problem.model_dump(),
            "constraints": spec.constraints.model_dump(),
            "success_metrics": spec.success_metrics.model_dump(),
            "diagram_scope": spec.diagram_scope.model_dump(),
            "contracts_data": spec.contracts_data.model_dump(),
            "test_strategy": spec.test_strategy.model_dump(),
            "operations": spec.operations.model_dump(),
            "export": spec.export.model_dump(),
            "dials": ctx.dials.model_dump(),
            "pack_type": "balanced",
            "run_id": str(ctx.run_id),
            "generated_at": ctx.created_at.isoformat()
        }

        # Render brief.md template
        try:
            from .types import Template, TemplateType
            brief_template = Template(
                path=self.template_renderer.template_dir / "balanced" / "brief.md",
                type=TemplateType.MARKDOWN
            )

            # Use render_string for now since we need to write content to file
            with open(brief_template.path) as f:
                template_content = f.read()

            rendered_content = self.template_renderer.render_string(template_content, template_data)

            # Write to output directory
            output_file = ctx.out_dir / "brief.md"
            ctx.out_dir.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(rendered_content)

            # Create artifact and add to blackboard
            from .artifacts import DocumentArtifact
            artifact = DocumentArtifact(
                name="brief",
                path=output_file,
                pack="balanced",
                purpose="Project brief document"
            )
            blackboard.add_artifact(artifact)

        except Exception as e:
            # Template rendering is non-critical in stub phase
            print(f"Warning: Failed to render brief.md: {e}")
