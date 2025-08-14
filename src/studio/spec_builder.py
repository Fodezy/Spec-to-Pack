"""Spec builder - merge idea and decisions into a source spec."""

from pathlib import Path

import yaml

from .types import (
    AudienceMode,
    Constraints,
    DevelopmentFlow,
    Dials,
    Meta,
    Problem,
    SourceSpec,
    SuccessMetrics,
    TestDepth,
)


class SpecBuilder:
    """Builds source specs from idea and decision files."""

    def __init__(self):
        """Initialize the spec builder."""
        pass

    def merge_idea_decisions(
        self,
        idea_path: Path | None = None,
        decisions_path: Path | None = None
    ) -> tuple[SourceSpec, Dials]:
        """Merge idea and decisions into a source spec and dials."""
        # Load idea if provided
        idea_data = {}
        if idea_path and idea_path.exists():
            with open(idea_path) as f:
                idea_data = yaml.safe_load(f) or {}

        # Load decisions if provided
        decisions_data = {}
        if decisions_path and decisions_path.exists():
            with open(decisions_path) as f:
                decisions_data = yaml.safe_load(f) or {}

        # Map decision data to Dials
        dials_data = {}
        # Handle nested dials structure
        dials_section = decisions_data.get("dials", decisions_data)
        if "audience_mode" in dials_section:
            # Map 'business' to 'balanced'
            audience_value = dials_section["audience_mode"]
            if audience_value == "business":
                audience_value = "balanced"
            dials_data["audience_mode"] = AudienceMode(audience_value)
        if "development_flow" in dials_section:
            dials_data["development_flow"] = DevelopmentFlow(dials_section["development_flow"])
        if "test_depth" in dials_section:
            # Map 'comprehensive' to 'full_matrix' 
            test_depth_value = dials_section["test_depth"]
            if test_depth_value == "comprehensive":
                test_depth_value = "full_matrix"
            dials_data["test_depth"] = TestDepth(test_depth_value)

        # Build spec from merged data
        spec_data = {
            "meta": Meta(
                name=idea_data.get("name", "Generated Spec"),
                version="0.1.0",
                description=idea_data.get("description")
            ),
            "problem": Problem(
                statement=idea_data.get("problem_statement", "Placeholder problem statement"),
                context=idea_data.get("target_audience")
            ),
            "success_metrics": SuccessMetrics(
                metrics=idea_data.get("key_features", [])
            ),
            "constraints": Constraints(
                offline_ok=decisions_data.get("offline", True),
                budget_tokens=decisions_data.get("budget_tokens", 80000)
            )
        }

        spec = SourceSpec(**spec_data)
        dials = Dials(**dials_data)

        return spec, dials

    def build_minimal_spec(self) -> SourceSpec:
        """Build a minimal valid SourceSpec for testing."""
        from .types import (
            Constraints,
            ContractsData,
            DiagramScope,
            Export,
            Meta,
            Operations,
            Problem,
            SourceSpec,
            SuccessMetrics,
            TestStrategy,
        )

        return SourceSpec(
            meta=Meta(
                name="Test Spec",
                version="1.0.0",
                description="A minimal test specification"
            ),
            problem=Problem(
                statement="Test problem statement",
                context="Test context"
            ),
            constraints=Constraints(),
            success_metrics=SuccessMetrics(),
            diagram_scope=DiagramScope(),
            contracts_data=ContractsData(),
            test_strategy=TestStrategy(),
            operations=Operations(),
            export=Export()
        )
