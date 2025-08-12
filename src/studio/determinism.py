"""Determinism utilities for consistent outputs."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class DeterminismUtils:
    """Utilities to ensure deterministic outputs."""
    
    @staticmethod
    def normalize_json(data: Dict[str, Any], exclude_keys: set = None) -> str:
        """Normalize JSON output with sorted keys and consistent formatting."""
        if exclude_keys is None:
            exclude_keys = {"generated_at"}
        
        # Remove timestamp keys for comparison
        normalized_data = {
            k: v for k, v in data.items() 
            if k not in exclude_keys
        }
        
        return json.dumps(normalized_data, sort_keys=True, indent=2, ensure_ascii=False)
    
    @staticmethod
    def ensure_lf_newlines(content: str) -> str:
        """Ensure LF newlines (Unix style) regardless of platform."""
        return content.replace('\r\n', '\n').replace('\r', '\n')
    
    @staticmethod
    def utc_timestamp() -> str:
        """Generate UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    @staticmethod
    def normalize_file_for_comparison(file_path: Path, exclude_patterns: list = None) -> str:
        """Normalize a file's content for deterministic comparison."""
        if exclude_patterns is None:
            exclude_patterns = [
                "generated_at",
                "run_id",
                "timestamp"
            ]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Normalize newlines
        content = DeterminismUtils.ensure_lf_newlines(content)
        
        # If it's JSON, normalize it
        if file_path.suffix == '.json':
            try:
                data = json.loads(content)
                for pattern in exclude_patterns:
                    if pattern in data:
                        del data[pattern]
                content = DeterminismUtils.normalize_json(data)
            except json.JSONDecodeError:
                pass  # Not valid JSON, keep as is
        
        return content