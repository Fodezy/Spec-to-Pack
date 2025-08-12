"""Spec builder - merge idea and decisions into a source spec."""

import yaml
from typing import Optional
from pathlib import Path

from .types import SourceSpec, Meta, Problem, Constraints, Dials, AudienceMode


class SpecBuilder:
    """Builds source specs from idea and decision files."""
    
    def __init__(self):
        """Initialize the spec builder."""
        pass
    
    def merge_idea_decisions(
        self, 
        idea_path: Optional[Path] = None,
        decisions_path: Optional[Path] = None
    ) -> SourceSpec:
        """Merge idea and decisions into a source spec."""
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
        
        # Build spec from merged data
        spec_data = {
            "meta": Meta(
                name=idea_data.get("name", "Generated Spec"),
                version="0.1.0",
                description=idea_data.get("description")
            ),
            "problem": Problem(
                statement=idea_data.get("problem", "Placeholder problem statement"),
                context=idea_data.get("context")
            ),
            "constraints": Constraints(
                offline_ok=decisions_data.get("offline", True),
                budget_tokens=decisions_data.get("budget_tokens", 80000)
            )
        }
        
        return SourceSpec(**spec_data)