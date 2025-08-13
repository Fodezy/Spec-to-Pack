"""Template versioning and management."""

from pathlib import Path
from typing import Dict, Any
import subprocess
import json

# Template set versions with semantic versioning
TEMPLATE_VERSIONS = {
    "balanced": "1.0.0",
    "deep": "1.0.0"
}

def get_template_commit() -> str:
    """Get current git commit hash for template versioning."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent.parent  # Go to repo root
        )
        if result.returncode == 0:
            return result.stdout.strip()[:8]  # Short hash
        else:
            return "unknown"
    except (subprocess.SubprocessError, FileNotFoundError):
        return "unknown"

def get_template_set_version(pack_type: str = "balanced") -> str:
    """Get semantic version for template set."""
    return f"{pack_type}-{TEMPLATE_VERSIONS.get(pack_type, '1.0.0')}"

def get_template_metadata() -> Dict[str, Any]:
    """Get complete template metadata for manifest embedding."""
    return {
        "template_set": get_template_set_version(),
        "template_commit": get_template_commit(),
        "available_sets": TEMPLATE_VERSIONS
    }