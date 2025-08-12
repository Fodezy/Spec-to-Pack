"""Spec builder - merge idea and decisions into a source spec."""

from typing import Dict, Any, Optional
from pathlib import Path


class SpecBuilder:
    """Builds source specs from idea and decision files."""
    
    def __init__(self):
        """Initialize the spec builder."""
        pass
    
    def merge_idea_decisions(
        self, 
        idea_path: Optional[Path] = None,
        decisions_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Merge idea and decisions into a source spec."""
        spec = {
            "meta": {
                "name": "Sample Spec",
                "version": "0.1.0"
            },
            "problem": {
                "statement": "Placeholder problem statement"
            },
            "success_metrics": [
                "Placeholder success metric"
            ],
            "constraints": {
                "offline_ok": True
            },
            "decisions": {
                "dials": {
                    "research": False,
                    "budget_tokens": 80000
                }
            }
        }
        return spec