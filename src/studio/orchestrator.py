"""Orchestrator for managing the generation pipeline."""

import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

from .types import SourceSpec, RunContext, PackType, Status
from .artifacts import ArtifactIndex, Blackboard
from .audit import AuditLog
from .validation import SchemaValidator
from .rendering import TemplateRenderer
from .adapters.llm import LLMAdapter, StubLLMAdapter
from .adapters.vector_store import VectorStoreAdapter, StubVectorStoreAdapter
from .adapters.browser import BrowserAdapter, StubBrowserAdapter
from .agents.base import Agent, FramerAgent, LibrarianAgent, PRDWriterAgent, DiagrammerAgent, QAArchitectAgent, RoadmapperAgent, PackagerAgent


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
        step_budget: int = 50,
        timeout_per_step_sec: int = 300,  # 5 minutes
        llm_adapter: Optional[LLMAdapter] = None,
        vector_store_adapter: Optional[VectorStoreAdapter] = None,
        browser_adapter: Optional[BrowserAdapter] = None
    ):
        """Initialize orchestrator with budgets and adapters."""
        self.step_budget = step_budget
        self.timeout_per_step_sec = timeout_per_step_sec
        
        # Adapters (use stubs if not provided)
        self.llm_adapter = llm_adapter or StubLLMAdapter()
        self.vector_store_adapter = vector_store_adapter or StubVectorStoreAdapter()
        self.browser_adapter = browser_adapter or StubBrowserAdapter()
        
        # Core components
        self.schema_validator = SchemaValidator()
        self.template_renderer = TemplateRenderer()
        
        # Agent registry
        self.agents: Dict[str, Agent] = {
            "framer": FramerAgent(),
            "librarian": LibrarianAgent(),
            "prd_writer": PRDWriterAgent(),
            "diagrammer": DiagrammerAgent(),
            "qa_architect": QAArchitectAgent(),
            "roadmapper": RoadmapperAgent(),
            "packager": PackagerAgent()
        }
        
        self.step_count = 0
    
    def run(self, ctx: RunContext, spec: SourceSpec, pack: PackType) -> ArtifactIndex:
        """Run the generation pipeline."""
        audit_log = AuditLog(ctx.out_dir / "audit.jsonl")
        blackboard = Blackboard()
        
        audit_log.log_event("pipeline_start", ctx.run_id, f"Starting {pack.value} pack generation")
        
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
            if duration > self.timeout_per_step_sec:
                raise StepTimeoutException(f"Step {step_name} exceeded timeout of {self.timeout_per_step_sec}s")
            
            self.step_count += 1
            audit_log.log_event("step_complete", ctx.run_id, 
                              f"Completed step: {step_name}", {"duration_sec": duration})
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            audit_log.log_event("step_error", ctx.run_id, 
                              f"Step {step_name} failed: {str(e)}", {"duration_sec": duration})
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
        """Run the balanced pack pipeline."""
        if not ctx.offline and ctx.dials.audience_mode.value in ["balanced", "deep"]:
            self._execute_step("research_content", ctx, audit_log,
                             lambda: self._run_agent("librarian", ctx, spec, blackboard))
        
        self._execute_step("write_prd", ctx, audit_log,
                          lambda: self._run_agent("prd_writer", ctx, spec, blackboard))
        
        self._execute_step("generate_diagrams", ctx, audit_log,
                          lambda: self._run_agent("diagrammer", ctx, spec, blackboard))
        
        self._execute_step("design_tests", ctx, audit_log,
                          lambda: self._run_agent("qa_architect", ctx, spec, blackboard))
        
        self._execute_step("create_roadmap", ctx, audit_log,
                          lambda: self._run_agent("roadmapper", ctx, spec, blackboard))
    
    def _run_deep_pipeline(self, ctx: RunContext, spec: SourceSpec, blackboard: Blackboard, audit_log: AuditLog) -> None:
        """Run the deep pack pipeline."""
        # Deep pack would include additional agents for:
        # - Deep engineering docs
        # - Contract generation  
        # - CI workflow generation
        # For now, just log that it would run
        audit_log.log_event("deep_pipeline", ctx.run_id, "Deep pack pipeline not yet implemented")